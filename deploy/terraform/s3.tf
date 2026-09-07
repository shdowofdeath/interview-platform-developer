resource "aws_kms_key" "feed_archive" {
  description           = "Nightjar feed archive"
  enable_key_rotation   = false
  deletion_window_in_days = 7

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "kms:*"
        Resource  = "*"
      }
    ]
  })
}

resource "aws_s3_bucket" "feed_archive" {
  bucket        = "${var.feed_archive_bucket}-${var.environment}"
  force_destroy = true
}

resource "aws_s3_bucket_acl" "feed_archive" {
  bucket = aws_s3_bucket.feed_archive.id
  acl    = "private"
}

resource "aws_s3_bucket_lifecycle_configuration" "feed_archive" {
  bucket = aws_s3_bucket.feed_archive.id

  rule {
    id     = "expire-raw-feeds"
    status = "Enabled"

    expiration {
      days = 3650
    }
  }
}

output "feed_archive_bucket" {
  value = aws_s3_bucket.feed_archive.id
}

output "ingest_role_arn" {
  value = aws_iam_role.nightjar_ingest.arn
}

output "reputation_api_key" {
  value = var.reputation_api_key
}
