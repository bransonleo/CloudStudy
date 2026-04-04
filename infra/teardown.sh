#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CloudStudy teardown script
#
# Deletes both CloudFormation stacks in the correct order.
# Pre-existing resources (RDS, S3, Cognito) are NOT deleted.
#
# Usage:
#   bash infra/teardown.sh
# ---------------------------------------------------------------------------
set -euo pipefail

REGION="us-east-1"
APP_STACK="cloudstudy-app"
NETWORK_STACK="cloudstudy-network"

echo "==> Deleting app stack..."
aws cloudformation delete-stack --stack-name "$APP_STACK" --region "$REGION"
echo "    Waiting for app stack deletion (this may take a few minutes)..."
aws cloudformation wait stack-delete-complete --stack-name "$APP_STACK" --region "$REGION"
echo "    App stack deleted."

echo ""
echo "==> Deleting network stack..."
aws cloudformation delete-stack --stack-name "$NETWORK_STACK" --region "$REGION"
echo "    Waiting for network stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name "$NETWORK_STACK" --region "$REGION"
echo "    Network stack deleted."

echo ""
echo "============================================"
echo "  CloudStudy infrastructure torn down."
echo ""
echo "  Still running (not managed by CF):"
echo "    - RDS instance (cloudstudy-db)"
echo "    - S3 bucket (cloudstudy-uploads)"
echo "    - Cognito user pool"
echo "============================================"
