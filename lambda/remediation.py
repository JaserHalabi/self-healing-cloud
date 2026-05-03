import boto3
import json
import urllib.request
import os
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

SLACK_WEBHOOK_URL = "CHANGE-TO-YOUR-SLACK-WEBHOOK-URL" # Change to your Slack webhook URL
ALERT_EMAIL       = "example@gmail.com"  # Change to your email
AWS_REGION        = "us-east-1" #Change to your AWS region

# ============================================================
# AWS CLIENTS
# ============================================================

ec2 = boto3.client('ec2', region_name=AWS_REGION)
sns = boto3.client('sns',  region_name=AWS_REGION)

# ============================================================
# HELPER: LOG
# ============================================================

def log_action(action, details):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action":    action,
        "details":   details
    }
    print(json.dumps(entry))
    return entry

# ============================================================
# STEP 1: ISOLATE
# ============================================================

def isolate_instance(instance_id):
    print(f"[*] Isolating: {instance_id}")

    response = ec2.describe_instances(InstanceIds=[instance_id])
    instance = response['Reservations'][0]['Instances'][0]
    vpc_id   = instance['VpcId']
    old_sgs  = [sg['GroupId'] for sg in instance['SecurityGroups']]

    # Get default security group
    default_sg = ec2.describe_security_groups(
        Filters=[
            {'Name': 'vpc-id',     'Values': [vpc_id]},
            {'Name': 'group-name', 'Values': ['default']}
        ]
    )['SecurityGroups'][0]['GroupId']

    # Move to default (isolated)
    ec2.modify_instance_attribute(
        InstanceId=instance_id,
        Groups=[default_sg]
    )

    print(f"[+] Isolated. Moved from {old_sgs} to {default_sg}")
    log_action('ISOLATED', {
        'instance_id':              instance_id,
        'original_security_groups': old_sgs,
        'new_security_group':       default_sg
    })

    return old_sgs

# ============================================================
# STEP 2: LAUNCH REPLACEMENT
# ============================================================

def launch_replacement(old_instance_id, original_sgs):
    print(f"[*] Launching replacement for: {old_instance_id}")

    # Get old instance details
    response     = ec2.describe_instances(InstanceIds=[old_instance_id])
    old_instance = response['Reservations'][0]['Instances'][0]

    # Get latest Amazon Linux 2 AMI
    ami_response = ec2.describe_images(
        Owners  = ['amazon'],
        Filters = [
            {'Name': 'name',                'Values': ['amzn2-ami-hvm-*-x86_64-gp2']},
            {'Name': 'virtualization-type', 'Values': ['hvm']},
            {'Name': 'state',               'Values': ['available']}
        ]
    )

    latest_ami = sorted(
        ami_response['Images'],
        key=lambda x: x['CreationDate'],
        reverse=True
    )[0]['ImageId']

    print(f"[*] Using AMI: {latest_ami}")

    # Website script
    user_data_script = """#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd

INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
DEPLOY_TIME=$(date '+%Y-%m-%d %H:%M:%S')

cat > /var/www/html/index.html << HTML
<!DOCTYPE html>
<html>
<head>
  <title>Self-Healing Cloud Demo</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .container {
      background: white;
      border-radius: 20px;
      padding: 50px;
      max-width: 700px;
      width: 100%;
      text-align: center;
    }
    h1 { color: #2d3748; margin-bottom: 10px; }
    .server-box {
      background: linear-gradient(135deg, #48bb78, #38a169);
      color: white;
      padding: 30px;
      border-radius: 15px;
      margin: 30px 0;
    }
    .replaced {
      background: linear-gradient(135deg, #ed8936, #dd6b20);
      color: white;
      padding: 10px 20px;
      border-radius: 20px;
      display: inline-block;
      margin-top: 15px;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Self-Healing Cloud Infrastructure</h1>
    <div class="server-box">
      <h2>Website is Running</h2>
      <p>Server ID: $INSTANCE_ID</p>
      <p>Deployed: $DEPLOY_TIME UTC</p>
    </div>
    <div class="replaced">AUTO-HEALED SERVER</div>
    <p style="margin-top:20px; color:#666;">
      The previous server was compromised and automatically replaced.<br>
      This is the clean replacement server.
    </p>
  </div>
</body>
</html>
HTML
"""

    # Launch new instance WITH public IP
    new_instance = ec2.run_instances(
        ImageId          = latest_ami,
        InstanceType     = old_instance['InstanceType'],
        MinCount         = 1,
        MaxCount         = 1,
        IamInstanceProfile = {
            'Name': 'dev-ec2-profile'
        },
        # KEY FIX: This gives the new server a public IP
        NetworkInterfaces = [{
            'DeviceIndex':              0,
            'SubnetId':                 old_instance['SubnetId'],
            'Groups':                   original_sgs,
            'AssociatePublicIpAddress': True
        }],
        UserData = user_data_script,
        TagSpecifications = [{
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Name',        'Value': 'dev-web-server'},
                {'Key': 'Environment', 'Value': 'dev'},
                {'Key': 'Status',      'Value': 'replacement'}
            ]
        }]
    )

    new_instance_id = new_instance['Instances'][0]['InstanceId']
    print(f"[+] New instance launched: {new_instance_id}")

    # Wait for instance to get public IP
    import time
    print("[*] Waiting 30 seconds for new instance to get public IP...")
    time.sleep(30)

    # Get the new public IP
    new_details = ec2.describe_instances(InstanceIds=[new_instance_id])
    new_public_ip = new_details['Reservations'][0]['Instances'][0].get('PublicIpAddress', 'Pending...')

    print(f"[+] New server public IP: {new_public_ip}")

    log_action('REPLACEMENT_LAUNCHED', {
        'old_instance_id': old_instance_id,
        'new_instance_id': new_instance_id,
        'new_public_ip':   new_public_ip
    })

    return new_instance_id, new_public_ip

# ============================================================
# STEP 3: TERMINATE OLD INSTANCE
# ============================================================

def terminate_instance(instance_id):
    print(f"[*] Terminating: {instance_id}")
    ec2.terminate_instances(InstanceIds=[instance_id])
    print(f"[+] Terminated: {instance_id}")
    log_action('TERMINATED', {'instance_id': instance_id})

# ============================================================
# STEP 4: SEND SLACK NOTIFICATION
# ============================================================

def send_slack(old_id, new_id, new_ip, finding_type, severity):
    print("[*] Sending Slack notification...")

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "SECURITY ALERT - Auto Remediation Complete"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Threat Detected:*\n{finding_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Action Taken:*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Compromised Server:*\n`{old_id}`\nIsolated and Terminated"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Replacement Server:*\n`{new_id}`\nRunning and Healthy"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Website is back online at:*\nhttp://{new_ip}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Status:*\nRemediation Complete"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_Self-Healing Cloud Infrastructure - Phase 2 | Automated Response_"
                    }
                ]
            }
        ]
    }

    data = json.dumps(message).encode('utf-8')
    req  = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data    = data,
        headers = {'Content-Type': 'application/json'},
        method  = 'POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            print(f"[+] Slack sent: {response.status}")
    except Exception as e:
        print(f"[-] Slack error: {e}")

# ============================================================
# STEP 5: SEND EMAIL
# ============================================================

def send_email(sns_topic_arn, old_id, new_id, new_ip, finding_type, severity):
    print("[*] Sending email...")

    try:
        sns.publish(
            TopicArn = sns_topic_arn,
            Subject  = f"SECURITY ALERT: Server Compromised and Auto-Replaced",
            Message  = (
                f"SECURITY ALERT - Auto Remediation Complete\n\n"
                f"Threat: {finding_type}\n"
                f"Severity: {severity}\n\n"
                f"What happened:\n"
                f"- Compromised server {old_id} was isolated and deleted\n"
                f"- Clean replacement {new_id} is now running\n"
                f"- Website is back at: http://{new_ip}\n\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                f"No manual action was required.\n"
                f"Self-Healing Cloud Infrastructure - Phase 2"
            )
        )
        print("[+] Email sent")
    except Exception as e:
        print(f"[-] Email error: {e}")

# ============================================================
# MAIN LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):
    print("[*] Lambda triggered")
    print(f"[*] Event: {json.dumps(event)}")

    try:
        # Get details from GuardDuty finding
        detail       = event.get('detail', {})
        finding_type = detail.get('type', 'Unknown')
        severity     = detail.get('severity', 0)
        resource     = detail.get('resource', {})

        instance_details = resource.get('instanceDetails', {})
        instance_id      = instance_details.get('instanceId', None)
        sns_topic_arn    = os.environ.get('SNS_TOPIC_ARN', '')

        print(f"[*] Finding: {finding_type}")
        print(f"[*] Severity: {severity}")
        print(f"[*] Instance: {instance_id}")

        # Only act on medium severity or higher
        if severity < 4:
            print(f"[*] Low severity ({severity}). Skipping.")
            return {
                'statusCode': 200,
                'body': 'Low severity. No action taken.'
            }

        if not instance_id:
            print("[*] No instance ID found. Skipping.")
            return {
                'statusCode': 200,
                'body': 'No instance ID in finding.'
            }

        # Run remediation steps
        original_sgs             = isolate_instance(instance_id)
        new_instance_id, new_ip  = launch_replacement(instance_id, original_sgs)
        terminate_instance(instance_id)
        send_slack(instance_id, new_instance_id, new_ip, finding_type, severity)

        if sns_topic_arn:
            send_email(sns_topic_arn, instance_id, new_instance_id, new_ip, finding_type, severity)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message':      'Remediation complete',
                'old_instance': instance_id,
                'new_instance': new_instance_id,
                'new_ip':       new_ip
            })
        }

    except Exception as e:
        print(f"[-] ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }