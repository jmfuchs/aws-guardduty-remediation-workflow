from __future__ import print_function
from botocore.exceptions import ClientError
import boto3
import os
import json
import datetime
import uuid
import time
import detect

# Global Variables
channel = '#%s' % os.environ['SLACK_CHANNEL']
token_bot = '%s' % os.environ['SLACK_TOKEN_NAME']

def EC2MaliciousIPCaller(event, context):
       
    # Log Event
    print("log -- Event: %s " % json.dumps(event))

    # Set Event Variables
    gd_vpc_id = event["detail"]["resource"]["instanceDetails"]["networkInterfaces"][0]["vpcId"]
    gd_instance_id = event["detail"]["resource"]["instanceDetails"]["instanceId"]

    # Set Initial Remediation Metadata
    event['remediation'] = {}
    event['remediation']['success'] = False
    event['remediation']['title'] = "GuardDog was unable to remediate the Instance"
    event['remediation']['description'] = "Auto remediation was unsuccessful.  Please review the finding and remediate manaully." 
    
    # Create Forensics Security Group
    ec2 = boto3.client('ec2')
    gd_sg_name = 'GuardDuty-Remediation-Workflow-Isolation'
    try:
        try:
            # Create Isolation Security Group
            gd_sg = ec2.create_security_group(
                GroupName=gd_sg_name,
                Description='This Security Group is used to isolate potentially compromised instances.',
                VpcId=gd_vpc_id
            )
            gd_sg_id = gd_sg['GroupId']

            # Remove Default Egress Rule
            gd_sg = ec2.describe_security_groups(
                GroupIds=[
                    gd_sg_id,
                ]
            )
            ec2.revoke_security_group_egress(
                GroupId=gd_sg_id,
                IpPermissions=gd_sg['SecurityGroups'][0]['IpPermissionsEgress']
            )

            ec2.authorize_security_group_ingress(
                FromPort=22,
                CidrIp='10.0.0.0/24',
                GroupId=gd_sg_id,
                IpProtocol='tcp',
                ToPort=22,
            )
        except ClientError as e:
            print(e)
            print("log -- Isolation Security Group already exists.")

            # Get Security Group ID
            gd_sg = ec2.describe_security_groups(
                Filters=[
                    {
                    'Name': 'vpc-id',
                    'Values': [
                        gd_vpc_id,
                    ]
                    },
                    {
                    'Name': 'group-name',
                    'Values': [
                        gd_sg_name,
                    ]
                    }
                ]
            )
            gd_sg_id = gd_sg['SecurityGroups'][0]['GroupId']

        # Remove existing Security Groups and Attach the Isolation Security Group
        ec2 = boto3.resource('ec2')
        gd_instance = ec2.Instance(gd_instance_id)
        print("log -- %s, %s" % (gd_instance.id, gd_instance.instance_type))

        # Get all Security Groups attached to the Instance
        all_sg_ids = [sg['GroupId'] for sg in gd_instance.security_groups]
        
        # Isolate Instance
        gd_instance.modify_attribute(Groups=[gd_sg_id])

        # Set Remediation Metadata
        event['remediation']['success'] = True
        event['remediation']['title'] = "GuardDog Successfully Isolated Instance ID: %s" % gd_instance.id
        event['remediation']['description'] = "Please follow your necessary forensic procedures." 
    
    except ClientError as e:
        print(e)
        print("log -- Error Auto-Remediating Finding")
    
    return event

def EC2BruteForce(event, context):

    # Log Event
    print("log -- Event: %s " % json.dumps(event))

    prefix = os.environ['RESOURCE_PREFIX']
    gd_instance_id = event["detail"]["resource"]["instanceDetails"]["instanceId"]
    scan_id = str(uuid.uuid4())
    scan_name = '%s-inspector-scan' % prefix
    target_name = '%s-target-%s' % (prefix, event["id"])
    template_name = '%s-template-%s' % (prefix, event["id"])
    assess_name = '%s-assessment-%s' % (prefix, event["id"])
    # Set Initial Remediation Metadata
    event['remediation'] = {}
    event['remediation']['success'] = False
    event['remediation']['title'] = "GuardDog was unable to remediate the Instance"
    event['remediation']['description'] = "Auto remediation was unsuccessful.  Please review the finding and remediate manaully." 
    
    

    # Kick off Inspector Scan    
    try:
        gd_sev = event['detail']['severity']

        # Set Severity Color
        gd_color = detect.getSevColor(gd_sev)

        # Set Generic GD Finding Message
        message = [
        {
            "title": 'Compromised Resource Details',
            "fields": [
                {
                    "title": "Instance ID",
                    "value": gd_instance_id,
                    "short": 'true'
                },
                {
                    "title": "Public IP",
                    "value": event["detail"]["resource"]["instanceDetails"]["networkInterfaces"][0]["publicIp"],
                    "short": 'true'
                },
                {
                    "title": 'Image Description',
                    "value": event["detail"]["resource"]["instanceDetails"]["imageDescription"],
                    "short": 'false'
                },
                {
                    "title": "VPC ID",
                    "value": event["detail"]["resource"]["instanceDetails"]["networkInterfaces"][0]['vpcId'],
                    "short": 'true'
                },
                {
                    "title": "Subnet ID",
                    "value": event["detail"]["resource"]["instanceDetails"]["networkInterfaces"][0]['subnetId'],
                    "short": 'true'
                }
            ],
            "fallback": "Required plain-text summary of the attachment.",
            "color": gd_color,
            "text": 'Below are some additional details related to the GuardDuty finding.',
        }]

        # Post Slack Message
        post = detect.PostMessage(channel, token_bot, message, event["ts"])


        ec2 = boto3.client('ec2')
        inspector = boto3.client('inspector')

        scan_in_progress = False 
        tags = ec2.describe_tags(
            Filters=[
                {
                    'Name': 'resource-id',
                    'Values': [
                        gd_instance_id,
                    ],
                },
            ],
            MaxResults=100
        )

        print(tags)

        for i in tags['Tags']:
            if i['Key'] == scan_name:
                print(i['Key'])
                scan_in_progress = True

        if scan_in_progress == False:
            print("log -- Event: Running Scan")
            ec2.create_tags(
                Resources=[
                    gd_instance_id,
                ],
                Tags=[
                    {
                        'Key': scan_name,
                        'Value': scan_id
                    }
                ]
            )

            packages = inspector.list_rules_packages(
                maxResults=100
            )

            group = inspector.create_resource_group(
                resourceGroupTags=[
                    {
                        'key': scan_name,
                        'value': scan_id
                    },
                ]
            )

            target = inspector.create_assessment_target(
                assessmentTargetName=target_name,
                resourceGroupArn=group['resourceGroupArn']
            )

            template = inspector.create_assessment_template(
                assessmentTargetArn=target['assessmentTargetArn'],
                assessmentTemplateName=template_name,
                durationInSeconds=900,
                rulesPackageArns=packages['rulesPackageArns'],
                userAttributesForFindings=[
                    {
                        'key': 'instance-id',
                        'value': gd_instance_id
                    },
                    {
                        'key': 'scan-name',
                        'value': scan_name
                    },
                    {
                        'key': 'scan-id',
                        'value': scan_id
                    },
                    {
                        'key': 'gd-slack-thread',
                        'value': event["ts"]

                    }
                ]
            )

            inspector.subscribe_to_event(
                resourceArn=template['assessmentTemplateArn'],
                event='ASSESSMENT_RUN_COMPLETED',
                topicArn=os.environ['SNS_TOPIC_ARN']
            )

            assessment = inspector.start_assessment_run(
                assessmentTemplateArn=template['assessmentTemplateArn'],
                assessmentRunName=assess_name     
            )

            # Set Remediation Metadata
            event['remediation']['title'] = "GuardDog initiated an AWS Inspector assessment on this instance: %s" % gd_instance_id
        else:
            print("log -- Event: Scan Already Running")
            event['remediation']['title'] = "GuardDog has already initiated an AWS Inspector scan on this instance: %s" % gd_instance_id
        
        # Set Remediation Metadata
        event['remediation']['success'] = True
        event['remediation']['description'] = "Please view the console if you'd like to track the progress of the assessment (%s).  A new message will be posted after the assessment has been completed." % assess_name

    except ClientError as e:
        print(e)
        print("log -- Error Starting an AWS Inspector Assessment")

    return event

def EC2CleanupBruteForce(event, context):
    
    # Log Event
    print("log -- Event: %s " % json.dumps(event))

    message = json.loads(event['Records'][0]['Sns']['Message'])
    cleanup = 'Failed'

    ec2 = boto3.client('ec2')
    inspector = boto3.client('inspector')


    try:
        
        if message['event'] == 'ASSESSMENT_RUN_COMPLETED':

            run = inspector.describe_assessment_runs(
                assessmentRunArns=[
                    message['run'],
                ]
            )

            for i in run['assessmentRuns'][0]['userAttributesForFindings']:
                if i['key'] == 'instance-id':
                    instance_id = i['value']
                elif i['key'] == 'scan-name':
                    scan_name = i['value']
                elif i['key'] == 'scan-id':
                    scan_id = i['value']
                elif i['key'] == 'gd-slack-thread':
                    thread_ts = i['value']


            ec2.delete_tags(
                Resources=[
                    instance_id,
                ],
                Tags=[
                    {
                        'Key': scan_name,
                        'Value': scan_id
                    },
                ]
            )

            #inspector.delete_assessment_template(
            #    assessmentTemplateArn=message['template']
            #)
            
            #inspector.delete_assessment_target(
            #    assessmentTargetArn=message['target'],
            #)

            # Set Generic GD Finding Message
            message = [
            {
                "title": 'Inspector Assessment Complete',
                "text": 'The assessment has completed and you can view the report in the console.',
            }]

            # Post Slack Message
            post = detect.PostMessage(channel, token_bot, message, thread_ts)


        else:
            print("log -- Not a Scan Completion Event")

    except ClientError as e:
        print(e)
        print("log -- Error Cleaning up")

    return cleanup
 

def InstanceCredentialExfiltration(event, context):

    # Log Event
    print("log -- Event: %s " % json.dumps(event))

    # Set Initial Remediation Metadata
    event['remediation'] = {}
    event['remediation']['success'] = False
    event['remediation']['title'] = "GuardDog was unable to remediate the Instance"
    event['remediation']['description'] = "Auto remediation was unsuccessful.  Please review the finding and remediate manaully." 
    
    try:
              
        # Set Clients
        iam = boto3.client('iam')
        ec2 = boto3.client('ec2')

        # Set Role Variable
        role = event['detail']['resource']['accessKeyDetails']['userName']

        # Current Time
        time = datetime.datetime.utcnow().isoformat()

        # Set Revoke Policy
        policy = """
        {
          "Version": "2012-10-17",
          "Statement": {
            "Effect": "Deny",
            "Action": "*",
            "Resource": "*",
            "Condition": {"DateLessThan": {"aws:TokenIssueTime": "%s"}}
          }
        }
        """ % time

        # Add policy to Role to Revoke all Current Sessions
        iam.put_role_policy(
            RoleName=role,
            PolicyName='RevokeOldSessions',
            PolicyDocument=policy.replace('\n', '').replace(' ', '')
        )

        # Set Remediation Metadata
        event['remediation']['success'] = True
        event['remediation']['title'] = "GuardDog Successfully Removed all Active Sessions for Role: %s" % role
        event['remediation']['description'] = "Please follow your necessary forensic procedures." 

    except ClientError as e:
        print(e)
        print("log -- Error Auto-Remediating Finding")

    return event
 