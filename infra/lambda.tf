# Execution role: Lambda may only write its own logs.
resource "aws_iam_role" "lambda" {
  name = "${var.project}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Created before the function, otherwise Lambda creates its own group that never expires.
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project}"
  retention_in_days = 7
}

# Look up the pushed image's digest, so `terraform apply` redeploys after a new push of the same tag.
data "aws_ecr_image" "app" {
  repository_name = aws_ecr_repository.app.name
  image_tag       = var.image_tag
}

resource "aws_lambda_function" "app" {
  function_name = var.project
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}@${data.aws_ecr_image.app.image_digest}"
  architectures = ["x86_64"] # build with: docker buildx build --platform linux/amd64 --provenance=false

  memory_size = 1024 # more memory = more CPU = faster pandas/sklearn cold start
  timeout     = 30

  reserved_concurrent_executions = var.reserved_concurrency

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_logs,
  ]
}

# Public HTTPS endpoint, no API Gateway needed.
resource "aws_lambda_function_url" "app" {
  function_name      = aws_lambda_function.app.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
  }
}

# Public Function URLs need both permissions (AWS change, late 2025).
resource "aws_lambda_permission" "url_invoke_url" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.app.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "url_invoke_function" {
  statement_id             = "FunctionURLInvokeAllowPublicAccess"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.app.function_name
  principal                = "*"
  invoked_via_function_url = true
}
