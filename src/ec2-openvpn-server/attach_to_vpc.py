#!/usr/bin/env python
from __future__ import print_function
import boto3
import requests
import json

VPN_NETWORK = '10.234.234.0/24'

def get_region():
    # return requests.get('http://169.254.169.254/latest/meta-data/placement/availability-zone').text[0:-1]
    return 'us-west-2'

def get_instance_id():
    # return requests.get('http://169.254.169.254/latest/meta-data/instance-id').text
    return 'i-01da3af03fe8c2b6e'

def get_instance(region, instance_id):
    ec2 = boto3.client('ec2', region_name=region)
    return ec2.describe_instances(InstanceIds=[instance_id]).get('Reservations', [None])[0].get('Instances', [None])[0]

def get_public_ip(instance):
    for network_interface in instance.get('NetworkInterfaces'):
        ip = network_interface.get('Association', {}).get('PublicIp')
        if ip:
            return ip
    return None

def get_route_tables(region, vpc_id):
    ec2 = boto3.client('ec2', region_name=region)
    return ec2.describe_route_tables(
        Filters=[{
            'Name': 'vpc-id',
            'Values': [vpc_id]
        }]
    ).get('RouteTables', {})
    

def get_vpc_id(instance):
    return instance.get('VpcId', None)


if __name__ == '__main__':
    region = get_region()
    instance_id = get_instance_id()
    instance = get_instance(region, instance_id)
    vpc_id = get_vpc_id(instance)
    public_ip = get_public_ip(instance)
    route_tables = get_route_tables(region, vpc_id)

    for route_table in route_tables:
        if route_table.get('Associations', [])[0].get('Main'):  # bad :(
            continue
        print(route_table['RouteTableId'])
        route_action = None
        for route in route_table.get('Routes'):
            if route.get('Origin') != 'CreateRoute' or 'InstanceId' not in route:
                continue
            if route.get('DestinationCidrBlock') != VPN_NETWORK:
                route_action = 'create'
            elif route.get('DestinationCidrBlock') == VPN_NETWORK and route.get('DestinationCidrBlock') != instance_id:
                route_action = 'update'
                break
            else:
                break  # do nothing

        if route_action == None:
            print('Route is fine. Nothing have to be done.')
        elif route_action == 'create':
            print('No route to VPN. Creating it!')
        elif route_action == 'update':
            print('Route is pointing to the wrong instance. Fixing it!')
        print('\n') 

        # elif 
        # print(json.dumps(route))
