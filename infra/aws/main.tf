locals {
  name       = "retailpulse-${var.environment}"
  bucket     = var.owner_bucket_name
  bucket_arn = "arn:aws:s3:::${local.name}-${var.account_id}-${var.aws_region}"
  lab_id     = substr(sha256("${var.account_id}:${var.aws_region}:${var.environment}"), 0, 16)
  database   = "rp_${replace(var.environment, "-", "_")}"
  glue_role  = "${local.name}-glue"
  log_prefix = "/retailpulse/${var.environment}/glue"
  log_names  = ["${local.log_prefix}/error", "${local.log_prefix}/output"]
  identity_tags = {
    Project = "RetailPulseAI", Environment = var.environment,
    LabId   = local.lab_id, Stage = "RP12C"
  }
  tags = merge(local.identity_tags, { ExpiresOn = var.expires_on })
  glue_trust = {
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow", Principal = { Service = "glue.amazonaws.com" }, Action = "sts:AssumeRole",
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.account_id },
        ArnLike      = { "aws:SourceArn" = "arn:aws:glue:${var.aws_region}:${var.account_id}:*" }
      }
    }]
  }
}
resource "aws_cloudwatch_log_group" "lab" {
  for_each          = toset(local.log_names)
  name              = each.value
  retention_in_days = 3
}
resource "aws_glue_job" "lab" {
  name                    = local.name
  role_arn                = data.aws_iam_role.owner_glue.arn
  glue_version            = "5.0"
  worker_type             = "G.1X"
  number_of_workers       = 2
  timeout                 = 5
  max_retries             = 0
  execution_class         = "STANDARD"
  job_run_queuing_enabled = false
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
  depends_on = [data.aws_s3_bucket_policy.owner, data.aws_iam_policy.owner_boundary, aws_cloudwatch_log_group.lab]
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
