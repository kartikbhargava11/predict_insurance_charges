resource "aws_ecr_repository" "app" {
  name                 = var.project
  image_tag_mutability = "MUTABLE" # so "latest" can be pushed again
  force_delete         = true      # lets `terraform destroy` remove the repo with images in it

  image_scanning_configuration {
    scan_on_push = true # basic scanning is free
  }
}

# Keep storage under the 500 MB free tier: only the last 2 images survive.
# No "delete untagged" rule: after a push the old image is untagged but Lambda
# may still run it (until the next apply), so it must not be expired early.
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 2 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 2
        }
        action = { type = "expire" }
      },
    ]
  })
}
