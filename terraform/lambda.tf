# ============================================================
# ZIP THE LAMBDA CODE
# ============================================================

data "archive_file" "remediation_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/remediation.py"
  output_path = "${path.module}/remediation.zip"
}

# ============================================================
# IAM ROLE FOR LAMBDA
# ============================================================

resource "aws_iam_role" "lambda_role" {
  name = "${var.environment}-lambda-remediation-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Allow Lambda to do EC2 actions
resource "aws_iam_role_policy" "lambda_ec2_policy" {
  name = "${var.environment}-lambda-ec2-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeImages",
          "ec2:ModifyInstanceAttribute",
          "ec2:RunInstances",
          "ec2:TerminateInstances",
          "ec2:CreateTags"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================
# LAMBDA FUNCTION
# ============================================================

resource "aws_lambda_function" "remediation" {
  filename         = data.archive_file.remediation_zip.output_path
  function_name    = "${var.environment}-auto-remediation"
  role             = aws_iam_role.lambda_role.arn
  handler          = "remediation.lambda_handler"
  runtime          = "python3.9"
  timeout          = 300
  source_code_hash = data.archive_file.remediation_zip.output_base64sha256

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.alerts.arn
    }
  }

  tags = {
    Name = "${var.environment}-auto-remediation"
  }
}

# ============================================================
# EVENTBRIDGE RULE
# ============================================================

resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "${var.environment}-guardduty-findings"
  description = "Capture GuardDuty findings and trigger remediation"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
  })

  tags = {
    Name = "${var.environment}-guardduty-rule"
  }
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "RemediationLambda"
  arn       = aws_lambda_function.remediation.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.remediation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.guardduty_findings.arn
}

# ============================================================
# OUTPUTS
# ============================================================

output "lambda_function_name" {
  description = "Name of the Lambda remediation function"
  value       = aws_lambda_function.remediation.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda remediation function"
  value       = aws_lambda_function.remediation.arn
}