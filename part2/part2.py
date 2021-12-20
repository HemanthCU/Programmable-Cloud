#!/usr/bin/env python3

import argparse
import os
import time
from pprint import pprint

import googleapiclient.discovery
import google.auth

credentials, project = google.auth.default()
service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

#
# Stub code - just lists all instances
#
def list_instances(compute, project, zone):
    result = compute.instances().list(project=project, zone=zone).execute()
    return result['items'] if 'items' in result else None

def create_snapshot(compute, project, zone, name):
    snapshotName = 'base-snapshot-{}'.format(name)
    snapshot_body = {
        'name':snapshotName
    }
    return service.disks().createSnapshot(
        project=project,
        zone=zone,
        disk=name,
        body=snapshot_body).execute()

def create_instance(compute, project, zone, name, bucket, snapshotName):
    # Configure the machine
    machine_type = "zones/%s/machineTypes/n1-standard-1" % zone
    startup_script = open(
        os.path.join(
            os.path.dirname(__file__), 'startup_script.sh'), 'r').read()

    config = {
        'name': name,
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceSnapshot': 'global/snapshots/' + snapshotName
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write'
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script',
                'value': startup_script
            }, {
                'key': 'bucket',
                'value': bucket
            }]
        }
    }

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()

def setup_firewall(compute, project):
    firewall_body = {
        'name': 'allow-5000',
        'allowed': [
            {
                'IPProtocol': 'tcp',
                'ports': [
                    '5000'
                ]
            }
        ],
        'sourceRanges': [
            '0.0.0.0/0'
        ],
        'targetTags': [
            'allow-5000'
        ]
    }
    return compute.firewalls().insert(
        project=project,
        body=firewall_body).execute()

def setup_tags(compute, project, zone, name):
    data = compute.instances().get(
        project=project,
        zone=zone,
        instance=name).execute()
    tags_body = {
        'items': [
            'allow-5000'
        ],
        'fingerprint': data['tags']['fingerprint']
    }

    return compute.instances().setTags(
        project=project,
        zone=zone,
        instance=name,
        body=tags_body).execute()

def delete_instance(compute, project, zone, name):
    return compute.instances().delete(
        project=project,
        zone=zone,
        instance=name).execute()

def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)

def main(project, bucket, zone, instance_name, wait=True):
    compute = googleapiclient.discovery.build('compute', 'v1')

    try:
        operation = setup_firewall(compute, project)
    except Exception as e:
        print('Firewall tag is already set')
    print('Creating snapshot.')
    operation = create_snapshot(compute, project, zone, instance_name)
    wait_for_operation(compute, project, zone, operation['name'])
    print('Creating instances.')
    snapshotName = 'base-snapshot-{}'.format(instance_name)
    count = 0
    while(count < 3):
        count = count + 1
        start_time = time.time()
        operation = create_instance(compute, project, zone, instance_name + '-snap' + str(count), bucket, snapshotName)
        wait_for_operation(compute, project, zone, operation['name'])
        operation = setup_tags(compute, project, zone, instance_name + '-snap' + str(count))
        print(instance_name + '-snap' + str(count) + ' is running in ' + " %s seconds" % (time.time() - start_time))
        instanceResp = compute.instances().get(
            project=project,
            zone=zone,
            instance=instance_name + '-snap' + str(count)).execute()
        if instanceResp:
            instanceIP = instanceResp['networkInterfaces'][0]['accessConfigs'][0]['natIP']
            print(instance_name + '-snap' + str(count) + " is running. Please access using the link http://" + instanceIP + ":5000")
    
    #wait_for_operation(compute, project, zone, operation['name'])

    instances = list_instances(compute, project, zone)

    print('Instances in project %s and zone %s:' % (project, zone))
    for instance in instances:
        print(' - ' + instance['name'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('project_id', help='Your Google Cloud project ID.')
    parser.add_argument(
        'bucket_name', help='Your Google Cloud Storage bucket name.')
    parser.add_argument(
        '--zone',
        default='us-west1-b',
        help='Compute Engine zone to deploy to.')
    parser.add_argument(
        '--name', default='demo-instance', help='New instance name.')

    args = parser.parse_args()

    main(args.project_id, args.bucket_name, args.zone, args.name)