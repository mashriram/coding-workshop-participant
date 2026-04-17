resource "aws_iam_role" "lambda_exec" {
  name = "coding-workshop-lambda-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Attaching the unified execution permission including CloudWatch logs and VPC bridging capabilities
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_function" "api" {
  function_name    = "coding-workshop-api"
  filename         = "${path.module}/backend.zip"
  source_code_hash = filebase64sha256("${path.module}/backend.zip")
  handler          = "lambda_handler.handler"
  runtime          = "python3.12"
  memory_size      = 256
  timeout          = 30

  role = aws_iam_role.lambda_exec.arn

  # Direct routing into the internal subnet layout
  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      POSTGRES_HOST = aws_db_instance.postgres.address
      POSTGRES_PORT = "5432"
      POSTGRES_NAME = aws_db_instance.postgres.db_name
      POSTGRES_USER = aws_db_instance.postgres.username
      POSTGRES_PASS = aws_db_instance.postgres.password
      JWT_SECRET    = "acme-super-secret-jwt-key-2024"
      ENVIRONMENT   = "production"
      IS_LOCAL      = "false"
    }
  }
}

resource "aws_apigatewayv2_api" "api" {
  name          = "coding-workshop-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["*"]
    allow_headers     = ["*"]
    expose_headers    = ["*"]
    max_age           = 86400
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"

  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.api.invoke_arn
  passthrough_behavior   = "WHEN_NO_MATCH"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
