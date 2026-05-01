#!/usr/bin/env python3
"""
Isolate a compromised EC2 instance by removing it from all security groups.
This prevents the instance from communicating with the network.

Usage: python3 isolate.py <instance-id>
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

def isolate_instance(instance_id):
    """
    Isolate an instance by moving it to the default security group.
    
    Args:
        instance_id: EC2 instance ID to isolate
    """
    try:
        print(f"\n[*] Starting isolation process for {instance_id}...")
        
        # Get current instance details
        response = ec2.describe_instances(InstanceIds=[instance_id])
        
        if not response['Reservations']:
            raise ValueError(f"Instance {instance_id} not found")
        
        instance = response['Reservations'][0]['Instances'][0]
        vpc_id = instance['VpcId']
        current_sgs = [sg['GroupId'] for sg in instance['SecurityGroups']]
        
        print(f"[*] Current security groups: {current_sgs}")
        
        # Get the default security group for this VPC
        default_sg_response = ec2.describe_security_groups(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'group-name', 'Values': ['default']}
            ]
        )
        
        if not default_sg_response['SecurityGroups']:
            raise ValueError(f"Could not find default security group for VPC {vpc_id}")
        
        default_sg_id = default_sg_response['SecurityGroups'][0]['GroupId']
        
        print(f"[*] Moving to default security group: {default_sg_id}")
        
        # Modify instance to use only the default security group
        ec2.modify_instance_attribute(
            InstanceId=instance_id,
            Groups=[default_sg_id]
        )
        
        print(f"\n[+] ✅ ISOLATION SUCCESSFUL")
        print(f"[+] Instance {instance_id} has been isolated")
        print(f"[+] Removed from: {current_sgs}")
        print(f"[+] Moved to: {default_sg_id}")
        print(f"[+] The instance can no longer communicate on the network")
        
        # Log the action
        log_action('ISOLATED', {
            'instance_id': instance_id,
            'original_security_groups': current_sgs,
            'new_security_group': default_sg_id,
            'vpc_id': vpc_id
        })
        
        print(f"[+] Action logged to logs/remediation.log\n")
        
        return True
        
    except Exception as e:
        print(f"\n[-] ERROR: {str(e)}", file=sys.stderr)
        log_action('ERROR', {
            'action': 'isolate_instance',
            'instance_id': instance_id,
            'error': str(e)
        })
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 isolate.py <instance-id>")
        print("Example: python3 isolate.py i-0123456789abcdef0")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    
    # Validate instance ID format
    if not instance_id.startswith('i-'):
        print("ERROR: Invalid instance ID (must start with 'i-')")
        sys.exit(1)
    
    isolate_instance(instance_id)