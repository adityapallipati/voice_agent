# API URL
output "api_url" {
  description = "URL of the deployed API"
  value       = "https://${var.domain_name}"
}

# N8N URL
output "n8n_url" {
  description = "URL of the N8N instance"
  value       = "https://n8n.${var.domain_name}"
}

# Load Balancer DNS
output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

# DB Endpoint
output "db_endpoint" {
  description = "Endpoint of the RDS PostgreSQL database"
  value       = aws_db_instance.postgres.endpoint
}

# Redis Endpoint
output "redis_endpoint" {
  description = "Endpoint of the ElastiCache Redis cluster"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

# ECS Cluster 
output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

# ECS Service
output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.api.name
}

# ECR Repository
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = var.ecr_repository_url
}

# Used image tag
output "deployed_image_tag" {
  description = "Image tag that was deployed"
  value       = var.image_tag
}

# VPC ID
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

# Private Subnets
output "private_subnets" {
  description = "List of private subnet IDs"
  value       = module.vpc.private_subnets
}

# Public Subnets
output "public_subnets" {
  description = "List of public subnet IDs"
  value       = module.vpc.public_subnets
}

# CloudWatch Log Group
output "cloudwatch_log_group" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.ecs_logs.name
}

# Security Groups
output "api_security_group_id" {
  description = "ID of the API security group"
  value       = aws_security_group.api_sg.id
}

output "db_security_group_id" {
  description = "ID of the database security group"
  value       = aws_security_group.db_sg.id
}

output "redis_security_group_id" {
  description = "ID of the Redis security group"
  value       = aws_security_group.redis_sg.id
}

# Auto Scaling Configuration
output "auto_scaling_target_id" {
  description = "ID of the Application Auto Scaling target"
  value       = aws_appautoscaling_target.api.resource_id
}

# Route53 Record
output "route53_record_name" {
  description = "Domain name of the Route53 record"
  value       = aws_route53_record.api.name
}

# Resource counts
output "resource_counts" {
  description = "Count of various resources created"
  value = {
    private_subnets = length(module.vpc.private_subnets)
    public_subnets  = length(module.vpc.public_subnets)
    azs_used        = length(module.vpc.azs)
  }
}

# Current environment
output "environment" {
  description = "Current deployment environment"
  value       = var.environment
}

# Project name
output "project_name" {
  description = "Project name"
  value       = var.project_name
}