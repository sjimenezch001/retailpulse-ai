# Explicit mock provider in every test file. No live apply operations.
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_lambda_function" {
    defaults = {
      arn        = "arn:aws:lambda:sa-east-1:000000000000:function:retailpulse-offline-metrics"
      invoke_arn = "arn:aws:apigateway:sa-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:sa-east-1:000000000000:function:retailpulse-offline-metrics/invocations"
    }
  }
  mock_resource "aws_apigatewayv2_api" {
    defaults = {
      id            = "offlineapi"
      execution_arn = "arn:aws:execute-api:sa-east-1:000000000000:offlineapi"
      api_endpoint  = "https://offlineapi.execute-api.sa-east-1.amazonaws.com"
    }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = {
      arn = "arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/api"
    }
  }
}
variables {
  account_id  = "000000000000"
  environment = "offline"
  expires_on  = "2099-01-01"
  run_id      = "000000000000000000000000"
  code_digest = "0000000000000000000000000000000000000000000000000000000000000000"
}
run "private_bounded_data_lab" {
  command = plan
  assert {
    condition = (
      aws_s3_bucket_public_access_block.lab.block_public_acls &&
      aws_s3_bucket_public_access_block.lab.block_public_policy &&
      aws_s3_bucket_public_access_block.lab.ignore_public_acls &&
      aws_s3_bucket_public_access_block.lab.restrict_public_buckets &&
      aws_s3_bucket_ownership_controls.lab.rule[0].object_ownership == "BucketOwnerEnforced" &&
      !aws_s3_bucket.lab.force_destroy
    )
    error_message = "Storage must remain private, ACL-free and protected from implicit purge."
  }
  assert {
    condition = (
      aws_glue_job.lab.number_of_workers == 2 &&
      aws_glue_job.lab.worker_type == "G.1X" &&
      aws_glue_job.lab.glue_version == "5.0" &&
      aws_glue_job.lab.timeout == 5 &&
      aws_glue_job.lab.max_retries == 0 &&
      aws_glue_job.lab.execution_property[0].max_concurrent_runs == 1
    )
    error_message = "Glue worker/time/retry bounds changed."
  }
  assert {
    condition = (
      aws_athena_workgroup.lab.configuration[0].enforce_workgroup_configuration &&
      aws_athena_workgroup.lab.configuration[0].bytes_scanned_cutoff_per_query == 10485760 &&
      aws_athena_workgroup.lab.configuration[0].result_configuration[0].encryption_configuration[0].encryption_option == "SSE_S3" &&
      length(aws_apigatewayv2_route.metrics) == 0
    )
    error_message = "Athena must enforce cost/output encryption; endpoint defaults off."
  }
}
run "optional_iam_endpoint" {
  command = plan
  variables { enable_endpoint = true }
  assert {
    condition = (
      aws_apigatewayv2_route.metrics[0].authorization_type == "AWS_IAM" &&
      aws_apigatewayv2_route.metrics[0].route_key == "GET /metrics/units" &&
      aws_lambda_function.metrics[0].timeout == 5 &&
      aws_lambda_function.metrics[0].memory_size == 128 &&
      aws_apigatewayv2_stage.metrics[0].default_route_settings[0].throttling_rate_limit == 1
    )
    error_message = "Endpoint authentication and resource limits are mandatory."
  }
  assert {
    condition = (
      jsondecode(aws_iam_role_policy.metrics[0].policy).Statement[0].Action[0] == "s3:GetObject" &&
      length(jsondecode(aws_iam_role_policy.metrics[0].policy).Statement[0].Resource) == 1 &&
      length(output.execution_role_pass_permissions.Statement) == 2
    )
    error_message = "Lambda reads one metric artifact; PassRole stays service-scoped."
  }
}
run "reject_invalid_run" {
  command = plan
  variables { run_id = "../unapproved" }
  expect_failures = [var.run_id]
}

run "execution_roles_and_transport" {
  command = plan
  assert {
    condition = alltrue([
      for statement in jsondecode(aws_iam_role_policy.glue.policy).Statement :
      !contains(statement.Action, "*") &&
      !contains(statement.Action, "s3:*") &&
      !contains(statement.Action, "iam:PassRole") &&
      !contains(statement.Resource, "*")
    ])
    error_message = "Execution role actions/resources cannot become account-wide."
  }
  assert {
    condition = (
      jsondecode(aws_s3_bucket_policy.lab.policy).Statement[0].Effect == "Deny" &&
      jsondecode(aws_s3_bucket_policy.lab.policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false" &&
      one(aws_s3_bucket_server_side_encryption_configuration.lab.rule).apply_server_side_encryption_by_default[0].sse_algorithm == "AES256" &&
      alltrue([for group in aws_cloudwatch_log_group.lab : group.retention_in_days == 3])
    )
    error_message = "TLS, encryption and short explicit log retention are mandatory."
  }
  assert {
    condition = (
      output.execution_role_pass_permissions.Statement[0].Condition.StringEquals["iam:PassedToService"] == "glue.amazonaws.com" &&
      output.execution_role_pass_permissions.Statement[0].Resource[0] == local.glue_arn
    )
    error_message = "The future deployment role can pass only the exact Glue role to Glue."
  }
}
