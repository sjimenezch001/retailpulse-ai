# All runs use the explicit mock provider; no real provider calls or apply.
mock_provider "aws" {
  override_during = plan
  mock_data "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1", bucket_region = "sa-east-1" }
  }
  mock_data "aws_s3_bucket_policy" {
    defaults = { policy = "{\"Version\": \"2012-10-17\", \"Statement\": [{\"Sid\": \"DenyInsecureTransport\", \"Effect\": \"Deny\", \"Principal\": \"*\", \"Action\": \"s3:*\", \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/*\"], \"Condition\": {\"Bool\": {\"aws:SecureTransport\": \"false\"}}}, {\"Sid\": \"DenyExplicitNonSseS3\", \"Effect\": \"Deny\", \"Principal\": \"*\", \"Action\": \"s3:PutObject\", \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/*\"], \"Condition\": {\"StringNotEquals\": {\"s3:x-amz-server-side-encryption\": \"AES256\"}, \"Null\": {\"s3:x-amz-server-side-encryption\": \"false\"}}}, {\"Sid\": \"DenyCustomerProvidedEncryption\", \"Effect\": \"Deny\", \"Principal\": \"*\", \"Action\": \"s3:PutObject\", \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/*\"], \"Condition\": {\"Null\": {\"s3:x-amz-server-side-encryption-customer-algorithm\": \"false\"}}}]}" }
  }
  mock_data "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::000000000000:role/retailpulse-offline-glue", path = "/", permissions_boundary = "arn:aws:iam::000000000000:policy/retailpulse-offline-glue-boundary",
    assume_role_policy = "{\"Version\": \"2012-10-17\", \"Statement\": [{\"Effect\": \"Allow\", \"Principal\": {\"Service\": \"glue.amazonaws.com\"}, \"Action\": \"sts:AssumeRole\", \"Condition\": {\"StringEquals\": {\"aws:SourceAccount\": \"000000000000\"}, \"ArnLike\": {\"aws:SourceArn\": \"arn:aws:glue:sa-east-1:000000000000:*\"}}}]}", tags = { "Project" : "RetailPulseAI", "Environment" : "offline", "LabId" : "2fb274a1f2a25a58", "Stage" : "RP12C" } }
  }
  mock_data "aws_iam_policy" {
    defaults = { arn = "arn:aws:iam::000000000000:policy/retailpulse-offline-glue-boundary", policy = "{\"Version\": \"2012-10-17\", \"Statement\": [{\"Sid\": \"ExplicitlyDenyEveryOtherAction\", \"Effect\": \"Deny\", \"NotAction\": [\"logs:CreateLogStream\", \"logs:PutLogEvents\", \"s3:AbortMultipartUpload\", \"s3:DeleteObject\", \"s3:GetBucketLocation\", \"s3:GetObject\", \"s3:ListBucket\", \"s3:ListMultipartUploadParts\", \"s3:PutObject\"], \"Resource\": \"*\"}, {\"Sid\": \"Execution1\", \"Effect\": \"Allow\", \"Action\": [\"s3:GetObject\"], \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/input/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/scripts/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/curated/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/temporary/000000000000000000000000/*\"], \"Condition\": {\"StringEquals\": {\"s3:ResourceAccount\": \"000000000000\"}}}, {\"Sid\": \"Execution2\", \"Effect\": \"Allow\", \"Action\": [\"s3:PutObject\", \"s3:DeleteObject\", \"s3:AbortMultipartUpload\", \"s3:ListMultipartUploadParts\"], \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/curated/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/temporary/000000000000000000000000/*\"], \"Condition\": {\"StringEquals\": {\"s3:ResourceAccount\": \"000000000000\"}}}, {\"Sid\": \"Execution3\", \"Effect\": \"Allow\", \"Action\": [\"s3:ListBucket\", \"s3:GetBucketLocation\"], \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1\"], \"Condition\": {\"StringEquals\": {\"s3:ResourceAccount\": \"000000000000\"}}}, {\"Sid\": \"Execution4\", \"Effect\": \"Allow\", \"Action\": [\"logs:CreateLogStream\", \"logs:PutLogEvents\"], \"Resource\": [\"arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/glue/error:log-stream:*\", \"arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/glue/output:log-stream:*\"]}, {\"Sid\": \"DenyOutsideExecutionScope1\", \"Effect\": \"Deny\", \"Action\": [\"s3:GetObject\"], \"NotResource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/input/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/scripts/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/curated/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/temporary/000000000000000000000000/*\"]}, {\"Sid\": \"DenyOutsideExecutionScope2\", \"Effect\": \"Deny\", \"Action\": [\"s3:PutObject\", \"s3:DeleteObject\", \"s3:AbortMultipartUpload\", \"s3:ListMultipartUploadParts\"], \"NotResource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/curated/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/temporary/000000000000000000000000/*\"]}, {\"Sid\": \"DenyOutsideExecutionScope3\", \"Effect\": \"Deny\", \"Action\": [\"s3:ListBucket\", \"s3:GetBucketLocation\"], \"NotResource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1\"]}, {\"Sid\": \"DenyOutsideExecutionScope4\", \"Effect\": \"Deny\", \"Action\": [\"logs:CreateLogStream\", \"logs:PutLogEvents\"], \"NotResource\": [\"arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/glue/error:log-stream:*\", \"arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/glue/output:log-stream:*\"]}, {\"Sid\": \"DenyWrongS3Owner\", \"Effect\": \"Deny\", \"Action\": [\"s3:AbortMultipartUpload\", \"s3:DeleteObject\", \"s3:GetBucketLocation\", \"s3:GetObject\", \"s3:ListBucket\", \"s3:ListMultipartUploadParts\", \"s3:PutObject\"], \"Resource\": [\"*\"], \"Condition\": {\"StringNotEquals\": {\"s3:ResourceAccount\": \"000000000000\"}}}]}" }
  }
}
variables {
  account_id              = "000000000000"
  environment             = "offline"
  expires_on              = "2099-01-01"
  run_id                  = "000000000000000000000000"
  code_digest             = "0000000000000000000000000000000000000000000000000000000000000000"
  owner_bucket_name       = "retailpulse-offline-000000000000-sa-east-1"
  owner_glue_role_arn     = "arn:aws:iam::000000000000:role/retailpulse-offline-glue"
  owner_glue_boundary_arn = "arn:aws:iam::000000000000:policy/retailpulse-offline-glue-boundary"
  bucket_policy_sha256    = sha256(jsonencode(jsondecode("{\"Version\": \"2012-10-17\", \"Statement\": [{\"Sid\": \"DenyInsecureTransport\", \"Effect\": \"Deny\", \"Principal\": \"*\", \"Action\": \"s3:*\", \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/*\"], \"Condition\": {\"Bool\": {\"aws:SecureTransport\": \"false\"}}}, {\"Sid\": \"DenyExplicitNonSseS3\", \"Effect\": \"Deny\", \"Principal\": \"*\", \"Action\": \"s3:PutObject\", \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/*\"], \"Condition\": {\"StringNotEquals\": {\"s3:x-amz-server-side-encryption\": \"AES256\"}, \"Null\": {\"s3:x-amz-server-side-encryption\": \"false\"}}}, {\"Sid\": \"DenyCustomerProvidedEncryption\", \"Effect\": \"Deny\", \"Principal\": \"*\", \"Action\": \"s3:PutObject\", \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/*\"], \"Condition\": {\"Null\": {\"s3:x-amz-server-side-encryption-customer-algorithm\": \"false\"}}}]}")))
  boundary_policy_sha256  = sha256(jsonencode(jsondecode("{\"Version\": \"2012-10-17\", \"Statement\": [{\"Sid\": \"ExplicitlyDenyEveryOtherAction\", \"Effect\": \"Deny\", \"NotAction\": [\"logs:CreateLogStream\", \"logs:PutLogEvents\", \"s3:AbortMultipartUpload\", \"s3:DeleteObject\", \"s3:GetBucketLocation\", \"s3:GetObject\", \"s3:ListBucket\", \"s3:ListMultipartUploadParts\", \"s3:PutObject\"], \"Resource\": \"*\"}, {\"Sid\": \"Execution1\", \"Effect\": \"Allow\", \"Action\": [\"s3:GetObject\"], \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/input/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/scripts/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/curated/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/temporary/000000000000000000000000/*\"], \"Condition\": {\"StringEquals\": {\"s3:ResourceAccount\": \"000000000000\"}}}, {\"Sid\": \"Execution2\", \"Effect\": \"Allow\", \"Action\": [\"s3:PutObject\", \"s3:DeleteObject\", \"s3:AbortMultipartUpload\", \"s3:ListMultipartUploadParts\"], \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/curated/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/temporary/000000000000000000000000/*\"], \"Condition\": {\"StringEquals\": {\"s3:ResourceAccount\": \"000000000000\"}}}, {\"Sid\": \"Execution3\", \"Effect\": \"Allow\", \"Action\": [\"s3:ListBucket\", \"s3:GetBucketLocation\"], \"Resource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1\"], \"Condition\": {\"StringEquals\": {\"s3:ResourceAccount\": \"000000000000\"}}}, {\"Sid\": \"Execution4\", \"Effect\": \"Allow\", \"Action\": [\"logs:CreateLogStream\", \"logs:PutLogEvents\"], \"Resource\": [\"arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/glue/error:log-stream:*\", \"arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/glue/output:log-stream:*\"]}, {\"Sid\": \"DenyOutsideExecutionScope1\", \"Effect\": \"Deny\", \"Action\": [\"s3:GetObject\"], \"NotResource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/input/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/scripts/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/curated/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/temporary/000000000000000000000000/*\"]}, {\"Sid\": \"DenyOutsideExecutionScope2\", \"Effect\": \"Deny\", \"Action\": [\"s3:PutObject\", \"s3:DeleteObject\", \"s3:AbortMultipartUpload\", \"s3:ListMultipartUploadParts\"], \"NotResource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/curated/000000000000000000000000/*\", \"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1/temporary/000000000000000000000000/*\"]}, {\"Sid\": \"DenyOutsideExecutionScope3\", \"Effect\": \"Deny\", \"Action\": [\"s3:ListBucket\", \"s3:GetBucketLocation\"], \"NotResource\": [\"arn:aws:s3:::retailpulse-offline-000000000000-sa-east-1\"]}, {\"Sid\": \"DenyOutsideExecutionScope4\", \"Effect\": \"Deny\", \"Action\": [\"logs:CreateLogStream\", \"logs:PutLogEvents\"], \"NotResource\": [\"arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/glue/error:log-stream:*\", \"arn:aws:logs:sa-east-1:000000000000:log-group:/retailpulse/offline/glue/output:log-stream:*\"]}, {\"Sid\": \"DenyWrongS3Owner\", \"Effect\": \"Deny\", \"Action\": [\"s3:AbortMultipartUpload\", \"s3:DeleteObject\", \"s3:GetBucketLocation\", \"s3:GetObject\", \"s3:ListBucket\", \"s3:ListMultipartUploadParts\", \"s3:PutObject\"], \"Resource\": [\"*\"], \"Condition\": {\"StringNotEquals\": {\"s3:ResourceAccount\": \"000000000000\"}}}]}")))
}
run "owner_foundations_are_only_references" {
  command = plan
  assert {
    condition     = output.lab.owner_managed == ["bucket", "glue_role", "glue_boundary"] && output.lab.glue_role_arn == var.owner_glue_role_arn && data.aws_s3_bucket.owner.bucket == var.owner_bucket_name
    error_message = "Foundation identity and lifecycle must remain owner-managed."
  }
  assert {
    condition     = aws_glue_job.lab.role_arn == var.owner_glue_role_arn && (aws_glue_job.lab.security_configuration == null || aws_glue_job.lab.security_configuration == "")
    error_message = "Use the fixed owner role and omit regional security configuration mutation."
  }
}
run "bounded_data_workloads" {
  command = plan
  assert {
    condition     = aws_glue_job.lab.number_of_workers == 2 && aws_glue_job.lab.worker_type == "G.1X" && aws_glue_job.lab.timeout == 5 && aws_glue_job.lab.max_retries == 0 && aws_glue_job.lab.execution_property[0].max_concurrent_runs == 1
    error_message = "Glue worker, timeout and concurrency bounds are mandatory."
  }
  assert {
    condition     = aws_athena_workgroup.lab.configuration[0].enforce_workgroup_configuration && aws_athena_workgroup.lab.configuration[0].bytes_scanned_cutoff_per_query == 10485760 && aws_athena_workgroup.lab.configuration[0].result_configuration[0].encryption_configuration[0].encryption_option == "SSE_S3" && alltrue([for group in aws_cloudwatch_log_group.lab : group.retention_in_days == 3])
    error_message = "Athena encryption/scan limits and log retention must remain bounded."
  }
  assert {
    condition     = length(output.execution_role_pass_permissions.Statement) == 1 && output.execution_role_pass_permissions.Statement[0].Resource == [var.owner_glue_role_arn] && output.execution_role_pass_permissions.Statement[0].Condition.StringEquals["iam:PassedToService"] == "glue.amazonaws.com" && output.lab.api_id == null && output.lab.lambda_role == null
    error_message = "Only Glue delegation is permitted; endpoint must remain disabled."
  }
}
run "reject_endpoint_enablement" {
  command = plan
  variables { enable_endpoint = true }
  expect_failures = [var.enable_endpoint]
}
run "reject_invalid_run" {
  command = plan
  variables { run_id = "../unapproved" }
  expect_failures = [var.run_id]
}
run "reject_untrusted_bucket" {
  command = plan
  variables { owner_bucket_name = "untrusted" }
  expect_failures = [var.owner_bucket_name]
}
run "reject_wrong_role" {
  command = plan
  variables { owner_glue_role_arn = "arn:aws:iam::000000000000:role/other" }
  expect_failures = [var.owner_glue_role_arn]
}

run "reject_incompatible_foundation" {
  command = plan
  override_data {
    target = data.aws_iam_role.owner_glue
    values = { arn = "arn:aws:iam::000000000000:role/other", path = "/", permissions_boundary = "untrusted", assume_role_policy = "{}", tags = {} }
  }
  expect_failures = [data.aws_iam_role.owner_glue]
}
