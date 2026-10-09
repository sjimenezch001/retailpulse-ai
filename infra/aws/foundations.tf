# Read-only owner foundations: no managed bucket/IAM resources.
data "aws_s3_bucket" "owner" {
  bucket = var.owner_bucket_name
  lifecycle {
    postcondition {
      condition     = self.arn == local.bucket_arn && self.bucket_region == var.aws_region
      error_message = "The exact owner bucket must exist in the selected region."
    }
  }
}
data "aws_s3_bucket_policy" "owner" {
  bucket = var.owner_bucket_name
  lifecycle {
    postcondition {
      condition     = sha256(jsonencode(jsondecode(self.policy))) == var.bucket_policy_sha256
      error_message = "Owner TLS/encryption policy must match fresh verification."
    }
  }
}
data "aws_iam_role" "owner_glue" {
  name = local.glue_role
  lifecycle {
    postcondition {
      condition = (
        self.arn == var.owner_glue_role_arn && self.path == "/" &&
        self.permissions_boundary == var.owner_glue_boundary_arn &&
        jsondecode(self.assume_role_policy) == local.glue_trust &&
        alltrue([for key, value in local.identity_tags : lookup(self.tags, key, "") == value])
      )
      error_message = "Owner Glue identity, boundary, tags and fixed trust must match."
    }
  }
}
data "aws_iam_policy" "owner_boundary" {
  arn = var.owner_glue_boundary_arn
  lifecycle {
    postcondition {
      condition = (
        self.arn == var.owner_glue_boundary_arn &&
        sha256(jsonencode(jsondecode(self.policy))) == var.boundary_policy_sha256
      )
      error_message = "Owner boundary must match the reviewed current run."
    }
  }
}
