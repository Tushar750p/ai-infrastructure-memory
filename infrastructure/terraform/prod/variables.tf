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
variable "aws_session_duration_seconds" { type=number default=900 }
variable "backend_image" { type=string }
variable "frontend_image" { type=string }
variable "acm_certificate_arn" { type=string default="" }
variable "app_secrets_arn" { type=string }
