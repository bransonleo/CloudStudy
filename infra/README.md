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
