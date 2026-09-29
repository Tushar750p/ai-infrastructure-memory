terraform {
  required_version = ">= 1.8.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 6.0" } }
}
provider "aws" { region = var.aws_region }
data "aws_availability_zones" "available" { state = "available" }

locals {
  name = var.project_name
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
  tags = { Project = var.project_name, Environment = var.environment, ManagedBy = "Terraform" }
}

resource "aws_vpc" "this" {
  cidr_block = var.vpc_cidr
  enable_dns_support = true
  enable_dns_hostnames = true
  tags = merge(local.tags, { Name = "${local.name}-vpc" })
}
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags = merge(local.tags, { Name = "${local.name}-igw" })
}
resource "aws_subnet" "public" {
  count = 2
  vpc_id = aws_vpc.this.id
  cidr_block = var.public_subnet_cidrs[count.index]
  availability_zone = local.azs[count.index]
  map_public_ip_on_launch = true
  tags = merge(local.tags, { Name = "${local.name}-public-${count.index + 1}" })
}
resource "aws_subnet" "private" {
  count = 2
  vpc_id = aws_vpc.this.id
  cidr_block = var.private_subnet_cidrs[count.index]
  availability_zone = local.azs[count.index]
  tags = merge(local.tags, { Name = "${local.name}-private-${count.index + 1}" })
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route { cidr_block = "0.0.0.0/0"; gateway_id = aws_internet_gateway.this.id }
}
resource "aws_route_table_association" "public" {
  count = 2
  subnet_id = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
resource "aws_eip" "nat" { count = 2; domain = "vpc" }
resource "aws_nat_gateway" "this" {
  count = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id = aws_subnet.public[count.index].id
  depends_on = [aws_internet_gateway.this]
}
resource "aws_route_table" "private" {
  count = 2
  vpc_id = aws_vpc.this.id
  route { cidr_block = "0.0.0.0/0"; nat_gateway_id = aws_nat_gateway.this[count.index].id }
}
resource "aws_route_table_association" "private" {
  count = 2
  subnet_id = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

resource "aws_security_group" "alb" {
  name = "${local.name}-alb"; vpc_id = aws_vpc.this.id
  ingress { from_port = 80; to_port = 80; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_security_group" "ecs" {
  name = "${local.name}-ecs"; vpc_id = aws_vpc.this.id
  ingress { from_port = 3000; to_port = 3000; protocol = "tcp"; security_groups = [aws_security_group.alb.id] }
  ingress { from_port = 8000; to_port = 8000; protocol = "tcp"; security_groups = [aws_security_group.alb.id] }
  egress { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_security_group" "rds" {
  name = "${local.name}-rds"; vpc_id = aws_vpc.this.id
  ingress { from_port = 5432; to_port = 5432; protocol = "tcp"; security_groups = [aws_security_group.ecs.id] }
}
resource "aws_security_group" "redis" {
  name = "${local.name}-redis"; vpc_id = aws_vpc.this.id
  ingress { from_port = 6379; to_port = 6379; protocol = "tcp"; security_groups = [aws_security_group.ecs.id] }
}

resource "aws_db_subnet_group" "this" { name = "${local.name}-db"; subnet_ids = aws_subnet.private[*].id }
resource "aws_db_instance" "this" {
  identifier = "${local.name}-postgres"
  engine = "postgres"; engine_version = "16"
  instance_class = var.rds_instance_class
  allocated_storage = 50; max_allocated_storage = 200; storage_type = "gp3"
  storage_encrypted = true
  db_name = var.db_name; username = var.db_username; password = var.db_password; port = 5432
  db_subnet_group_name = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible = false
  backup_retention_period = 7
  deletion_protection = true
  skip_final_snapshot = false
}

resource "aws_elasticache_subnet_group" "this" { name = "${local.name}-redis"; subnet_ids = aws_subnet.private[*].id }
resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${local.name}-redis"
  description = "AIME production Redis"
  engine = "redis"; engine_version = "7.1"
  node_type = var.redis_node_type
  num_cache_clusters = 2
  automatic_failover_enabled = true; multi_az_enabled = true
  subnet_group_name = aws_elasticache_subnet_group.this.name
  security_group_ids = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true; transit_encryption_enabled = true
}

resource "aws_ecr_repository" "backend" {
  name = "${local.name}/backend"; image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}
resource "aws_ecr_repository" "frontend" {
  name = "${local.name}/frontend"; image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}
resource "aws_ecs_cluster" "this" {
  name = "${local.name}-cluster"
  setting { name = "containerInsights"; value = "enabled" }
}

resource "aws_iam_role" "execution" {
  name = "${local.name}-ecs-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole"
  }]})
}
resource "aws_iam_role_policy_attachment" "execution" {
  role = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role" "task" {
  name = "${local.name}-ecs-task"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole"
  }]})
}
resource "aws_iam_role_policy" "task" {
  role = aws_iam_role.task.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["cloudtrail:LookupEvents","ec2:Describe*","rds:Describe*","elasticache:Describe*","cloudwatch:GetMetricData","cloudwatch:GetMetricStatistics","cloudwatch:ListMetrics"], Resource = "*"
  }]})
}

resource "aws_cloudwatch_log_group" "backend" { name = "/ecs/${local.name}/backend"; retention_in_days = 30 }
resource "aws_cloudwatch_log_group" "frontend" { name = "/ecs/${local.name}/frontend"; retention_in_days = 30 }

resource "aws_lb" "this" {
  name = "${local.name}-alb"; load_balancer_type = "application"; internal = false
  security_groups = [aws_security_group.alb.id]; subnets = aws_subnet.public[*].id
}
resource "aws_lb_target_group" "frontend" {
  name = "${local.name}-frontend"; port = 3000; protocol = "HTTP"; target_type = "ip"; vpc_id = aws_vpc.this.id
  health_check { path = "/"; matcher = "200-399" }
}
resource "aws_lb_target_group" "backend" {
  name = "${local.name}-backend"; port = 8000; protocol = "HTTP"; target_type = "ip"; vpc_id = aws_vpc.this.id
  health_check { path = "/health/ready"; matcher = "200" }
}
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn; port = 80; protocol = "HTTP"
  default_action { type = "forward"; target_group_arn = aws_lb_target_group.frontend.arn }
}
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn; priority = 100
  condition { path_pattern { values = ["/api/*"] } }
  action { type = "forward"; target_group_arn = aws_lb_target_group.backend.arn }
}

resource "aws_ecs_task_definition" "frontend" {
  family = "${local.name}-frontend"; requires_compatibilities = ["FARGATE"]; network_mode = "awsvpc"
  cpu = 256; memory = 512; execution_role_arn = aws_iam_role.execution.arn
  container_definitions = jsonencode([{
    name = "frontend"; image = var.frontend_image; essential = true
    portMappings = [{ containerPort = 3000, protocol = "tcp" }]
    logConfiguration = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.frontend.name, awslogs-region = var.aws_region, awslogs-stream-prefix = "frontend" } }
  }])
}
resource "aws_ecs_task_definition" "backend" {
  family = "${local.name}-backend"; requires_compatibilities = ["FARGATE"]; network_mode = "awsvpc"
  cpu = 512; memory = 1024; execution_role_arn = aws_iam_role.execution.arn; task_role_arn = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name = "backend"; image = var.backend_image; essential = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name="DATABASE_URL", value="postgresql+psycopg2://${var.db_username}:${var.db_password}${aws_db_instance.this.address}:5432/${var.db_name}" },
      { name="REDIS_URL", value="rediss://${aws_elasticache_replication_group.this.primary_endpoint_address}:6379/0" },
      { name="CREDENTIALS_ENCRYPTION_KEY", value=var.credentials_encryption_key },
      { name="AWS_SESSION_DURATION_SECONDS", value=tostring(var.aws_session_duration_seconds) },
      { name="CORS_ALLOWED_ORIGINS", value=var.cors_allowed_origins },
      { name="AUTH_COOKIE_SECURE", value="true" }, { name="AUTH_COOKIE_NAME", value="aime_session" },
      { name="SMTP_HOST", value=var.smtp_host }, { name="SMTP_PORT", value=tostring(var.smtp_port) },
      { name="SMTP_USERNAME", value=var.smtp_username }, { name="SMTP_PASSWORD", value=var.smtp_password },
      { name="SMTP_FROM", value=var.smtp_from }, { name="SMTP_USE_TLS", value=tostring(var.smtp_use_tls) },
      { name="PASSWORD_RESET_URL", value=var.password_reset_url }, { name="EMAIL_VERIFICATION_URL", value=var.email_verification_url }
    ]
    logConfiguration = { logDriver="awslogs", options={ awslogs-group=aws_cloudwatch_log_group.backend.name, awslogs-region=var.aws_region, awslogs-stream-prefix="backend" } }
  }])
}
resource "aws_ecs_service" "frontend" {
  name = "${local.name}-frontend"; cluster = aws_ecs_cluster.this.id; task_definition = aws_ecs_task_definition.frontend.arn
  desired_count = 2; launch_type = "FARGATE"
  network_configuration { subnets=aws_subnet.private[*].id; security_groups=[aws_security_group.ecs.id]; assign_public_ip=false }
  load_balancer { target_group_arn=aws_lb_target_group.frontend.arn; container_name="frontend"; container_port=3000 }
  depends_on = [aws_lb_listener.http]
}
resource "aws_ecs_service" "backend" {
  name = "${local.name}-backend"; cluster = aws_ecs_cluster.this.id; task_definition = aws_ecs_task_definition.backend.arn
  desired_count = 2; launch_type = "FARGATE"
  network_configuration { subnets=aws_subnet.private[*].id; security_groups=[aws_security_group.ecs.id]; assign_public_ip=false }
  load_balancer { target_group_arn=aws_lb_target_group.backend.arn; container_name="backend"; container_port=8000 }
  depends_on = [aws_lb_listener.http]
}
