terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  default_tags {
    tags = {
      Project   = "coding-workshop-personal"
      ManagedBy = "Terraform"
    }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
