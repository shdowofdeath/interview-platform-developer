data "aws_iam_policy_document" "assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${var.account_id}:oidc-provider/${var.oidc_provider}"]
    }

    condition {
      test     = "StringLike"
      variable = "${var.oidc_provider}:sub"
      values   = ["system:serviceaccount:*:*"]
    }
  }
}

resource "aws_iam_role" "nightjar_ingest" {
  name               = "nightjar-ingest-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "nightjar_ingest" {
  statement {
    effect    = "Allow"
    actions   = ["s3:*"]
    resources = ["*"]
  }

  statement {
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "nightjar_ingest" {
  name   = "nightjar-ingest-${var.environment}"
  role   = aws_iam_role.nightjar_ingest.id
  policy = data.aws_iam_policy_document.nightjar_ingest.json
}

resource "aws_secretsmanager_secret" "reputation_api_key" {
  name = "nightjar/${var.environment}/reputation-api-key"
}

resource "aws_secretsmanager_secret_version" "reputation_api_key" {
  secret_id     = aws_secretsmanager_secret.reputation_api_key.id
  secret_string = var.reputation_api_key
}
