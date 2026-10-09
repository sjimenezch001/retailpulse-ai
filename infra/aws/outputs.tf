output "lab" {
  value = {
    account       = var.account_id, region = var.aws_region, environment = var.environment,
    lab_id        = local.lab_id, run_id = var.run_id, bucket = data.aws_s3_bucket.owner.bucket,
    database      = local.database, job = aws_glue_job.lab.name,
    workgroup     = aws_athena_workgroup.lab.name, tags = local.tags,
    glue_role     = local.glue_role, glue_role_arn = data.aws_iam_role.owner_glue.arn,
    boundary_arn  = data.aws_iam_policy.owner_boundary.arn,
    owner_managed = ["bucket", "glue_role", "glue_boundary"],
    lambda_role   = null, function = null, api_id = null, endpoint = null,
    log_groups    = local.log_names
  }
}
output "execution_role_pass_permissions" {
  description = "Exact Glue delegation for separate owner review; never attached automatically."
  value = {
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow", Action = ["iam:PassRole"], Resource = [var.owner_glue_role_arn],
      Condition = { StringEquals = { "iam:PassedToService" = "glue.amazonaws.com" } }
    }]
  }
}
