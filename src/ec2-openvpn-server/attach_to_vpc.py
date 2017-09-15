#!/usr/bin/env python
from __future__ import print_function

import boto3
import requests


class OpenVPN(object):
    route53 = boto3.client('route53')

    def __init__(self, vpn_dns_zone, vpn_network):
        self.region = self.get_region()
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.instance_id = self.get_instance_id()
        self.instance = self.get_instance(self.region, self.instance_id)
        self.vpn_dns_zone = vpn_dns_zone
        self.vpn_network = vpn_network

    @staticmethod
    def get_region():
        return requests.get('http://169.254.169.254/latest/meta-data/placement/availability-zone').text[0:-1]

    @staticmethod
    def get_instance_id():
        return requests.get('http://169.254.169.254/latest/meta-data/instance-id').text

    @staticmethod
    def get_instance(region, instance_id):
        ec2 = boto3.client('ec2', region_name=region)
        return ec2.describe_instances(InstanceIds=[instance_id]).get('Reservations', [None])[0].get('Instances', [None])[0]

    def get_public_ip(self):
        for network_interface in self.instance.get('NetworkInterfaces'):
            ip = network_interface.get('Association', {}).get('PublicIp')
            if ip:
                return ip
        return None

    def get_route_tables(self):
        return self.ec2.describe_route_tables(
            Filters=[{
                'Name': 'vpc-id',
                'Values': [self.get_vpc_id()]
            }]
        ).get('RouteTables', {})

    def get_vpc_id(self):
        return self.instance.get('VpcId', None)

    def update_dns_record(self):
        public_ip = self.get_public_ip()
        hosted_zone = self.route53.list_hosted_zones_by_name(DNSName=self.vpn_dns_zone, MaxItems='1')['HostedZones'][0]
        if hosted_zone['Name'] != '%s.' % self.vpn_dns_zone:
            raise Exception('Unknown DNS zone %s' % self.vpn_dns_zone)
        vpn_domain = 'vpn.%s.' % self.vpn_dns_zone
        record_sets = self.route53.list_resource_record_sets(
            HostedZoneId=hosted_zone['Id'],
            StartRecordName=vpn_domain,
            StartRecordType='A',
            MaxItems='1'
        )
        record_set = record_sets['ResourceRecordSets'][0]
        if record_set['Name'] == vpn_domain and len(record_set.get('ResourceRecords', [])) == 1 and record_set['ResourceRecords'][0]['Value'] == public_ip:
            print('Domain name "%s" is set up properly. :)' % vpn_domain)
        else:
            print('Domain name "%s" is not set up properly. Fixing it!' % vpn_domain)
            dns_change_response = self.route53.change_resource_record_sets(
                HostedZoneId=hosted_zone['Id'],
                ChangeBatch={
                    'Comment': 'Updating VPN endpoint to instance "%s"' % self.instance_id,
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'ResourceRecords': [{'Value': public_ip}],
                            'Type': 'A',
                            'Name': vpn_domain,
                            'TTL': 60
                        }
                    }]
                })
            print('Domain name "%s" updated to "%s". Status is %s' % (vpn_domain, public_ip, dns_change_response['ChangeInfo']['Status']))

    def update_route_table(self, route_table):
        if route_table.get('Associations', [None])[0].get('Main'):  # bad :(
            return
        route_table_id = route_table['RouteTableId']
        for route in route_table.get('Routes'):
            if route.get('DestinationCidrBlock') == self.vpn_network:
                if route.get('InstanceId') != self.instance_id:
                    print('Route table "%s" is pointing to the wrong instance. Fixing it!' % route_table_id)
                    self.ec2.replace_route(
                        DestinationCidrBlock=self.vpn_network,
                        InstanceId=self.instance_id,
                        RouteTableId=route_table_id
                    )
                    print('Route table "%s" VPN entry updated route to instance "%s".' % (route_table_id, self.instance_id))
                else:
                    print('Route table "%s" is fine. Nothing have to be done.' % route_table_id)
                return

        print('No route to VPN in route table "%s". Creating it!' % route_table_id)
        self.ec2.create_route(
            DestinationCidrBlock=self.vpn_network,
            InstanceId=self.instance_id,
            RouteTableId=route_table_id
        )
        print('Route table "%s" VPN entry added route to instance "%s".' % (route_table_id, self.instance_id))

    def update_route_tables(self):
        route_tables = self.get_route_tables()
        for route_table in route_tables:
            self.update_route_table(route_table)

    def check_aws_config(self):
        ''' Do everything, in the right sequence! :D '''
        self.update_route_tables()
        self.update_dns_record()


if __name__ == '__main__':
    print(r'''                     *** Pritunl ***
________                     ____   _____________________   
\_____  \ ______   ____   ___\   \ /   /\______   \      \  
 /   |   \\____ \_/ __ \ /    \   Y   /  |     ___/   |   \ 
/    |    \  |_> >  ___/|   |  \     /   |    |  /    |    \
\_______  /   __/ \___  >___|  /\___/    |____|  \____|__  /
        \/|__|        \/     \/                          \/ ''')

    import argparse
    parser = argparse.ArgumentParser(description='Update VPC Route table for this VPN instance')
    parser.add_argument('vpn_domain', type=str, help='Domain to create the "vpc" subdomain. Must live in Route53.')
    parser.add_argument('vpn_cidr', type=str, help='CIDR network to be used internally by VPN clients.')
    args = parser.parse_args()

    print("\n\tCIDR: %s\t\tHosted Zone: %s\n" % (args.vpn_cidr, args.vpn_domain))
    vpn = OpenVPN(args.vpn_domain, args.vpn_cidr)
    vpn.check_aws_config()
