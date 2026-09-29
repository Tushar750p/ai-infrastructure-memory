# AIME AWS IAM Role Setup

AIME can collect infrastructure memory using an AWS IAM role with short-lived STS credentials. This is the recommended production connection mode.

## Permissions

Attach [aime-readonly-policy.json](./aime-readonly-policy.json) to the customer role. It grants only the read operations currently used by AIME:

- CloudTrail event lookup
- EC2 VPC, subnet, security group and instance discovery
- RDS DB instance discovery
- ElastiCache replication group discovery
- CloudWatch metric statistics

AIME does not need permission to create, modify, terminate, or delete customer infrastructure.

## Role trust policy

Use [aime-role-trust-policy.json](./aime-role-trust-policy.json) as a template. Replace:

- `<AIME-AWS-PRINCIPAL-ARN>` with the AWS principal that runs AIME.
- `<AIME-EXTERNAL-ID>` with the unique external ID generated/provided for the customer connection.

The ExternalId condition helps prevent confused-deputy access when AIME assumes customer roles.

## Connect the role

Send the AIME API:

```json
{
  "organization_name": "example-company",
  "credential_mode": "role",
  "role_arn": "arn:aws:iam::123456789012:role/AIMEInfrastructureMemoryRole",
  "external_id": "customer-specific-external-id",
  "region": "ap-south-1"
}
```

The API verifies the role using STS before saving the connection.

## Security notes

- AIME stores the role ARN and encrypts the external ID.
- STS credentials are temporary and are not persisted as AWS access keys.
- Existing access-key connections remain supported for backward compatibility.
- For production, use HTTPS and protect the AIME organization API key.
- Review the IAM policy whenever AIME adds a new AWS integration; do not grant broad `AdministratorAccess`.
