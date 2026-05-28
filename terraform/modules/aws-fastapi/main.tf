variable "aws_region" {
  description = "AWS region."
  type        = string
}

variable "ecr_repo_name" {
  description = "AWS ECR repository name."
  type        = string
}

variable "app_runner_name" {
  description = "AWS App Runner service name."
  type        = string
}

variable "image_tag" {
  description = "Docker image tag."
  type        = string
}

resource "aws_ecr_repository" "repo" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_iam_role" "apprunner_ecr_access" {
  name = "${var.app_runner_name}-ecr-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access_policy" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_apprunner_service" "service" {
  service_name = var.app_runner_name

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.repo.repository_url}:${var.image_tag}"
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"
      }
    }

    auto_deployments_enabled = false
  }

  depends_on = [
    aws_iam_role_policy_attachment.apprunner_ecr_access_policy
  ]
}

output "ecr_repository_url" {
  value = aws_ecr_repository.repo.repository_url
}

output "app_runner_url" {
  value = "https://${aws_apprunner_service.service.service_url}"
}