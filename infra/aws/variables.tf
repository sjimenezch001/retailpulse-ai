variable "aws_region" {
  type    = string
  default = "sa-east-1"
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "Select exactly one reviewed region."
  }
}
variable "aws_profile" {
  type    = string
  default = "offline-not-configured"
}
variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Select one account explicitly."
  }
}
variable "environment" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,16}$", var.environment))
    error_message = "Use a short explicit lab environment."
  }
}
variable "expires_on" {
  type = string
  validation {
    condition     = can(formatdate("YYYY-MM-DD", "${var.expires_on}T00:00:00Z"))
    error_message = "An ISO expiry date is required; tags do not delete resources."
  }
}
variable "run_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{24}$", var.run_id))
    error_message = "Use the exact prepared run identity."
  }
}
variable "code_digest" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.code_digest))
    error_message = "Use the code checksum from prepare."
  }
}
variable "enable_endpoint" {
  type    = bool
  default = false
}
variable "lambda_bundle" {
  type    = string
  default = "../../artifacts/rp12/prepared/lambda.zip"
}
