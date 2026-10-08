resource "aws_iam_role" "metrics" {
  count = var.enable_endpoint ? 1 : 0
  name  = local.lambda_role
  path  = local.role_path
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy" "metrics" {
  count = var.enable_endpoint ? 1 : 0
  name  = "read-one-metric"
  role  = aws_iam_role.metrics[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow", Action = ["s3:GetObject"]
        Resource = ["${local.bucket_arn}/serving/${var.run_id}/units.json"]
      },
      {
        Effect   = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = ["arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:/aws/lambda/${local.lambda_role}:*"]
      }
    ]
  })
}
resource "aws_lambda_function" "metrics" {
  count            = var.enable_endpoint ? 1 : 0
  function_name    = local.lambda_role
  role             = local.lambda_arn
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  handler          = "cloud.aws.lambda_handler.handler"
  filename         = var.lambda_bundle
  source_code_hash = filebase64sha256(var.lambda_bundle)
  memory_size      = 128
  timeout          = 5
  # Reserved/provisioned concurrency omitted: account eligibility unverified.
  environment {
    variables = {
      LAB_ACCOUNT = var.account_id, LAB_REGION = var.aws_region,
      LAB_ENV     = var.environment, LAB_RUN_ID = var.run_id
    }
  }
  logging_config { log_format = "JSON" }
  depends_on = [aws_iam_role_policy.metrics, aws_cloudwatch_log_group.lab]
}
resource "aws_apigatewayv2_api" "metrics" {
  count         = var.enable_endpoint ? 1 : 0
  name          = "${local.name}-metrics"
  protocol_type = "HTTP"
}
resource "aws_apigatewayv2_integration" "metrics" {
  count                  = var.enable_endpoint ? 1 : 0
  api_id                 = aws_apigatewayv2_api.metrics[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.metrics[0].invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 6000
}
resource "aws_apigatewayv2_route" "metrics" {
  count              = var.enable_endpoint ? 1 : 0
  api_id             = aws_apigatewayv2_api.metrics[0].id
  route_key          = "GET /metrics/units"
  authorization_type = "AWS_IAM"
  target             = "integrations/${aws_apigatewayv2_integration.metrics[0].id}"
}
resource "aws_apigatewayv2_stage" "metrics" {
  count       = var.enable_endpoint ? 1 : 0
  api_id      = aws_apigatewayv2_api.metrics[0].id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 2
    throttling_rate_limit  = 1
  }
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.lab["/retailpulse/${var.environment}/api"].arn
    format = jsonencode({
      requestId = "$context.requestId", status = "$context.status",
      routeKey  = "$context.routeKey", integrationStatus = "$context.integrationStatus"
    })
  }
}
resource "aws_lambda_permission" "api" {
  count          = var.enable_endpoint ? 1 : 0
  statement_id   = "ExactIamMetricRoute"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.metrics[0].function_name
  principal      = "apigateway.amazonaws.com"
  source_account = var.account_id
  source_arn     = "${aws_apigatewayv2_api.metrics[0].execution_arn}/$default/GET/metrics/units"
}
