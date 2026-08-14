import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { App } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { WikiStack } from "../lib/wiki-stack.js";

describe("WikiStack", () => {
  let template: Template;
  let assetRoot = "";

  beforeAll(() => {
    assetRoot = fs.mkdtempSync(path.join(os.tmpdir(), "wiki-stack-test-"));
    const lambdaAssetPath = path.join(assetRoot, "lambda");
    const webDistPath = path.join(assetRoot, "web");
    fs.mkdirSync(lambdaAssetPath);
    fs.mkdirSync(webDistPath);
    fs.writeFileSync(path.join(lambdaAssetPath, "handler.py"), "def lambda_handler(event, context): pass\n");
    fs.writeFileSync(path.join(webDistPath, "index.html"), "<!doctype html><title>Atlas</title>\n");
    const app = new App({ context: { environment: "dev", webOrigin: "http://localhost:5173" } });
    const stack = new WikiStack(app, "TestStack", {
      environment: "dev",
      env: { account: "123456789012", region: "us-east-1" },
      lambdaAssetPath,
      webDistPath,
    });
    template = Template.fromStack(stack);
  }, 60_000);

  afterAll(() => {
    fs.rmSync(assetRoot, { recursive: true, force: true });
  });

  it("encrypts, versions, and blocks public access to document buckets", () => {
    template.hasResourceProperties("AWS::S3::Bucket", {
      BucketEncryption: Match.anyValue(),
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
      VersioningConfiguration: { Status: "Enabled" },
    });
  });

  it("uses S3 Vectors with 1024-dimensional cosine embeddings", () => {
    template.hasResourceProperties("AWS::S3Vectors::Index", {
      DataType: "float32",
      Dimension: 1024,
      DistanceMetric: "cosine",
    });
    template.hasResourceProperties("AWS::Bedrock::KnowledgeBase", {
      StorageConfiguration: Match.objectLike({ Type: "S3_VECTORS" }),
    });
  });

  it("protects both public HTTP routes with JWT authorization", () => {
    const routes = template.findResources("AWS::ApiGatewayV2::Route");
    expect(Object.keys(routes)).toHaveLength(2);
    for (const value of Object.values(routes)) {
      const route = value as { Properties?: { AuthorizationType?: unknown } };
      expect(route.Properties?.AuthorizationType).toBe("JWT");
    }
  });

  it("creates an explicit asynchronous ingestion workflow", () => {
    template.resourceCountIs("AWS::StepFunctions::StateMachine", 1);
    template.resourceCountIs("AWS::Cognito::UserPool", 1);
    template.resourceCountIs("AWS::CloudTrail::Trail", 1);
  });

  it("proxies authenticated API paths through the web distribution without caching", () => {
    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: Match.objectLike({
        CacheBehaviors: Match.arrayWith([
          Match.objectLike({ PathPattern: "/query" }),
          Match.objectLike({ PathPattern: "/sources/*" }),
        ]),
      }),
    });
  });
});
