variable "aws_region" { type=string default="ap-south-1" }
variable "project_name" { type=string default="aime" }
variable "environment" { type=string default="prod" }
variable "vpc_cidr" { type=string default="10.40.0.0/16" }
variable "public_subnet_cidrs" { type=list(string) default=["10.40.1.0/24","10.40.2.0/24"] }
variable "private_subnet_cidrs" { type=list(string) default=["10.40.11.0/24","10.40.12.0/24"] }
variable "rds_instance_class" { type=string default="db.t4g.micro" }
variable "redis_node_type" { type=string default="cache.t4g.micro" }
variable "db_name" { type=string default="infra_memory" }
variable "db_username" { type=string default="aime" }
variable "db_password" { type=string sensitive=true }
variable "credentials_encryption_key" { type=string sensitive=true }
variable "aws_session_duration_seconds" { type=number default=900 }
variable "cors_allowed_origins" { type=string }
variable "smtp_host" { type=string default="" }
variable "smtp_port" { type=number default=587 }
variable "smtp_username" { type=string default="" }
variable "smtp_password" { type=string sensitive=true default="" }
variable "smtp_from" { type=string default="AIME <no-reply@example.com>" }
variable "smtp_use_tls" { type=bool default=true }
variable "password_reset_url" { type=string }
variable "email_verification_url" { type=string }
variable "backend_image" { type=string }
variable "frontend_image" { type=string }
