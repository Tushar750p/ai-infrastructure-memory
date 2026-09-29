output "alb_dns_name" { value=aws_lb.this.dns_name }
output "backend_ecr_repository_url" { value=aws_ecr_repository.backend.repository_url }
output "frontend_ecr_repository_url" { value=aws_ecr_repository.frontend.repository_url }
output "rds_endpoint" { value=aws_db_instance.this.address }
output "redis_endpoint" { value=aws_elasticache_replication_group.this.primary_endpoint_address }
output "ecs_cluster_name" { value=aws_ecs_cluster.this.name }
output "private_subnet_ids" { value=aws_subnet.private[*].id }
output "ecs_security_group_id" { value=aws_security_group.ecs.id }
output "migration_task_definition" { value=aws_ecs_task_definition.migrate.arn }
output "rds_master_user_secret_arn" { value=aws_db_instance.this.master_user_secret[0].secret_arn }

output "ecs_frontend_service_name" { value=aws_ecs_service.frontend.name }
output "ecs_backend_service_name" { value=aws_ecs_service.backend.name }
