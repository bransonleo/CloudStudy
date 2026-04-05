# CloudStudy Infrastructure

Two CloudFormation stacks that deploy CloudStudy to AWS.

## Architecture

```
Internet -> ALB (public subnets, HTTPS 443) -> EC2 instances (private subnets) -> RDS MySQL (private subnets)
                                                nginx :80 + gunicorn :5000
```

- **Stack 1 (`cloudstudy-network`):** VPC, 2 public + 2 private subnets across 2 AZs, IGW, NAT GW, route tables, security groups
- **Stack 2 (`cloudstudy-app`):** ALB (HTTP + HTTPS), Auto Scaling Group (min 1, max 4), Launch Template, CloudWatch scaling alarms

RDS MySQL, S3, and Cognito are pre-existing resources. Their endpoints and IDs are passed into the app stack as parameters with defaults already set.

The frontend is pre-built locally and uploaded to S3. EC2 instances are bootstrapped via UserData: clone repo from `main`, sync pre-built frontend from S3, configure nginx, install backend Python dependencies, start gunicorn via systemd. This keeps bootstrap time under 2 minutes on a t2.micro.

## Prerequisites

- AWS CLI installed and configured
- Node.js 20.19+ and npm (for building the frontend locally)
- Learner Lab credentials exported:
  ```bash
  export AWS_ACCESS_KEY_ID=<from Learner Lab>
  export AWS_SECRET_ACCESS_KEY=<from Learner Lab>
  export AWS_SESSION_TOKEN=<from Learner Lab>
  ```
- Your Learner Lab account ID (visible in the AWS console top-right)
- Gemini API key

## Deploy

The deploy script handles everything: both CloudFormation stacks, HTTPS setup, Cognito configuration, frontend build, and S3 sync.

```bash
# Export Learner Lab credentials first, then:
bash infra/deploy.sh <rds-password> <gemini-api-key>
```

The script performs these steps:
1. Deploys the network stack (VPC, subnets, security groups)
2. Deploys the app stack (ALB, ASG, Launch Template, CloudWatch)
3. Opens port 443 on the ALB security group
4. Creates a self-signed SSL certificate and adds an HTTPS listener to the ALB
5. Updates Cognito callback and logout URLs with the HTTPS ALB endpoint
6. Builds the frontend with the correct redirect URI and uploads to S3
7. Syncs the frontend to the running EC2 instance

Total time: ~8 minutes. The self-signed certificate will cause a browser security warning; click through it to proceed.

### Manual deploy

If you prefer to run each step individually, the script is well-commented and each step can be run separately. See [deploy.sh](deploy.sh) for details.

## Post-Deploy Verification

Run these checks in order after `deploy.sh` completes. Each step depends on the one before it.

### 1. RDS is available

```bash
aws rds describe-db-instances \
  --db-instance-identifier cloudstudy-db \
  --region us-east-1 \
  --query "DBInstances[0].DBInstanceStatus" \
  --output text
```

Expected: `available`. If `stopping` or `stopped`, start it from the RDS console before proceeding.

### 2. ASG instances are InService

```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names CloudStudy-asg \
  --region us-east-1 \
  --query "AutoScalingGroups[0].Instances[*].[InstanceId,LifecycleState]" \
  --output table
```

Expected: 2 instances with `LifecycleState: InService`. If fewer, the UserData bootstrap likely failed. Check `/var/log/cloud-init-output.log` via SSM Session Manager.

### 3. ALB target group has healthy targets

```bash
TG_ARN=$(aws elbv2 describe-target-groups \
  --region us-east-1 \
  --query "TargetGroups[?contains(TargetGroupName,'CloudStudy')].TargetGroupArn | [0]" \
  --output text)

aws elbv2 describe-target-health \
  --target-group-arn "$TG_ARN" \
  --region us-east-1 \
  --query "TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]" \
  --output table
```

Expected: at least 1 target in `healthy` state. The ALB requires 2 consecutive `/api/health` successes (30s interval) before marking a target healthy. Wait up to 1 minute after ASG shows InService if targets are still `initial`.

### 4. API health endpoint responds

```bash
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name cloudstudy-app \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='ALBEndpoint'].OutputValue" \
  --output text | sed 's|^http://||')

curl -sk "https://$ALB_DNS/api/health"
```

Expected: `{"status":"ok"}`. This confirms nginx is running, gunicorn is serving, and RDS was reachable at startup. The app calls `create_tables()` on boot, so a DB failure would crash gunicorn before it could respond.

### 5. Frontend is served

```bash
curl -sk "https://$ALB_DNS/" | head -3
```

Expected: HTML beginning with `<!doctype html>`. This confirms the S3-to-EC2 nginx sync completed and nginx is serving the React SPA. A non-HTML response (e.g. JSON 404) means the sync did not run. Re-run it manually:

```bash
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" "Name=tag:Name,Values=CloudStudy-ec2" \
  --region us-east-1 \
  --query "Reservations[].Instances[0].InstanceId" --output text | head -1)

aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["aws s3 sync s3://cloudstudy-uploads/frontend/ /usr/share/nginx/html/ --delete --exact-timestamps"]' \
  --region us-east-1
```

### 6. Cognito callback URLs include the ALB

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id us-east-1_Ss7jHFZSC \
  --client-id 7oiatn9dtru73j9vrl08896fv4 \
  --region us-east-1 \
  --query "UserPoolClient.CallbackURLs" \
  --output json
```

Expected: the list includes `https://<ALB_DNS>/callback`. If missing, the Cognito step in deploy.sh did not complete. Re-run step 5 of the script manually or re-run the full deploy.

### 7. S3 frontend assets are present

```bash
aws s3 ls s3://cloudstudy-uploads/frontend/ --region us-east-1 | head -10
```

Expected: `index.html` and hashed JS/CSS asset files. If empty, the frontend build did not upload. Run `cd frontend && npm run build` then `aws s3 sync dist/ s3://cloudstudy-uploads/frontend/ --delete --region us-east-1`. New ASG instances pull from S3 on boot, so this must be populated before scaling events.

### 8. CloudWatch alarms are not in ALARM state

```bash
aws cloudwatch describe-alarms \
  --alarm-names CloudStudy-high-cpu CloudStudy-low-cpu \
  --region us-east-1 \
  --query "MetricAlarms[*].[AlarmName,StateValue]" \
  --output table
```

Expected: `OK` or `INSUFFICIENT_DATA` (normal immediately after deploy, as there are not enough data points yet). `ALARM` right after deploy indicates a misconfiguration in the scaling policy or ASG dimensions.

---

## Teardown

```bash
bash infra/teardown.sh
```

This deletes both stacks in the correct order (app first, then network).

Note: The S3 bucket (`cloudstudy-uploads`), RDS instance (`cloudstudy-db`), and Cognito user pool are not managed by CloudFormation and will not be deleted. Remove them manually via the console or CLI if needed.

## Troubleshooting

- **Stack creation fails:** Check Events tab in CloudFormation console for the specific error
- **Credentials expired:** Re-export Learner Lab credentials and retry the command
- **ASG timed out (0 SUCCESS signals):** UserData bootstrap failed on the EC2 instance. SSH via SSM Session Manager and check `/var/log/cloud-init-output.log`
- **502 Bad Gateway:** gunicorn may not have started; check `systemctl status cloudstudy` on the instance
- **RDS connection refused:** Confirm the RDS instance is in `available` state: `aws rds describe-db-instances --region us-east-1`
