# AIME AWS Production Bootstrap

The GitHub Actions production deployment uses AWS OIDC. The AWS IAM role is intentionally created outside the application Terraform stack so Terraform does not need bootstrap credentials to create its own deploy identity.

## 1. Create the GitHub OIDC provider

If your AWS account does not already have the GitHub Actions OIDC provider, create it for:

`https://token.actions.githubusercontent.com`

Audience:

`sts.amazonaws.com`

## 2. Create the deployment role

Create an IAM role named `aime-github-deploy` with a trust policy restricted to this repository and its `main` branch.

Replace `AWS_ACCOUNT_ID` and `GITHUB_ORG_REPO`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:GITHUB_ORG_REPO:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

For this repository, `GITHUB_ORG_REPO` is:

`Tushar750p/ai-infrastructure-memory`

## 3. Permissions

The role must be allowed to perform the resources managed by `infrastructure/terraform/prod`, plus:

- ECR repository/image operations
- S3 state bucket operations
- DynamoDB state-lock operations
- Secrets Manager create/read/update
- STS GetCallerIdentity
- ECS task/service operations
- CloudFormation is not required by the AIME Terraform stack

For the first bootstrap, it is acceptable to use a dedicated deployment policy covering the Terraform-managed AWS resources. After the first successful deployment, tighten the policy to the exact resource ARNs.

## 4. GitHub repository secrets

Add these GitHub Actions secrets:

| Secret | Required | Purpose |
|---|---|---|
| `AWS_DEPLOY_ROLE_ARN` | Yes | OIDC deployment role ARN |
| `CREDENTIALS_ENCRYPTION_KEY` | Yes | Fernet application encryption key |
| `CORS_ALLOWED_ORIGINS` | Yes | Production frontend origin |
| `PASSWORD_RESET_URL` | Yes | Password-reset URL |
| `EMAIL_VERIFICATION_URL` | Yes | Email-verification URL |
| `SMTP_HOST` | Optional | SMTP server |
| `SMTP_USERNAME` | Optional | SMTP username |
| `SMTP_PASSWORD` | Optional | SMTP password |
| `SMTP_FROM` | Optional | Sender address |
| `SMTP_PORT` | Optional | Defaults to 587 |
| `SMTP_USE_TLS` | Optional | Defaults to true |
| `ACM_CERTIFICATE_ARN` | Recommended | ACM certificate for ALB HTTPS |

The RDS master password is generated and managed by Amazon RDS; it is no longer a GitHub secret.

## 5. Verify the OIDC role before deployment

After creating the role, verify that the role trust policy contains all of the following:

- OIDC provider: `token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`
- Subject: `repo:Tushar750p/ai-infrastructure-memory:ref:refs/heads/main`
- GitHub Actions permission: `id-token: write` (already present in the workflow)

The GitHub secret `AWS_DEPLOY_ROLE_ARN` must contain the full ARN of that exact role, for example:

`arn:aws:iam::AWS_ACCOUNT_ID:role/aime-github-deploy`

Do not put an AWS access key or secret key into the repository secrets for this workflow.

## 6. Generate the application encryption key

Run locally:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the generated value into `CREDENTIALS_ENCRYPTION_KEY`.

## 7. Trigger deployment

Open GitHub Actions → **Production Deploy** → **Run workflow**.

The workflow will:

1. Run the backend test suite.
2. Authenticate to AWS using OIDC.
3. Create ECR repositories if missing.
4. Create/update the application secret in Secrets Manager.
5. Build and push immutable backend/frontend images.
6. Bootstrap encrypted/versioned Terraform state.
7. Run Terraform.
8. Run Alembic migrations as a one-shot ECS task.
9. Wait for both ECS services to become stable.

No AWS access key or long-lived AWS secret needs to be stored in GitHub.

## Important

The first run creates production infrastructure and can incur AWS charges. Review the Terraform plan/costs before allowing the first production apply.
