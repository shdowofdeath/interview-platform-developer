terraform {
  backend "local" {
    path = ".terraform/interview.tfstate"
  }
}

provider "aws" {
  region = var.region

  access_key = "mock"
  secret_key = "mock"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
}
