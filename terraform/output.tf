output "azure_acr_login_server" {
  description = "Azure Container Registry login server."
  value       = module.azure_fastapi.acr_login_server
}

output "azure_web_app_url" {
  description = "Azure Web App URL."
  value       = module.azure_fastapi.web_app_url
}

output "aws_ecr_repository_url" {
  description = "AWS ECR repository URL."
  value       = module.aws_fastapi.ecr_repository_url
}

output "aws_app_runner_url" {
  description = "AWS App Runner service URL."
  value       = module.aws_fastapi.app_runner_url
}