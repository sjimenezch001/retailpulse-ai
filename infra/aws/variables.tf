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
  validation {
    condition     = var.enable_endpoint == false
    error_message = "Lambda and API Gateway are deferred in RP-12C."
  }
}
variable "owner_bucket_name" {
  type = string
  validation {
    condition     = var.owner_bucket_name == "retailpulse-${var.environment}-${var.account_id}-${var.aws_region}"
    error_message = "Reference only the exact owner-managed lab bucket."
  }
}
variable "owner_glue_role_arn" {
  type = string
  validation {
    condition     = var.owner_glue_role_arn == "arn:aws:iam::${var.account_id}:role/retailpulse-${var.environment}-glue"
    error_message = "Reference only the fixed root-path owner Glue role."
  }
}
variable "owner_glue_boundary_arn" {
  type = string
  validation {
    condition     = var.owner_glue_boundary_arn == "arn:aws:iam::${var.account_id}:policy/retailpulse-${var.environment}-glue-boundary"
    error_message = "Reference only the exact owner-managed Glue boundary."
  }
}
variable "bucket_policy_sha256" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.bucket_policy_sha256))
    error_message = "Use the checksum from fresh read-only foundation verification."
  }
}
variable "boundary_policy_sha256" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.boundary_policy_sha256))
    error_message = "Use the reviewed current-run execution boundary checksum."
  }
}
