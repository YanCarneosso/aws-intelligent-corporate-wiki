import * as fs from "node:fs";
import * as path from "node:path";
import {
  Arn,
  ArnFormat,
  CfnOutput,
  CfnResource,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  Tags,
} from "aws-cdk-lib";
import * as apigwv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as apigwv2Authorizers from "aws-cdk-lib/aws-apigatewayv2-authorizers";
import * as apigwv2Integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as cloudtrail from "aws-cdk-lib/aws-cloudtrail";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as eventTargets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as kms from "aws-cdk-lib/aws-kms";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as sqs from "aws-cdk-lib/aws-sqs";
import { Construct } from "constructs";

export interface WikiStackProps extends StackProps {
  readonly environment: string;
  readonly lambdaAssetPath?: string;
  readonly webDistPath?: string;
}

export class WikiStack extends Stack {
  constructor(scope: Construct, id: string, props: WikiStackProps) {
    super(scope, id, props);

    const isProduction = props.environment === "prod";
    const removalPolicy = isProduction ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY;
    const owner = (this.node.tryGetContext("owner") as string | undefined) ?? "portfolio";
    const costCenter =
      (this.node.tryGetContext("costCenter") as string | undefined) ?? "learning";
    for (const [key, value] of Object.entries({
      Project: "IntelligentCorporateWiki",
      Environment: props.environment,
      ManagedBy: "AWS-CDK",
      Owner: owner,
      CostCenter: costCenter,
    })) {
      Tags.of(this).add(key, value);
    }

    const dataKey = new kms.Key(this, "DataKey", {
      alias: `alias/intelligent-wiki-${props.environment}`,
      enableKeyRotation: true,
      removalPolicy,
      pendingWindow: Duration.days(14),
    });

    const rawBucket = this.dataBucket("RawDocuments", dataKey, removalPolicy, true);
    const processedBucket = this.dataBucket("ProcessedDocuments", dataKey, removalPolicy, false);
    const quarantineBucket = this.dataBucket("Quarantine", dataKey, removalPolicy, false);
    const accessLogBucket = new s3.Bucket(this, "AccessLogs", {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: false,
      objectOwnership: s3.ObjectOwnership.OBJECT_WRITER,
      removalPolicy,
      autoDeleteObjects: !isProduction,
      lifecycleRules: [{ expiration: Duration.days(isProduction ? 365 : 30) }],
    });

    const documents = new dynamodb.Table(this, "Documents", {
      partitionKey: { name: "document_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: dataKey,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: isProduction },
      removalPolicy,
    });

    const deadLetterQueue = new sqs.Queue(this, "ProcessingDeadLetterQueue", {
      encryption: sqs.QueueEncryption.KMS,
      encryptionMasterKey: dataKey,
      enforceSSL: true,
      retentionPeriod: Duration.days(14),
    });

    const lambdaAsset = props.lambdaAssetPath ?? path.resolve(__dirname, "../../../build/lambda");
    if (!fs.existsSync(lambdaAsset)) {
      throw new Error("Missing build/lambda asset. Run 'make build-backend' before CDK synth.");
    }
    const commonEnvironment = {
      RAW_BUCKET: rawBucket.bucketName,
      PROCESSED_BUCKET: processedBucket.bucketName,
      QUARANTINE_BUCKET: quarantineBucket.bucketName,
      DOCUMENT_TABLE: documents.tableName,
      BEDROCK_MODEL_ID: "amazon.nova-lite-v1:0",
      LOG_LEVEL: "INFO",
      AWS_RETRY_MODE: "standard",
      AWS_MAX_ATTEMPTS: "5",
    };
    const createFunction = (
      logicalId: string,
      handler: string,
      options: { timeout?: Duration; memorySize?: number } = {},
    ): lambda.Function => {
      const logGroup = new logs.LogGroup(this, `${logicalId}Logs`, {
        retention: isProduction ? logs.RetentionDays.THREE_MONTHS : logs.RetentionDays.TWO_WEEKS,
        encryptionKey: dataKey,
        removalPolicy,
      });
      return new lambda.Function(this, logicalId, {
        runtime: lambda.Runtime.PYTHON_3_12,
        architecture: lambda.Architecture.ARM_64,
        code: lambda.Code.fromAsset(lambdaAsset),
        handler,
        timeout: options.timeout ?? Duration.seconds(60),
        memorySize: options.memorySize ?? 512,
        tracing: lambda.Tracing.ACTIVE,
        environment: commonEnvironment,
        logGroup,
      });
    };

    const classifier = createFunction("ClassifierFunction", "services.ingestion.handler.lambda_handler", {
      timeout: Duration.minutes(2),
      memorySize: 1_024,
    });
    const pdfProcessor = createFunction(
      "PdfProcessorFunction",
      "services.processing.handlers.digital_pdf_handler",
      { timeout: Duration.minutes(5), memorySize: 1_536 },
    );
    const csvProcessor = createFunction(
      "CsvProcessorFunction",
      "services.processing.handlers.csv_handler",
      { timeout: Duration.minutes(5), memorySize: 1_024 },
    );
    const textractStarter = createFunction(
      "TextractStarterFunction",
      "services.processing.handlers.start_textract_handler",
    );
    const textractPoller = createFunction(
      "TextractPollerFunction",
      "services.processing.handlers.poll_textract_handler",
      { timeout: Duration.minutes(5), memorySize: 1_024 },
    );
    const metadata = createFunction("MetadataFunction", "services.metadata.handler.lambda_handler", {
      timeout: Duration.minutes(5),
      memorySize: 1_024,
    });
    const indexStarter = createFunction(
      "IndexStarterFunction",
      "services.indexing.handlers.start_handler",
    );
    const indexPoller = createFunction(
      "IndexPollerFunction",
      "services.indexing.handlers.poll_handler",
    );
    const failure = createFunction("FailureFunction", "services.failure.handler.lambda_handler");
    const query = createFunction("QueryFunction", "services.query.handler.lambda_handler", {
      timeout: Duration.seconds(29),
      memorySize: 1_024,
    });
    const source = createFunction("SourceFunction", "services.query.source_handler.lambda_handler");

    rawBucket.grantRead(classifier);
    documents.grantReadWriteData(classifier);
    for (const fn of [pdfProcessor, csvProcessor, textractPoller]) {
      rawBucket.grantRead(fn);
      processedBucket.grantReadWrite(fn);
    }
    rawBucket.grantRead(textractStarter);
    textractStarter.addToRolePolicy(
      new iam.PolicyStatement({
        sid: "TextractStartHasNoResourceLevelPermissions",
        actions: ["textract:StartDocumentTextDetection"],
        resources: ["*"],
      }),
    );
    textractPoller.addToRolePolicy(
      new iam.PolicyStatement({
        sid: "TextractGetHasNoResourceLevelPermissions",
        actions: ["textract:GetDocumentTextDetection"],
        resources: ["*"],
      }),
    );
    processedBucket.grantReadWrite(metadata);
    metadata.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [this.foundationModelArn("amazon.nova-lite-v1:0")],
      }),
    );
    quarantineBucket.grantWrite(failure);
    documents.grantReadWriteData(failure);
    documents.grantReadData(source);
    rawBucket.grantRead(source);

    const vectorBucket = new CfnResource(this, "VectorBucket", {
      type: "AWS::S3Vectors::VectorBucket",
      properties: {
        EncryptionConfiguration: { SseType: "aws:kms", KmsKeyArn: dataKey.keyArn },
      },
    });
    vectorBucket.applyRemovalPolicy(removalPolicy);
    const vectorIndex = new CfnResource(this, "VectorIndex", {
      type: "AWS::S3Vectors::Index",
      properties: {
        VectorBucketArn: vectorBucket.ref,
        DataType: "float32",
        Dimension: 1024,
        DistanceMetric: "cosine",
        MetadataConfiguration: { NonFilterableMetadataKeys: ["title"] },
      },
    });
    vectorIndex.addResourceDependency(vectorBucket);
    vectorIndex.applyRemovalPolicy(removalPolicy);

    const knowledgeBaseRole = new iam.Role(this, "KnowledgeBaseRole", {
      assumedBy: new iam.ServicePrincipal("bedrock.amazonaws.com", {
        conditions: { StringEquals: { "aws:SourceAccount": this.account } },
      }),
    });
    processedBucket.grantRead(knowledgeBaseRole, "knowledge-base/*");
    dataKey.grantEncryptDecrypt(knowledgeBaseRole);
    knowledgeBaseRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [this.foundationModelArn("amazon.titan-embed-text-v2:0")],
      }),
    );
    knowledgeBaseRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "s3vectors:GetIndex",
          "s3vectors:PutVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:QueryVectors",
          "s3vectors:GetVectors",
        ],
        resources: [vectorBucket.ref, vectorIndex.ref],
      }),
    );

    const knowledgeBase = new CfnResource(this, "KnowledgeBase", {
      type: "AWS::Bedrock::KnowledgeBase",
      properties: {
        Name: `intelligent-wiki-${props.environment}`,
        Description: "Grounded corporate wiki with page/row provenance",
        RoleArn: knowledgeBaseRole.roleArn,
        KnowledgeBaseConfiguration: {
          Type: "VECTOR",
          VectorKnowledgeBaseConfiguration: {
            EmbeddingModelArn: this.foundationModelArn("amazon.titan-embed-text-v2:0"),
            EmbeddingModelConfiguration: {
              BedrockEmbeddingModelConfiguration: {
                Dimensions: 1024,
                EmbeddingDataType: "FLOAT32",
              },
            },
          },
        },
        StorageConfiguration: {
          Type: "S3_VECTORS",
          S3VectorsConfiguration: {
            VectorBucketArn: vectorBucket.ref,
            IndexArn: vectorIndex.ref,
          },
        },
      },
    });
    knowledgeBase.addResourceDependency(vectorIndex);
    knowledgeBase.addResourceDependency(knowledgeBaseRole.node.defaultChild as CfnResource);

    const dataSource = new CfnResource(this, "KnowledgeBaseDataSource", {
      type: "AWS::Bedrock::DataSource",
      properties: {
        Name: `processed-documents-${props.environment}`,
        KnowledgeBaseId: knowledgeBase.ref,
        DataDeletionPolicy: isProduction ? "RETAIN" : "DELETE",
        DataSourceConfiguration: {
          Type: "S3",
          S3Configuration: {
            BucketArn: processedBucket.bucketArn,
            InclusionPrefixes: ["knowledge-base/"],
          },
        },
        VectorIngestionConfiguration: {
          ChunkingConfiguration: { ChunkingStrategy: "NONE" },
        },
      },
    });
    dataSource.addResourceDependency(knowledgeBase);

    const knowledgeBaseArn = Arn.format(
      {
        service: "bedrock",
        resource: "knowledge-base",
        resourceName: knowledgeBase.ref,
        arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
      },
      this,
    );
    for (const fn of [indexStarter, indexPoller]) {
      fn.addEnvironment("KNOWLEDGE_BASE_ID", knowledgeBase.ref);
      fn.addEnvironment("KNOWLEDGE_BASE_DATA_SOURCE_ID", dataSource.getAtt("DataSourceId").toString());
      fn.addToRolePolicy(
        new iam.PolicyStatement({
          actions: ["bedrock:StartIngestionJob", "bedrock:GetIngestionJob"],
          resources: [knowledgeBaseArn],
        }),
      );
    }
    documents.grantReadWriteData(indexPoller);

    const guardrail = new CfnResource(this, "WikiGuardrail", {
      type: "AWS::Bedrock::Guardrail",
      properties: {
        Name: `intelligent-wiki-${props.environment}`,
        Description: "Blocks prompt attacks and masks sensitive output",
        BlockedInputMessaging: "A solicitação não pode ser processada com segurança.",
        BlockedOutputsMessaging: "A resposta foi bloqueada pelos controles de segurança.",
        KmsKeyArn: dataKey.keyArn,
        ContentPolicyConfig: {
          ContentFiltersTierConfig: { TierName: "STANDARD" },
          FiltersConfig: [
            {
              Type: "PROMPT_ATTACK",
              InputStrength: "HIGH",
              OutputStrength: "NONE",
              InputAction: "BLOCK",
              OutputAction: "NONE",
              InputEnabled: true,
              OutputEnabled: false,
              InputModalities: ["TEXT"],
              OutputModalities: ["TEXT"],
            },
          ],
        },
        SensitiveInformationPolicyConfig: {
          PiiEntitiesConfig: [
            { Type: "EMAIL", Action: "ANONYMIZE" },
            { Type: "PHONE", Action: "ANONYMIZE" },
          ],
        },
      },
    });

    query.addEnvironment("KNOWLEDGE_BASE_ID", knowledgeBase.ref);
    query.addEnvironment("BEDROCK_GUARDRAIL_ID", guardrail.ref);
    query.addEnvironment("BEDROCK_GUARDRAIL_VERSION", "DRAFT");
    query.addEnvironment("RETRIEVAL_TOP_K", "8");
    query.addEnvironment("RETRIEVAL_SCORE_THRESHOLD", "0.35");
    source.addEnvironment("PRESIGNED_URL_TTL_SECONDS", "300");
    source.addEnvironment("KNOWLEDGE_BASE_ID", knowledgeBase.ref);
    query.addToRolePolicy(
      new iam.PolicyStatement({ actions: ["bedrock:Retrieve"], resources: [knowledgeBaseArn] }),
    );
    query.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [this.foundationModelArn("amazon.nova-lite-v1:0")],
      }),
    );
    query.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:ApplyGuardrail"],
        resources: [
          Arn.format(
            {
              service: "bedrock",
              resource: "guardrail",
              resourceName: guardrail.ref,
              arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
            },
            this,
          ),
        ],
      }),
    );

    const stateMachine = this.ingestionStateMachine({
      classifier,
      pdfProcessor,
      csvProcessor,
      textractStarter,
      textractPoller,
      metadata,
      indexStarter,
      indexPoller,
      failure,
      deadLetterQueue,
      logKey: dataKey,
    });
    new events.Rule(this, "RawObjectCreatedRule", {
      eventPattern: {
        source: ["aws.s3"],
        detailType: ["Object Created"],
        detail: { bucket: { name: [rawBucket.bucketName] } },
      },
      targets: [new eventTargets.SfnStateMachine(stateMachine, { deadLetterQueue })],
    });

    const userPool = new cognito.UserPool(this, "UserPool", {
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      passwordPolicy: {
        minLength: 12,
        requireDigits: true,
        requireLowercase: true,
        requireSymbols: true,
        requireUppercase: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      deletionProtection: isProduction,
      removalPolicy,
      standardAttributes: { email: { required: true, mutable: false } },
    });
    new cognito.CfnUserPoolGroup(this, "AdminGroup", {
      userPoolId: userPool.userPoolId,
      groupName: "admin",
      description: "Full wiki access",
    });
    new cognito.CfnUserPoolGroup(this, "CommercialGroup", {
      userPoolId: userPool.userPoolId,
      groupName: "commercial",
      description: "Commercial department documents",
    });
    const userPoolClient = userPool.addClient("WebClient", {
      generateSecret: false,
      authFlows: { userPassword: true, userSrp: true },
      accessTokenValidity: Duration.minutes(60),
      idTokenValidity: Duration.minutes(60),
      refreshTokenValidity: Duration.days(7),
      preventUserExistenceErrors: true,
    });
    const jwtAuthorizer = new apigwv2Authorizers.HttpJwtAuthorizer(
      "CognitoAuthorizer",
      `https://cognito-idp.${this.region}.${this.urlSuffix}/${userPool.userPoolId}`,
      { jwtAudience: [userPoolClient.userPoolClientId] },
    );
    const apiAccessLogs = new logs.LogGroup(this, "ApiAccessLogs", {
      retention: isProduction ? logs.RetentionDays.THREE_MONTHS : logs.RetentionDays.TWO_WEEKS,
      encryptionKey: dataKey,
      removalPolicy,
    });
    const httpApi = new apigwv2.HttpApi(this, "WikiApi", {
      createDefaultStage: false,
      corsPreflight: {
        allowCredentials: true,
        allowHeaders: ["authorization", "content-type"],
        allowMethods: [apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.POST],
        allowOrigins: [
          (this.node.tryGetContext("webOrigin") as string | undefined) ?? "http://localhost:5173",
        ],
        maxAge: Duration.hours(1),
      },
    });
    new apigwv2.HttpStage(this, "DefaultApiStage", {
      httpApi,
      stageName: "$default",
      autoDeploy: true,
      throttle: { burstLimit: 50, rateLimit: 25 },
      accessLogSettings: {
        destination: new apigwv2.LogGroupLogDestination(apiAccessLogs),
        format: apigateway.AccessLogFormat.jsonWithStandardFields(),
      },
    });
    httpApi.addRoutes({
      path: "/query",
      methods: [apigwv2.HttpMethod.POST],
      integration: new apigwv2Integrations.HttpLambdaIntegration("QueryIntegration", query),
      authorizer: jwtAuthorizer,
    });
    httpApi.addRoutes({
      path: "/sources/{documentId}",
      methods: [apigwv2.HttpMethod.GET],
      integration: new apigwv2Integrations.HttpLambdaIntegration("SourceIntegration", source),
      authorizer: jwtAuthorizer,
    });

    const webBucket = new s3.Bucket(this, "WebAssets", {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy,
      autoDeleteObjects: !isProduction,
    });
    const apiOrigin = new origins.HttpOrigin(
      `${httpApi.apiId}.execute-api.${this.region}.${this.urlSuffix}`,
      { protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY },
    );
    const apiBehavior: cloudfront.BehaviorOptions = {
      origin: apiOrigin,
      viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
      cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
      originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
      responseHeadersPolicy: cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
    };
    const distribution = new cloudfront.Distribution(this, "WebDistribution", {
      defaultRootObject: "index.html",
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(webBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        responseHeadersPolicy: cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      additionalBehaviors: {
        "/query": apiBehavior,
        "/sources/*": apiBehavior,
      },
      enableLogging: true,
      logBucket: accessLogBucket,
      logFilePrefix: "cloudfront/",
    });
    const webDist = props.webDistPath ?? path.resolve(__dirname, "../../../apps/web/dist");
    if (!fs.existsSync(webDist)) {
      throw new Error("Missing apps/web/dist. Run 'make build-frontend' before CDK synth.");
    }
    new s3deploy.BucketDeployment(this, "DeployWeb", {
      destinationBucket: webBucket,
      sources: [
        s3deploy.Source.asset(webDist),
        s3deploy.Source.data(
          "config.js",
          `window.__WIKI_CONFIG__=${JSON.stringify({
            apiUrl: "",
            awsRegion: this.region,
            userPoolId: userPool.userPoolId,
            userPoolClientId: userPoolClient.userPoolClientId,
          })};`,
        ),
      ],
      distribution,
      distributionPaths: ["/*"],
      prune: true,
    });

    new cloudtrail.Trail(this, "AuditTrail", {
      bucket: accessLogBucket,
      encryptionKey: dataKey,
      includeGlobalServiceEvents: true,
      isMultiRegionTrail: true,
      sendToCloudWatchLogs: true,
      cloudWatchLogsRetention: isProduction
        ? logs.RetentionDays.THREE_MONTHS
        : logs.RetentionDays.TWO_WEEKS,
    });
    this.observabilityDashboard(query, stateMachine, deadLetterQueue);

    new CfnOutput(this, "RawBucketName", { value: rawBucket.bucketName });
    new CfnOutput(this, "ApiUrl", { value: httpApi.apiEndpoint });
    new CfnOutput(this, "WebUrl", { value: `https://${distribution.distributionDomainName}` });
    new CfnOutput(this, "UserPoolId", { value: userPool.userPoolId });
    new CfnOutput(this, "UserPoolClientId", { value: userPoolClient.userPoolClientId });
    new CfnOutput(this, "KnowledgeBaseId", { value: knowledgeBase.ref });
  }

  private dataBucket(
    id: string,
    key: kms.IKey,
    removalPolicy: RemovalPolicy,
    eventBridgeEnabled: boolean,
  ): s3.Bucket {
    return new s3.Bucket(this, id, {
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: key,
      bucketKeyEnabled: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      eventBridgeEnabled,
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      removalPolicy,
      autoDeleteObjects: removalPolicy === RemovalPolicy.DESTROY,
      lifecycleRules: [
        {
          noncurrentVersionExpiration: Duration.days(90),
          abortIncompleteMultipartUploadAfter: Duration.days(7),
        },
      ],
    });
  }

  private foundationModelArn(modelId: string): string {
    return Arn.format(
      {
        service: "bedrock",
        account: "",
        resource: "foundation-model",
        resourceName: modelId,
        arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
      },
      this,
    );
  }

  private ingestionStateMachine(input: {
    classifier: lambda.IFunction;
    pdfProcessor: lambda.IFunction;
    csvProcessor: lambda.IFunction;
    textractStarter: lambda.IFunction;
    textractPoller: lambda.IFunction;
    metadata: lambda.IFunction;
    indexStarter: lambda.IFunction;
    indexPoller: lambda.IFunction;
    failure: lambda.IFunction;
    deadLetterQueue: sqs.IQueue;
    logKey: kms.IKey;
  }): sfn.StateMachine {
    const invoke = (id: string, fn: lambda.IFunction): tasks.LambdaInvoke =>
      new tasks.LambdaInvoke(this, id, { lambdaFunction: fn, payloadResponseOnly: true });
    const classifier = invoke("Classify", input.classifier);
    const pdf = invoke("ExtractDigitalPdf", input.pdfProcessor);
    const csv = invoke("ParseStructuredCsv", input.csvProcessor);
    const startOcr = invoke("StartTextract", input.textractStarter);
    const pollOcr = invoke("PollTextract", input.textractPoller);
    const enrich = invoke("EnrichMetadata", input.metadata);
    const startIndex = invoke("StartKnowledgeBaseSync", input.indexStarter);
    const pollIndex = invoke("PollKnowledgeBaseSync", input.indexPoller);
    const failure = invoke("PersistFailure", input.failure);

    for (const task of [classifier, pdf, csv, startOcr, pollOcr, enrich, startIndex, pollIndex]) {
      task.addRetry({
        errors: [
          "Lambda.ServiceException",
          "Lambda.TooManyRequestsException",
          "KnowledgeBaseBusy",
          "States.Timeout",
        ],
        interval: Duration.seconds(2),
        backoffRate: 2,
        maxAttempts: 4,
      });
      task.addCatch(failure, { resultPath: "$.error" });
    }
    const dlq = new tasks.SqsSendMessage(this, "SendFailureToDLQ", {
      queue: input.deadLetterQueue,
      messageBody: sfn.TaskInput.fromJsonPathAt("$"),
    });
    failure.next(dlq).next(new sfn.Fail(this, "ProcessingFailed", { cause: "Document quarantined" }));

    const success = new sfn.Succeed(this, "DocumentAvailable");
    const duplicate = new sfn.Succeed(this, "DuplicateIgnored");
    const waitOcr = new sfn.Wait(this, "WaitForTextract", {
      time: sfn.WaitTime.duration(Duration.seconds(5)),
    });
    const ocrComplete = new sfn.Choice(this, "TextractComplete?");
    startOcr.next(waitOcr).next(pollOcr).next(ocrComplete);
    ocrComplete.when(sfn.Condition.booleanEquals("$.ocr_complete", true), enrich).otherwise(waitOcr);

    pdf.next(enrich);
    csv.next(enrich);
    const waitIndex = new sfn.Wait(this, "WaitForKnowledgeBase", {
      time: sfn.WaitTime.duration(Duration.seconds(10)),
    });
    const indexComplete = new sfn.Choice(this, "KnowledgeBaseSyncComplete?");
    enrich.next(startIndex).next(waitIndex).next(pollIndex).next(indexComplete);
    indexComplete
      .when(sfn.Condition.booleanEquals("$.index_complete", true), success)
      .otherwise(waitIndex);

    const route = new sfn.Choice(this, "RouteByProcessingMethod")
      .when(sfn.Condition.stringEquals("$.classification.processing_method", "direct_text"), pdf)
      .when(sfn.Condition.stringEquals("$.classification.processing_method", "structured_parser"), csv)
      .when(sfn.Condition.stringEquals("$.classification.processing_method", "textract"), startOcr)
      .otherwise(new sfn.Fail(this, "UnsupportedType", { cause: "No processor route" }));
    const definition = classifier.next(
      new sfn.Choice(this, "DuplicateEvent?")
        .when(sfn.Condition.booleanEquals("$.duplicate", true), duplicate)
        .otherwise(route),
    );
    const stateMachineLogs = new logs.LogGroup(this, "StateMachineLogs", {
      retention: logs.RetentionDays.ONE_MONTH,
      encryptionKey: input.logKey,
      removalPolicy: RemovalPolicy.DESTROY,
    });
    return new sfn.StateMachine(this, "IngestionStateMachine", {
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: Duration.hours(2),
      tracingEnabled: true,
      logs: { destination: stateMachineLogs, level: sfn.LogLevel.ERROR, includeExecutionData: false },
    });
  }

  private observabilityDashboard(
    query: lambda.IFunction,
    stateMachine: sfn.IStateMachine,
    deadLetterQueue: sqs.IQueue,
  ): void {
    const dashboard = new cloudwatch.Dashboard(this, "OperationsDashboard");
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: "RAG API",
        left: [query.metricInvocations(), query.metricErrors()],
        right: [query.metricDuration({ statistic: "p95" })],
      }),
      new cloudwatch.GraphWidget({
        title: "Ingestion",
        left: [
          stateMachine.metricStarted(),
          stateMachine.metricSucceeded(),
          stateMachine.metricFailed(),
        ],
        right: [deadLetterQueue.metricApproximateNumberOfMessagesVisible()],
      }),
    );
    query.metricErrors({ period: Duration.minutes(5) }).createAlarm(this, "QueryErrorsAlarm", {
      threshold: 1,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    stateMachine.metricFailed({ period: Duration.minutes(5) }).createAlarm(
      this,
      "IngestionFailuresAlarm",
      {
        threshold: 1,
        evaluationPeriods: 1,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      },
    );
    deadLetterQueue.metricApproximateNumberOfMessagesVisible().createAlarm(this, "DLQAlarm", {
      threshold: 1,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
  }
}
