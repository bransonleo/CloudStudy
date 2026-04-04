#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CloudStudy full deploy script
#
# Deploys both CloudFormation stacks, sets up HTTPS on the ALB, configures
# Cognito callback URLs, builds the frontend with the correct redirect URI,
# and syncs it to the running EC2 instance.
#
# Usage:
#   export AWS_ACCESS_KEY_ID=...
#   export AWS_SECRET_ACCESS_KEY=...
#   export AWS_SESSION_TOKEN=...
#   cd CloudStudy
#   bash infra/deploy.sh <rds-password> <gemini-api-key>
# ---------------------------------------------------------------------------
set -euo pipefail

REGION="us-east-1"
NETWORK_STACK="cloudstudy-network"
APP_STACK="cloudstudy-app"
S3_BUCKET="cloudstudy-uploads"
COGNITO_USER_POOL_ID="us-east-1_Ss7jHFZSC"
COGNITO_CLIENT_ID="7oiatn9dtru73j9vrl08896fv4"
COGNITO_DOMAIN="https://us-east-1ss7jhfzsc.auth.us-east-1.amazoncognito.com"

# ---- Validate arguments ----
if [ $# -lt 2 ]; then
  echo "Usage: bash infra/deploy.sh <rds-password> <gemini-api-key>"
  exit 1
fi
RDS_PASSWORD="$1"
GEMINI_API_KEY="$2"

# ---- Verify AWS credentials ----
echo "==> Verifying AWS credentials..."
aws sts get-caller-identity --region "$REGION" > /dev/null
echo "    Credentials OK."

# ---- Step 1: Deploy network stack ----
echo ""
echo "==> Step 1/7: Deploying network stack..."
aws cloudformation deploy \
  --template-file infra/network.yaml \
  --stack-name "$NETWORK_STACK" \
  --region "$REGION" \
  --no-fail-on-empty-changeset
echo "    Network stack ready."

# ---- Step 2: Deploy app stack ----
echo ""
echo "==> Step 2/7: Deploying app stack (this takes ~5 min)..."
aws cloudformation deploy \
  --template-file infra/app.yaml \
  --stack-name "$APP_STACK" \
  --parameter-overrides \
      RdsPassword="$RDS_PASSWORD" \
      GeminiApiKey="$GEMINI_API_KEY" \
  --region "$REGION" \
  --no-fail-on-empty-changeset
echo "    App stack ready."

# ---- Get ALB details ----
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name "$APP_STACK" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ALBEndpoint'].OutputValue" \
  --output text | sed 's|^http://||')
echo "    ALB DNS: $ALB_DNS"

ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names CloudStudy-alb \
  --region "$REGION" \
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

ALB_SG=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns "$ALB_ARN" \
  --region "$REGION" \
  --query "LoadBalancers[0].SecurityGroups[0]" --output text)

TG_ARN=$(aws elbv2 describe-target-groups \
  --region "$REGION" \
  --query "TargetGroups[?contains(TargetGroupName,'CloudStudy')].TargetGroupArn | [0]" \
  --output text)

# ---- Step 3: Open port 443 on ALB security group ----
echo ""
echo "==> Step 3/7: Ensuring port 443 is open on ALB security group..."
aws ec2 authorize-security-group-ingress \
  --group-id "$ALB_SG" \
  --protocol tcp --port 443 --cidr 0.0.0.0/0 \
  --region "$REGION" 2>/dev/null || echo "    (already open)"
echo "    Port 443 OK."

# ---- Step 4: Create self-signed cert and HTTPS listener ----
echo ""
echo "==> Step 4/7: Setting up HTTPS listener..."

# Check if HTTPS listener already exists
HTTPS_LISTENER=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --region "$REGION" \
  --query "Listeners[?Port==\`443\`].ListenerArn | [0]" --output text)

if [ "$HTTPS_LISTENER" = "None" ] || [ -z "$HTTPS_LISTENER" ]; then
  CERT_DIR=$(mktemp -d)
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -subj "/CN=$ALB_DNS" 2>/dev/null

  CERT_ARN=$(aws acm import-certificate \
    --certificate "fileb://$CERT_DIR/cert.pem" \
    --private-key "fileb://$CERT_DIR/key.pem" \
    --region "$REGION" \
    --query "CertificateArn" --output text)

  rm -rf "$CERT_DIR"

  aws elbv2 create-listener \
    --load-balancer-arn "$ALB_ARN" \
    --protocol HTTPS --port 443 \
    --certificates CertificateArn="$CERT_ARN" \
    --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
    --region "$REGION" > /dev/null

  echo "    HTTPS listener created."
else
  echo "    HTTPS listener already exists."
fi

# ---- Step 5: Update Cognito callback URLs ----
echo ""
echo "==> Step 5/7: Updating Cognito callback and logout URLs..."
aws cognito-idp update-user-pool-client \
  --user-pool-id "$COGNITO_USER_POOL_ID" \
  --client-id "$COGNITO_CLIENT_ID" \
  --callback-urls \
    "http://localhost:5173/callback" \
    "https://$ALB_DNS/callback" \
  --logout-urls \
    "http://localhost:5173" \
    "http://localhost:5173/login" \
    "https://$ALB_DNS" \
    "https://$ALB_DNS/login" \
  --supported-identity-providers COGNITO \
  --allowed-o-auth-flows code \
  --allowed-o-auth-scopes openid email profile aws.cognito.signin.user.admin \
  --allowed-o-auth-flows-user-pool-client \
  --region "$REGION" > /dev/null
echo "    Cognito URLs updated."

# ---- Step 6: Build frontend and upload to S3 ----
echo ""
echo "==> Step 6/7: Building frontend and uploading to S3..."
cat > frontend/.env <<EOF
VITE_COGNITO_DOMAIN=$COGNITO_DOMAIN
VITE_COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID
VITE_COGNITO_REDIRECT_URI=https://$ALB_DNS/callback
VITE_COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID
EOF

(cd frontend && npm install --silent && npm run build --silent)
aws s3 sync frontend/dist/ "s3://$S3_BUCKET/frontend/" --delete --region "$REGION" > /dev/null
echo "    Frontend built and uploaded to S3."

# ---- Step 7: Sync frontend to running EC2 instance ----
echo ""
echo "==> Step 7/7: Syncing frontend to running EC2 instance..."
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" "Name=tag:Name,Values=CloudStudy-ec2" \
  --region "$REGION" \
  --query "Reservations[].Instances[0].InstanceId" --output text | head -1)

if [ -n "$INSTANCE_ID" ] && [ "$INSTANCE_ID" != "None" ]; then
  CMD_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["aws s3 sync s3://cloudstudy-uploads/frontend/ /usr/share/nginx/html/ --delete --exact-timestamps"]' \
    --region "$REGION" \
    --query "Command.CommandId" --output text)

  # Wait for SSM command to finish (up to 30 seconds)
  for i in $(seq 1 6); do
    sleep 5
    STATUS=$(aws ssm get-command-invocation \
      --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
      --region "$REGION" \
      --query "Status" --output text 2>/dev/null || echo "Pending")
    if [ "$STATUS" != "InProgress" ] && [ "$STATUS" != "Pending" ]; then
      break
    fi
  done
  echo "    Frontend synced to instance $INSTANCE_ID."
else
  echo "    WARNING: No running instance found. Frontend will sync on next ASG launch."
fi

# ---- Done ----
echo ""
echo "============================================"
echo "  CloudStudy deployed successfully!"
echo ""
echo "  URL:  https://$ALB_DNS"
echo ""
echo "  Note: Self-signed cert -- browser will"
echo "  show a security warning. Click through it."
echo "============================================"
