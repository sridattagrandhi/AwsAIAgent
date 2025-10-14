#!/usr/bin/env bash
set -euo pipefail

if ! command -v sam >/dev/null 2>&1; then
  echo "Please install AWS SAM CLI: https://docs.aws.amazon.com/serverless-application-model/"
  exit 1
fi

sam build
sam deploy --guided
