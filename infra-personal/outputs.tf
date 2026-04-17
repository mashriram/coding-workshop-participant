output "cloudfront_domain" {
  value = aws_cloudfront_distribution.s3_distribution.domain_name
}

output "api_url" {
  value = trimsuffix(aws_apigatewayv2_stage.default.invoke_url, "/")
}

output "s3_bucket" {
  value = aws_s3_bucket.frontend.bucket
}

output "db_address" {
  value = aws_db_instance.postgres.address
}
