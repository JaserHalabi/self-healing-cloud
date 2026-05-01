# Self-Healing Cloud Infrastructure - Phase 1

Automated security remediation system that detects compromised servers and replaces them automatically.

## What This Does

- Deploys a website to AWS
- Monitors for threats 24/7
- Automatically isolates compromised servers
- Launches clean replacements
- Logs everything for forensics

## Quick Start

### 1. Prerequisites

- AWS account
- AWS CLI configured
- Terraform installed
- Python 3.9+

### 2. Configure Your Email

Edit `terraform/variables.tf` and change:
```hcl
default = "your-email@gmail.com"  # YOUR EMAIL HERE
```

### 3. Deploy

```bash
cd terraform
terraform init
terraform apply
```

### 4. Visit Your Website

```bash
terraform output website_url
# Copy the URL and open in browser
```

### 5. Test Full Remediation

```bash
cd ~/self-healing-cloud
bash scripts/test-full-remediation.sh
```

## Project Structure