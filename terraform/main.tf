module "azure_fastapi" {
  source = "./modules/azure-fastapi"

  resource_group_name = var.azure_resource_group_name
  location            = var.azure_location
  acr_name            = var.azure_acr_name
  web_app_name        = var.azure_web_app_name
  image_name          = var.image_name
  image_tag           = var.image_tag
}

module "aws_fastapi" {
  source = "./modules/aws-fastapi"

  aws_region          = var.aws_region
  ecr_repo_name       = var.aws_ecr_repo_name
  app_runner_name     = var.aws_app_runner_name
  image_tag           = var.image_tag
}