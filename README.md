# Self-Healing Cloud Infrastructure

A cybersecurity project demonstrating **fully automated** security incident response in cloud environments. When a server is compromised, the system automatically isolates it, launches a clean replacement, and notifies the security team all without human intervention.

---

## The Problem

Traditional cloud security is reactive:

```
Threat Detected (10:00)
    ↓ Engineer investigates (10:05-10:30)
    ↓ Manual remediation (10:30-11:00)
    ↓ Threat Contained (11:00)

Total Response Time: 60+ minutes
Risk: High (hacker has time to steal data)
```

---

## The Solution

Automated security response:

```
Threat Detected (10:00)
    ↓ Lambda automatically isolates (10:00.5)
    ↓ Terraform launches replacement (10:01)
    ↓ Team notified via Slack + Email (10:02)

Total Response Time: 2 minutes
Risk: Minimal (hacker barely has time)
Human Input: Zero
```

---

## What's Built

### Phase 1: Manual Remediation | Done

**Technologies:**
- Terraform (Infrastructure as Code)
- Python + Boto3 (Automation scripts)
- AWS EC2, VPC, Security Groups (Infrastructure)
- CloudWatch + GuardDuty (Monitoring)

**Capabilities:**
- Deploy infrastructure with one command
- Monitor for threats 24/7
- Manually isolate compromised servers
- Manually launch replacements via Terraform
- Full audit logging

### Phase 2: Automated Remediation | Done

**Technologies:**
- AWS Lambda (Serverless automation)
- AWS EventBridge (Event routing)
- AWS SNS (Email alerts)
- Slack Webhooks (Team notifications)
- GuardDuty (Threat detection)

**Capabilities:**
- GuardDuty detects a threat
- EventBridge automatically triggers Lambda
- Lambda runs isolation + replacement automatically
- Slack notifies the security team
- Email sent with full details
- Complete audit trail of all actions

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   AWS CLOUD                         │
│                                                     │
│  ┌────────────────────────────────────────────┐    │
│  │            VPC (10.0.0.0/16)               │    │
│  │                                            │    │
│  │  ┌──────────────────────────────────────┐ │    │
│  │  │  EC2 Web Server                      │ │    │
│  │  │  - Website hosted here               │ │    │
│  │  │  - CloudWatch monitoring             │ │    │
│  │  └──────────────────────────────────────┘ │    │
│  │                                            │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
│  ┌────────────────────────────────────────────┐    │
│  │  GuardDuty                                 │    │
│  │  - Detects threats 24/7                   │    │
│  └──────────────┬─────────────────────────────┘    │
│                 │                                   │
│  ┌──────────────▼─────────────────────────────┐    │
│  │  EventBridge                               │    │
│  │  - Routes threat findings                 │    │
│  └──────────────┬─────────────────────────────┘    │
│                 │                                   │
│  ┌──────────────▼─────────────────────────────┐    │
│  │  AWS Lambda (Python)                      │    │
│  │  - Isolates server (removes from SG)      │    │
│  │  - Launches replacement (Terraform)       │    │
│  │  - Terminates old server                  │    │
│  │  - Sends notifications                    │    │
│  └──────────────┬─────────────────────────────┘    │
│                 │                                   │
│  ┌──────────────┴──────────────────────────────┐   │
│  │          Notifications                      │   │
│  ├──────────────────────────────────────────────┤  │
│  │  Slack   →  #security-alerts                │  │
│  │  Email   →  your-email@example.com          │  │
│  │  Logs    →  CloudWatch Logs                 │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Project Structure

```
self-healing-cloud/
│
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                # VPC, networking, security groups
│   ├── compute.tf             # EC2 web server
│   ├── monitoring.tf          # CloudWatch, GuardDuty, SNS, alarms
│   ├── lambda.tf              # Lambda function for automation
│   ├── eventbridge.tf         # EventBridge rules
│   ├── variables.tf           # Configuration
│   └── outputs.tf             # Outputs
│
├── lambda/                     # Lambda automation code
│   └── remediation.py         # Main remediation logic
│
├── python/                     # Manual remediation scripts (Phase 1)
│   ├── describe.py            # List instances
│   ├── isolate.py             # Isolate server
│   └── terminate.py           # Delete server
│
├── logs/                       # Auto-generated audit logs
│   └── remediation.log        # Record of all actions
│
└── README.md                   # This file
```

---

## Setup & Deployment

### Prerequisites

- AWS Account (free tier works)
- Terraform installed
- Python 3.9+
- AWS CLI configured
- Slack workspace (for notifications)

### 1. Configure Your Email & Slack

Edit `terraform/variables.tf`:

```hcl
variable "my_email" {
  default = "your-email@gmail.com"  # CHANGE THIS
}
```

Edit `lambda/remediation.py` line 12:

```python
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"  # CHANGE THIS
```

### 2. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform apply
```

Takes about 2-3 minutes. Outputs will show your website URL.

### 3. Visit Your Website

```bash
terraform output website_url
```

Open that URL in your browser. You'll see your website with the current server ID.

### 4. Verify Notifications Work

Slack message test:
```bash
# From PowerShell - test your Slack webhook
$webhook = "YOUR-SLACK-WEBHOOK-URL"
$body = @{"text" = "Test message"} | ConvertTo-Json
Invoke-RestMethod -Uri $webhook -Method Post -Body $body -ContentType "application/json"
```

You should see a message appear in your Slack `#security-alerts` channel.

---

## How to Test Automated Remediation

### Create Test Event

Create `lambda/test-event.json`:

```json
{
  "detail": {
    "type": "UnauthorizedAccess:EC2/SSHBruteForce",
    "severity": 8,
    "resource": {
      "instanceDetails": {
        "instanceId": "YOUR-INSTANCE-ID"
      }
    }
  }
}
```

Get your instance ID:

```bash
terraform output -raw instance_id
```

### Trigger Lambda

```bash
aws lambda invoke \
  --function-name dev-auto-remediation \
  --cli-binary-format raw-in-base64-out \
  --payload file://lambda/test-event.json \
  response.json

type response.json
```

### Watch It Happen

1. **Check Slack** - Message arrives with "AUTO-HEALED SERVER" details and new website address
2. **Check Email** - Alert email arrives from SNS
3. **Check AWS Console** - Old instance terminated, new instance running
4. **Visit Website** - New server ID displayed with "AUTO-HEALED SERVER" badge

---

## What Happens During Real Attack

When GuardDuty detects a real threat:

1. **Detection** - GuardDuty identifies suspicious activity
2. **Alert** - EventBridge automatically routes to Lambda
3. **Isolation** - Lambda removes server from all security groups (hacker can't reach it)
4. **Replacement** - Lambda launches clean replacement via Terraform
5. **Termination** - Lambda deletes the compromised server
6. **Notification** - Slack message sent to your team with new server details and website URL
7. **Complete** - Your website is back online on a fresh, clean server

**Time: Under 2 minutes. Zero human input.**

---

## Monitoring & Alerts

### CloudWatch Alarms

Two alarms monitor the primary server:

- **High CPU** - Triggers if CPU >80% (could indicate cryptomining)
- **Status Check Failed** - Triggers if server stops responding

Both send SNS alerts to your email.

### GuardDuty

Monitors for:
- Unauthorized network activity
- Malware and cryptocurrency mining
- Suspicious API calls
- Command & control communications

### VPC Flow Logs

All network traffic logged to CloudWatch for forensics.

---

## Cleanup

Delete all AWS resources:

```bash
cd terraform
terraform destroy
```

Type `yes` when prompted. Everything is deleted in 2-3 minutes.

---

## Learning Outcomes

This project teaches:

- **Infrastructure as Code** - Deploy entire systems with code
- **Cloud Security** - VPCs, security groups, threat detection
- **AWS Services** - EC2, Lambda, EventBridge, CloudWatch, GuardDuty, SNS
- **Python Automation** - Boto3 for AWS API calls
- **Event-Driven Architecture** - How systems react to events automatically
- **Incident Response** - Automated threat remediation
- **DevSecOps** - Security integrated into infrastructure

---

## Architecture Decisions

### Why Terraform?

Infrastructure as Code makes remediation possible. Without it, we'd have to manually configure servers. With Terraform, new servers are identical and deploy in 30 seconds.

### Why Lambda?

Serverless automation. Lambda automatically runs Python code when EventBridge detects a threat. No infrastructure to manage, costs pennies.

### Why EventBridge?

Connects GuardDuty findings directly to Lambda. When GuardDuty detects something, EventBridge immediately triggers remediation. No human needed.

### Why Slack + Email?

Slack notifies the team immediately. Email provides an audit trail. Both ensure transparency.

---

## Cost

**Free Tier:** Fully covered for 12 months
- 750 hours EC2 t3.micro per month
- 1 million Lambda invocations per month
- GuardDuty first 30 days free

**After Free Tier:** ~$2-5/month (if left running continuously)

---

## Security Considerations

### This Project Demonstrates Best Practices

 Least privilege - EC2 roles only have needed permissions  
 Automation - Removes human error from remediation  
 Audit logging - Every action logged with timestamps  
 Immutable infrastructure - Replacement servers are fresh, not patched  
 Monitoring - GuardDuty watches 24/7  
 Rapid response - 2 minutes vs 60 minutes  

## Troubleshooting

### Website Not Loading

```bash
# Check instance is running
aws ec2 describe-instances \
  --instance-ids YOUR-INSTANCE-ID \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text
# Should return: running
```

Wait 2 minutes after deployment for Apache to start.

### Lambda Not Triggering

Check EventBridge rule:

```bash
aws events describe-rule --name dev-guardduty-findings
# State should be: ENABLED
```

Check Lambda permissions:

```bash
aws lambda get-policy --function-name dev-auto-remediation
# Should show EventBridge permission
```

### Slack Message Not Arriving

Test webhook directly:

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"test"}' \
  YOUR-SLACK-WEBHOOK-URL
```

If that works, webhook is fine. Check Lambda logs:

```bash
aws logs tail /aws/lambda/dev-auto-remediation --follow
```

---

## Deployment Status

✅ **Phase 1:** Manual remediation - Tested and working  
✅ **Phase 2:** Automated remediation - Tested and working  
✅ **All systems:** Verified in real test scenarios  

Ready for production use or as a demonstration of cloud security automation.

---

## Author

Jaser Halabi

GitHub: https://github.com/JaserHalabi/self-healing-cloud  
LinkedIn: https://linkedin.com/in/jaser-halabi

---
