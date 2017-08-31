#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='ec2_openvpn_server',
    version='0.0.1',
    description='OpenVPN Server for your VPC',
    packages=find_packages(),
    license='MIT',
    author='Marcos Araujo Sobrinho',
    author_email='marcos.sobrinho@truckpad.com.br',
    url='https://github.com/truckpad/openvpn-server/',
    download_url='https://github.com/truckpad/openvpn-server/',
    keywords=['aws', 'vpn', 'openvpn', 'vpc', 'pritunl'],
    # long_description=open('README.md').read(),
    scripts=['ec2-openvpn-server/provisioner.py'],
    install_requires=open('requirements.txt').read().strip('\n').split('\n')
)