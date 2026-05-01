# Where alerts will be sent
resource "aws_sns_topic" "alerts" {
  name = "${var.environment}-security-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "halabijaser@gmail.com"   # IF YOU WANNA USE THIS, CHANGE THIS EMAIL TO YOUR EMAIL
}

# Alert if server CPU spikes
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_actions       = [aws_sns_topic.alerts.arn]
  dimensions          = { InstanceId = aws_instance.web.id }
}

# Alert if server stops responding
resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "${var.environment}-status-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alerts.arn]
  dimensions          = { InstanceId = aws_instance.web.id }
}

# Turn on threat detection (GuardDuty)
resource "aws_guardduty_detector" "main" {
  enable = true
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}