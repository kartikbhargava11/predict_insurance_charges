output "ecr_repository_url" {
  description = "Push the Docker image here."
  value       = aws_ecr_repository.app.repository_url
}

output "function_name" {
  value = aws_lambda_function.app.function_name
}

output "function_url" {
  description = "Public API endpoint (ends with /)."
  value       = aws_lambda_function_url.app.function_url
}
