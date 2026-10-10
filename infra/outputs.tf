output "ecr_repository_url" {
  description = "Push the Docker image here."
  value       = aws_ecr_repository.app.repository_url
}
