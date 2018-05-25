from __future__ import print_function
from slackclient import SlackClient
import boto3
import json
import os

# Global Variables
channel = '#%s' % os.environ['SLACK_CHANNEL']
token_bot = '%s' % os.environ['SLACK_TOKEN_NAME']

def getSlackToken (user):
    ssm = boto3.client('ssm')

    token = ssm.get_parameter(
        Name='%s' % user,
        WithDecryption=True
    )

    token = token['Parameter']['Value']

    return token

def getSevColor (sev):
    if sev >= 8:
        color = '#ff0000'
    elif sev < 8 and sev >= 4:
        color = '#ffa500'
    else:
        color = '0000ff'

    return color

def getRemColor (rem):
    if rem == False:
        color = '#ff0000'
    else:
        color = '#83F52C'

    return color

def PostMessage(channel, token_bot, message, thread_ts):

    # Get Bot Token
    gd_token = getSlackToken(token_bot)

    # Slack Client for Web API Requests
    slack_client = SlackClient(gd_token)

    if thread_ts == 'NA':
        # Post Slack Message
        post = slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            as_user='true',
            attachments=message
        )
    else:
        # Post Slack Message
        post = slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            as_user='true',
            thread_ts=thread_ts,
            attachments=message
        )

    return post

def PublishEvent(event, context):

    # Log Event
    print("log -- Event: %s " % json.dumps(event))
    
    # Set Event Variables
    gd_sev = event['detail']['severity']
    gd_account = event['detail']['accountId']
    gd_region = event['detail']['region']
    gd_desc = event['detail']['description']
    gd_type = event['detail']['type']
    thread_ts = 'NA'

    # Set Severity Color
    gd_color = getSevColor(gd_sev)


    # Set Generic GD Finding Message
    message = [
    {
        "title": gd_type,
        "fields": [
            {
                "title": "AccountID",
                "value": gd_account,
                "short": 'true'
            },
            {
                "title": "Region",
                "value": gd_region,
                "short": 'true'
            }
        ],
        "fallback": "Required plain-text summary of the attachment.",
        "color": gd_color,
        "text": gd_desc,
    }]

    # Post Slack Message
    post = PostMessage(channel, token_bot, message, thread_ts)

    # Add Slack Thread Id to Event
    event["ts"] = post['message']['ts']

    return event

def PublishRemediation(event, context):

    # Log Event
    print("log -- Event: %s " % json.dumps(event))
    
    # Set Event Variables
    gd_rem = event['remediation']['success']
    gd_rem_desc = event['remediation']['description']
    gd_rem_title = event['remediation']['title']

    # Set Severity Color
    gd_color = getRemColor(gd_rem)

    # Set Generic GD Finding Message
    message = [
    {
        "title": gd_rem_title,
        "color": gd_color,
        "text": gd_rem_desc
    }]

    # Post Slack Message
    post = PostMessage(channel, token_bot, message, event["ts"])

    return event
 