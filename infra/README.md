# CloudStudy Infrastructure

Two CloudFormation stacks that deploy CloudStudy to AWS.

## Architecture

```
Internet -> ALB (public subnets) -> EC2 instances (private subnets) -> RDS MySQL (private subnets)
                                    nginx :80 + gunicorn :5000
```

- **Stack 1 (`cloudstudy-network`):** VPC, 2 public + 2 private subnets across 2 AZs, IGW, NAT GW, route tables, security groups
- **Stack 2 (`cloudstudy-app`):** ALB, Auto Scaling Group (min 1, max 4), Launch Template, CloudWatch scaling alarms

RDS MySQL, S3, and Cognito are pre-existing resources. Their endpoints and IDs are passed into the app stack as parameters with defaults already set.

EC2 instances are bootstrapped via UserData: clone repo from `main`, build frontend, configure nginx, install backend, start gunicorn via systemd.

## Prerequisites

- AWS CLI installed and configured
- Learner Lab credentials exported:
  ```bash
  export AWS_ACCESS_KEY_ID=<from Learner Lab>
  export AWS_SECRET_ACCESS_KEY=<from Learner Lab>
  export AWS_SESSION_TOKEN=<from Learner Lab>
  ```
- Your Learner Lab account ID (visible in the AWS console top-right)
- Gemini API key

## Deploy

```bash
# 1. Deploy network stack (~3 min)
aws cloudformation deploy \
  --template-file infra/network.yaml \
  --stack-name cloudstudy-network \
  --region us-east-1

# 2. Deploy app stack (~15 min)
# RdsHost, S3BucketName, CognitoUserPoolId, CognitoClientId all have correct defaults.
# Only RdsPassword and GeminiApiKey must be supplied.
aws cloudformation deploy \
  --template-file infra/app.yaml \
  --stack-name cloudstudy-app \
  --parameter-overrides \
      RdsPassword=<your-db-password> \
      GeminiApiKey=<your-gemini-key> \
  --region us-east-1

# 3. Get the app URL and other outputs
aws cloudformation describe-stacks \
  --stack-name cloudstudy-app \
  --query "Stacks[0].Outputs" \
  --region us-east-1
```

## Teardown

Delete in reverse order. The network stack can only be deleted after the app stack is gone.

```bash
# 1. Delete app stack
aws cloudformation delete-stack --stack-name cloudstudy-app --region us-east-1
aws cloudformation wait stack-delete-complete --stack-name cloudstudy-app --region us-east-1

# 2. Delete network stack
aws cloudformation delete-stack --stack-name cloudstudy-network --region us-east-1
```

Note: The S3 bucket (`cloudstudy-uploads`) and RDS instance (`cloudstudy-db`) are not managed by CloudFormation and will not be deleted by the above commands. Delete them manually via the console or CLI if needed.

## Troubleshooting

- **Stack creation fails:** Check Events tab in CloudFormation console for the specific error
- **Credentials expired:** Re-export Learner Lab credentials and retry the command
- **ASG timed out (0 SUCCESS signals):** UserData bootstrap failed on the EC2 instance. SSH via SSM Session Manager and check `/var/log/cloud-init-output.log`
- **502 Bad Gateway:** gunicorn may not have started; check `systemctl status cloudstudy` on the instance
- **RDS connection refused:** Confirm the RDS instance is in `available` state: `aws rds describe-db-instances --region us-east-1`
