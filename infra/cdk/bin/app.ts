#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { WikiStack } from "../lib/wiki-stack.js";

const app = new cdk.App();
const environment = app.node.tryGetContext("environment") as string;

new WikiStack(app, `IntelligentCorporateWiki-${environment}`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? process.env.AWS_REGION ?? "us-east-1",
  },
  description: "Format-aware AWS document ingestion and grounded corporate RAG wiki",
  environment,
});
