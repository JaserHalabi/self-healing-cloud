#!/usr/bin/env python3
"""
Terminate a compromised EC2 instance after replacement is confirmed.

Usage: python3 terminate.py <instance-id>
"""

import boto3
import json
import sys
from datetime import datetime
import os

# Initialize AWS EC2 client
ec2 = boto3.client('ec2', region_name='us-east-1')

def log_action(action, details):
    """Write action to audit log"""
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'remediation.log')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'details': details
    }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

def terminate_instance(instance_id, force=False):
    """
    Terminate an EC2 instance.
    
    Args:
        instance_id: EC2 instance ID to terminate
        force: If True, skip confirmation prompt
    """
    try:
        print(f"\n[*] Preparing to terminate {instance_id}...")
        
        # Get instance details
        response = ec2.describe_instances(InstanceIds=[instance_id])
        
        if not response['Reservations']:
            raise ValueError(f"Instance {instance_id} not found")
        
        instance = response['Reservations'][0]['Instances'][0]
        
        # Get instance name
        name = 'Unknown'
        for tag in instance.get('Tags', []):
            if tag['Key'] == 'Name':
                name = tag['Value']
        
        print(f"[*] Instance Name: {name}")
        print(f"[*] State: {instance['State']['Name']}")
        print(f"[*] Private IP: {instance.get('PrivateIpAddress', 'N/A')}")
        
        # Confirmation (unless forced)
        if not force:
            print(f"\n⚠️  WARNING: This will permanently delete the instance!")
            response = input("Type 'yes' to confirm termination: ")
            if response.lower() != 'yes':
                print("[-] Termination cancelled")
                log_action('TERMINATION_CANCELLED', {'instance_id': instance_id})
                return False
        
        # Terminate the instance
        print(f"\n[*] Terminating instance...")
        ec2.terminate_instances(InstanceIds=[instance_id])
        
        print(f"\n[+] ✅ TERMINATION INITIATED")
        print(f"[+] Instance {instance_id} is being terminated")
        print(f"[+] It will be fully deleted in 1-2 minutes")
        
        # Log the action
        log_action('TERMINATED', {
            'instance_id': instance_id,
            'instance_name': name,
            'forced': force
        })
        
        print(f"[+] Action logged to logs/remediation.log\n")
        
        return True
        
    except Exception as e:
        print(f"\n[-] ERROR: {str(e)}", file=sys.stderr)
        log_action('ERROR', {
            'action': 'terminate_instance',
            'instance_id': instance_id,
            'error': str(e)
        })
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 terminate.py <instance-id> [--force]")
        print("Example: python3 terminate.py i-0123456789abcdef0")
        print("         python3 terminate.py i-0123456789abcdef0 --force")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    force = '--force' in sys.argv
    
    # Validate instance ID format
    if not instance_id.startswith('i-'):
        print("ERROR: Invalid instance ID (must start with 'i-')")
        sys.exit(1)
    
    terminate_instance(instance_id, force=force)