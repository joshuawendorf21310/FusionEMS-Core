output "docs_bucket_name" {
  description = "Name of the documents S3 bucket"
  value       = aws_s3_bucket.this["docs"].id
}

output "exports_bucket_name" {
  description = "Name of the exports S3 bucket"
  value       = aws_s3_bucket.this["exports"].id
}

output "proposals_bucket_name" {
  description = "Name of the proposals S3 bucket"
  value       = aws_s3_bucket.this["proposals"].id
}

output "audit_bucket_name" {
  description = "Name of the audit S3 bucket"
  value       = aws_s3_bucket.this["audit"].id
}

output "artifacts_bucket_name" {
  description = "Name of the artifacts S3 bucket"
  value       = aws_s3_bucket.this["artifacts"].id
}

output "docs_bucket_arn" {
  description = "ARN of the documents S3 bucket"
  value       = aws_s3_bucket.this["docs"].arn
}

output "exports_bucket_arn" {
  description = "ARN of the exports S3 bucket"
  value       = aws_s3_bucket.this["exports"].arn
}

output "proposals_bucket_arn" {
  description = "ARN of the proposals S3 bucket"
  value       = aws_s3_bucket.this["proposals"].arn
}

output "audit_bucket_arn" {
  description = "ARN of the audit S3 bucket"
  value       = aws_s3_bucket.this["audit"].arn
}

output "artifacts_bucket_arn" {
  description = "ARN of the artifacts S3 bucket"
  value       = aws_s3_bucket.this["artifacts"].arn
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for S3 encryption"
  value       = aws_kms_key.s3.arn
}
