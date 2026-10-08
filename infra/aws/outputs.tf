output "lab" {
  value = {
    account     = var.account_id, region = var.aws_region, environment = var.environment,
    lab_id      = local.lab_id, run_id = var.run_id, bucket = local.bucket,
    database    = local.database, job = aws_glue_job.lab.name,
    workgroup   = aws_athena_workgroup.lab.name, tags = local.tags,
    glue_role   = local.glue_role,
    lambda_role = var.enable_endpoint ? local.lambda_role : null,
    log_groups  = local.log_names,
    api_id      = var.enable_endpoint ? aws_apigatewayv2_api.metrics[0].id : null,
    endpoint    = var.enable_endpoint ? aws_apigatewayv2_api.metrics[0].api_endpoint : null,
    function    = var.enable_endpoint ? aws_lambda_function.metrics[0].function_name : null
  }
}
output "execution_role_pass_permissions" {
  description = "Review for a separate deployment identity; not automatically attached."
  value = {
    Version = "2012-10-17"
    Statement = concat(
      [{
        Effect    = "Allow", Action = ["iam:PassRole"], Resource = [local.glue_arn],
        Condition = { StringEquals = { "iam:PassedToService" = "glue.amazonaws.com" } }
      }],
      var.enable_endpoint ? [{
        Effect    = "Allow", Action = ["iam:PassRole"], Resource = [local.lambda_arn],
        Condition = { StringEquals = { "iam:PassedToService" = "lambda.amazonaws.com" } }
      }] : []
    )
  }
}
