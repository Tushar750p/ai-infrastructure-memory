output "alb_dns_name" { value=aws_lb.this.dns_name }
output "backend_ecr_repository_url" { value=aws_ecr_repository.backend.repository_url }
output "frontend_ecr_repository_url" { value=aws_ecr_repository.frontend.repository_url }
output "rds_endpoint" { value=aws_db_instance.this.address }
output "redis_endpoint" { value=aws_elasticache_replication_group.this.primary_endpoint_address }
output "ecs_cluster_name" { value=aws_ecs_cluster.this.name }
