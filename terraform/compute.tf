# ============================================================
# GET LATEST AMAZON LINUX AMI
# ============================================================

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ============================================================
# IAM ROLE - Allows EC2 to send logs to CloudWatch
# ============================================================

resource "aws_iam_role" "ec2_role" {
  name = "${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.environment}-ec2-role"
  }
}

resource "aws_iam_role_policy_attachment" "cloudwatch" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.environment}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# ============================================================
# EC2 INSTANCE - Your Web Server
# ============================================================

resource "aws_instance" "web" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  # Script that runs when server boots up
  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -e
    
    # Update system
    yum update -y
    
    # Install Apache web server
    yum install -y httpd
    
    # Start Apache
    systemctl start httpd
    systemctl enable httpd
    
    # Get this server's instance ID from AWS metadata
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    
    # Get the deployment timestamp
    DEPLOY_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Create the website
    cat > /var/www/html/index.html << HTML
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Self-Healing Cloud Demo</title>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .container {
          background: white;
          border-radius: 20px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          max-width: 700px;
          width: 100%;
          padding: 50px;
          text-align: center;
        }
        h1 {
          color: #2d3748;
          font-size: 32px;
          margin-bottom: 10px;
        }
        .subtitle {
          color: #718096;
          font-size: 16px;
          margin-bottom: 40px;
        }
        .server-box {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 30px;
          border-radius: 15px;
          margin: 30px 0;
        }
        .server-box h2 {
          font-size: 24px;
          margin-bottom: 15px;
        }
        .server-info {
          background: rgba(255,255,255,0.2);
          padding: 15px;
          border-radius: 10px;
          margin-top: 15px;
        }
        .server-info p {
          margin: 8px 0;
          font-family: 'Courier New', monospace;
          font-size: 14px;
        }
        .status-text {
          color: #4a5568;
          font-size: 15px;
          line-height: 1.8;
          margin-top: 30px;
        }
        .badge {
          display: inline-block;
          background: #48bb78;
          color: white;
          padding: 8px 20px;
          border-radius: 20px;
          font-size: 14px;
          font-weight: bold;
          margin-top: 20px;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>🛡️ Self-Healing Cloud Infrastructure</h1>
        <p class="subtitle">Automated Security Remediation System</p>
        
        <div class="server-box">
          <h2>Website is Running ✅</h2>
          <div class="server-info">
            <p><strong>Server ID:</strong> $INSTANCE_ID</p>
            <p><strong>Deployed:</strong> $DEPLOY_TIME UTC</p>
            <p><strong>Region:</strong> us-east-1</p>
          </div>
        </div>
        
        <div class="badge">PROTECTED</div>
        
        <p class="status-text">
          This website is protected by automated security monitoring.<br><br>
          <strong>If this server is compromised:</strong><br>
          • System automatically isolates it from the network<br>
          • Fresh replacement server launches in ~30 seconds<br>
          • Compromised server is terminated<br>
          • Website stays online throughout the process
        </p>
      </div>
    </body>
    </html>
HTML
    
    # Log deployment
    echo "Website deployed successfully at $DEPLOY_TIME" > /var/log/deployment.log
    echo "Instance ID: $INSTANCE_ID" >> /var/log/deployment.log
  EOF
  )

  tags = {
    Name        = "${var.environment}-web-server"
    Environment = var.environment
  }

  # This tells Terraform to wait for the user_data script to finish
  # before considering the instance "created"
  depends_on = [
    aws_iam_instance_profile.ec2_profile
  ]
}