variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "account_id" {
  type    = string
  default = "111122223333"
}

variable "oidc_provider" {
  type    = string
  default = "oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
}

variable "feed_archive_bucket" {
  type    = string
  default = "nightjar-feed-archive"
}

variable "reputation_api_key" {
  type    = string
  default = "rep_live_7f4a2c9e1b8d6350a1f2"
}
