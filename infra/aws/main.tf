locals {
  name        = "retailpulse-${var.environment}"
  bucket      = "${local.name}-${var.account_id}-${var.aws_region}"
  bucket_arn  = "arn:aws:s3:::${local.bucket}"
  lab_id      = substr(sha256("${var.account_id}:${var.aws_region}:${var.environment}"), 0, 16)
  database    = "rp_${replace(var.environment, "-", "_")}"
  glue_role   = "${local.name}-glue"
  lambda_role = "${local.name}-metrics"
  role_path   = "/retailpulse/${var.environment}/"
  glue_arn    = "arn:aws:iam::${var.account_id}:role${local.role_path}${local.glue_role}"
  lambda_arn  = "arn:aws:iam::${var.account_id}:role${local.role_path}${local.lambda_role}"
  log_prefix  = "/retailpulse/${var.environment}/glue"
  tags = {
    Project = "RetailPulseAI", Environment = var.environment, LabId = local.lab_id
    Stage   = "RP12A", ExpiresOn = var.expires_on
  }
  log_names = concat(
    ["${local.log_prefix}/error", "${local.log_prefix}/output"],
    var.enable_endpoint ? ["/aws/lambda/${local.lambda_role}", "/retailpulse/${var.environment}/api"] : []
  )
}
resource "aws_s3_bucket" "lab" {
  bucket        = local.bucket
  force_destroy = false
}
resource "aws_s3_bucket_public_access_block" "lab" {
  bucket                  = aws_s3_bucket.lab.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_ownership_controls" "lab" {
  bucket = aws_s3_bucket.lab.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "lab" {
  bucket = aws_s3_bucket.lab.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_versioning" "lab" {
  bucket = aws_s3_bucket.lab.id
  versioning_configuration {
    status = "Enabled"
  }
}
resource "aws_s3_bucket_policy" "lab" {
  bucket = aws_s3_bucket.lab.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport", Effect = "Deny", Principal = "*"
      Action    = "s3:*", Resource = [local.bucket_arn, "${local.bucket_arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}
resource "aws_s3_bucket_lifecycle_configuration" "lab" {
  bucket     = aws_s3_bucket.lab.id
  depends_on = [aws_s3_bucket_versioning.lab]
  rule {
    id     = "temporary-results"
    status = "Enabled"
    filter { prefix = "results/" }
    expiration { days = 1 }
  }
  rule {
    id     = "bounded-lab-retention"
    status = "Enabled"
    filter {}
    expiration { days = 7 }
    noncurrent_version_expiration { noncurrent_days = 1 }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}
resource "aws_cloudwatch_log_group" "lab" {
  for_each          = toset(local.log_names)
  name              = each.value
  retention_in_days = 3
}
resource "aws_iam_role" "glue" {
  name = local.glue_role
  path = local.role_path
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow", Principal = { Service = "glue.amazonaws.com" }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:glue:${var.aws_region}:${var.account_id}:*" }
      }
    }]
  })
}
resource "aws_iam_role_policy" "glue" {
  name = "bounded-etl"
  role = aws_iam_role.glue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadApprovedInputAndCode", Effect = "Allow", Action = ["s3:GetObject"]
        Resource = ["${local.bucket_arn}/input/${var.run_id}/*", "${local.bucket_arn}/scripts/${var.run_id}/*"]
      },
      {
        Sid      = "OwnRunOnly", Effect = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
        Resource = ["${local.bucket_arn}/curated/${var.run_id}/*", "${local.bucket_arn}/temporary/${var.run_id}/*"]
      },
      {
        Sid      = "ListExactPrefixes", Effect = "Allow", Action = ["s3:ListBucket"]
        Resource = [local.bucket_arn]
        Condition = { StringLikeIfExists = { "s3:prefix" = [
          "input/${var.run_id}/*", "scripts/${var.run_id}/*",
          "curated/${var.run_id}/*", "temporary/${var.run_id}/*"
        ] } }
      },
      {
        Sid    = "BucketRegion", Effect = "Allow"
        Action = ["s3:GetBucketLocation"], Resource = [local.bucket_arn]
      },
      {
        Sid    = "ExistingLogGroupsOnly", Effect = "Allow"
        Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:${local.log_prefix}/error:*",
          "arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:${local.log_prefix}/output:*"
        ]
      }
    ]
  })
}
resource "aws_glue_security_configuration" "lab" {
  name = local.name
  encryption_configuration {
    s3_encryption { s3_encryption_mode = "SSE-S3" }
    cloudwatch_encryption { cloudwatch_encryption_mode = "DISABLED" }
    job_bookmarks_encryption { job_bookmarks_encryption_mode = "DISABLED" }
  }
}
resource "aws_glue_job" "lab" {
  name                    = local.name
  role_arn                = local.glue_arn
  glue_version            = "5.0"
  worker_type             = "G.1X"
  number_of_workers       = 2
  timeout                 = 5
  max_retries             = 0
  execution_class         = "STANDARD"
  job_run_queuing_enabled = false
  security_configuration  = aws_glue_security_configuration.lab.name
  execution_property { max_concurrent_runs = 1 }
  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${local.bucket}/scripts/${var.run_id}/glue_job.py"
  }
  non_overridable_arguments = {
    "--LAB_ACCOUNT"                  = var.account_id
    "--LAB_REGION"                   = var.aws_region
    "--LAB_ENV"                      = var.environment
    "--LAB_RUN_ID"                   = var.run_id
    "--CODE_DIGEST"                  = var.code_digest
    "--extra-py-files"               = "s3://${local.bucket}/scripts/${var.run_id}/glue_bundle.zip"
    "--TempDir"                      = "s3://${local.bucket}/temporary/${var.run_id}/"
    "--job-bookmark-option"          = "job-bookmark-disable"
    "--custom-logGroup-prefix"       = local.log_prefix
    "--enable-auto-scaling"          = "false"
    "--enable-spark-ui"              = "false"
    "--enable-job-insights"          = "false"
    "--enable-observability-metrics" = "false"
  }
  depends_on = [aws_iam_role_policy.glue, aws_cloudwatch_log_group.lab]
}
resource "aws_glue_catalog_database" "lab" {
  name       = local.database
  catalog_id = var.account_id
  parameters = { lab_id = local.lab_id, run_id = var.run_id }
}
resource "aws_glue_catalog_table" "lab" {
  for_each      = local.table_columns
  name          = each.key
  database_name = aws_glue_catalog_database.lab.name
  catalog_id    = var.account_id
  table_type    = "EXTERNAL_TABLE"
  parameters = {
    classification  = "parquet", EXTERNAL = "TRUE", synthetic = "true"
    dataset_version = "synthetic-web-v1", run_id = var.run_id, lab_id = local.lab_id
  }
  storage_descriptor {
    location      = "s3://${local.bucket}/curated/${var.run_id}/${each.key}/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }
    dynamic "columns" {
      for_each = each.value
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}
resource "aws_athena_workgroup" "lab" {
  name          = local.name
  force_destroy = false
  configuration {
    enforce_workgroup_configuration    = true
    bytes_scanned_cutoff_per_query     = 10485760
    publish_cloudwatch_metrics_enabled = false
    engine_version { selected_engine_version = "Athena engine version 3" }
    result_configuration {
      output_location       = "s3://${local.bucket}/results/"
      expected_bucket_owner = var.account_id
      encryption_configuration { encryption_option = "SSE_S3" }
    }
  }
}
