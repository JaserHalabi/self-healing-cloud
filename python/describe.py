#!/usr/bin/env python3
"""
List all running EC2 instances with their details.
"""

import boto3
import json
import sys

# Initialize AWS EC2 client
ec2 = boto3.client('ec2', region_name='us-east-1')

def describe_instances():
    """Describe all running EC2 instances"""
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running', 'pending', 'stopping', 'stopped']}
            ]
        )
        
        if not response['Reservations']:
            print("No instances found.")
            return
        
        print("\n" + "="*70)
        print("RUNNING EC2 INSTANCES")
        print("="*70 + "\n")
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                # Get instance name from tags
                name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                
                print(f"Instance Name:    {name}")
                print(f"Instance ID:      {instance['InstanceId']}")
                print(f"Instance Type:    {instance['InstanceType']}")
                print(f"State:            {instance['State']['Name']}")
                print(f"Public IP:        {instance.get('PublicIpAddress', 'N/A')}")
                print(f"Private IP:       {instance.get('PrivateIpAddress', 'N/A')}")
                print(f"Security Groups:  {[sg['GroupName'] + ' (' + sg['GroupId'] + ')' for sg in instance['SecurityGroups']]}")
                print(f"Launch Time:      {instance['LaunchTime']}")
                print("-" * 70 + "\n")
        
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    describe_instances()