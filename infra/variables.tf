variable "region" {
  description = "AWS region for all resources."
  type        = string
  default     = "eu-central-1"
}

variable "project" {
  description = "Name used for the ECR repo, Lambda function and other resources."
  type        = string
  default     = "insurance-api"
}

variable "image_tag" {
  description = "Tag of the image in ECR that Lambda runs."
  type        = string
  default     = "latest"
}

variable "alert_email" {
  description = "Email that receives the error alarm and budget alerts."
  type        = string
}

variable "budget_limit" {
  description = "Monthly budget limit. 5 EUR, or about 6 if the account bills in USD."
  type        = string
  default     = "5"
}

variable "budget_unit" {
  description = "Budget currency. Must match the account's billing currency (EUR or USD)."
  type        = string
  default     = "EUR"
}

variable "reserved_concurrency" {
  description = "Max parallel Lambda runs (abuse guard). null = no limit; new accounts often cannot reserve any."
  type        = number
  default     = null
}
