variable "project_name" {
  description = "Project name used for resource naming."
  type        = string
  default     = "fastapi-demo-hema"
}

variable "azure_location" {
  description = "Azure region."
  type        = string
  default     = "southeastasia"
}

variable "azure_resource_group_name" {
  description = "Azure resource group name."
  type        = string
  default     = "rg-fastapi-multicloud"
}

variable "azure_acr_name" {
  description = "Azure Container Registry name. Must be globally unique and only contain letters and numbers."
  type        = string
  default     = "fastapiacrhema001"
}

variable "azure_web_app_name" {
  description = "Azure Web App name. Must be globally unique."
  type        = string
  default     = "fastapi-azure-hema001"
}

variable "aws_region" {
  description = "AWS region."
  type        = string
  default     = "ap-southeast-1"
}

variable "aws_ecr_repo_name" {
  description = "AWS ECR repository name."
  type        = string
  default     = "fastapi-api"
}

variable "aws_app_runner_name" {
  description = "AWS App Runner service name."
  type        = string
  default     = "fastapi-aws-hema"
}

variable "image_name" {
  description = "Docker image name."
  type        = string
  default     = "fastapi-api"
}

variable "image_tag" {
  description = "Docker image tag."
  type        = string
  default     = "latest"
}