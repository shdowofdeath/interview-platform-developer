terraform {
  backend "s3" {
    bucket = "nightjar-tfstate"
    key    = "nightjar-ingest/terraform.tfstate"
    region = "eu-west-1"
  }

  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}
