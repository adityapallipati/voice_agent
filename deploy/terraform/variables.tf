variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "voice-agent"
}

variable "environment" {
  description = "Deployment environment (production, staging, development)"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "ecr_repository_url" {
  description = "ECR repository URL for container images"
  type        = string
}

variable "image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "latest"
}

variable "vapi_api_key" {
  description = "VAPI API key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
}

variable "n8n_url" {
  description = "URL for N8N instance"
  type        = string
  default     = "http://n8n.example.com"
}

variable "secret_key" {
  description = "Secret key for application security"
  type        = string
  sensitive   = true
}

variable "certificate_arn" {
  description = "ARN of ACM certificate for HTTPS"
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the API"
  type        = string
  default     = "api.voice-agent.example.com"
}

variable "service_desired_count" {
  description = "Desired number of tasks running in the service"
  type        = number
  default     = 2
}