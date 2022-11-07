# GuardDuty Remediation Workflow with Step Functions

This serverless application creates an [AWS Step Functions](https://aws.amazon.com/step-functions/) state machine that uses AWS Lambda functions to publish alerts and remediate [Amazon GuardDuty](https://aws.amazon.com/guardduty/) findings. The below architecture showcases how a finding is processed through the workflow.

## Architecture

![Architecture](images/aws-gd-remediation-arch.png)

## Prerequisites

Below are the necessary prerequisites:

*	[AWS Account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/)
*	[AWS CLI](https://aws.amazon.com/cli/)
*	[pip](https://pypi.org/project/pip/)

### Cloud9 Environment

If you have trouble installing any of the prerequisites or dependencies, you can spin up an [AWS Cloud9](https://aws.amazon.com/cloud9/) environment, which is a cloud-based IDE that comes prepackaged with a number of essential packages.

## Install Dependencies

After cloning the repo, change to the aws-guardduty-remediation-workflow and run the following to install the dependencies:

```
pip install -r requirements.txt -t ./
```

## Setup Environment

Before you deploy the SAM template for your serverless application you need to setup a number of resources manually.

### Slack

#### Create Slack Bot

Go to your Slack client:

1. Click the top left corner drop down.
2. Under **Administration** click **Manage Apps**.
3. In the left navigation click **Custom Integrations** and click **Bots**.
4. Click **Add Configuration**
5. Type **guardduty** for the Username and click **Add Bot Integration**.
6. Securely copy the API Token.  You'll be adding this to parameter store later on.
7. Customize the Name and Icon as you see fit and click **Save Integration**.

#### Create Slack Channel

Create a new channel for receiving alerts. Invite your bot by typing **@guardduty** in the channel and clicking **invite them to join**.

### AWS Resources

#### Create an S3 Bucket

In order to package and deploy SAM templates you need to have an S3 bucket where you can upload your artifacts.  If you don't already have a bucket you plan on using you can run the command below to create one.

```
aws s3api create-bucket --bucket <BUCKET NAME> --region <REGION> --create-bucket-configuration LocationConstraint=<REGION>
```

### Create Parameter

For this application you need to manually create a Parameter in AWS Systems Manager Parameter Store for your Slack Bot Token.

```
aws ssm put-parameter --name "bot-token-guardduty" --type "SecureString" --value "<INSERT SLACK API TOKEN>"
```

### Create Inspector Role

If you haven't used Amazon Inspector before you'll need to create an IAM Service-Linked Role.

1. Browse to [IAM Console](https://console.aws.amazon.com/iam/home#/home) and click **Roles** in the left navigation.
2. Click **Create Role** and select **Inspector** for the service that will be using the Role.
3. Click **Next: Permissions**, **Next: Review**, and then **Create Role**.

## Package and Deploy the SAM template

Package local artifacts and upload to the S3 bucket you previously created.

```
aws cloudformation package --template-file guardduty_workflow.yml --s3-bucket <BUCKET NAME> --output-template-file guardduty_workflow_output.yml
```

Deploy the CloudFormation template.

```
aws cloudformation deploy --template-file guardduty_workflow_output.yml --stack-name sam-gd-remediation-workflow --parameter-overrides SlackChannel=<CHANNEL> SlackTokenName=bot-token-guardduty --capabilities CAPABILITY_NAMED_IAM
```

## View your GuardDuty Remediation State Machine

1. Browse to the [AWS Step Functions](https://us-west-2.console.aws.amazon.com/states/home)
2. Click **State Machines** in the left navigation and click on **guardduty-workflow**.
3. Click **Definition** to view the JSON structure and visual representation of the workflow.

Below are additional details about the Lambda functions included in the State Machine.

### State Machine Workflow Details

![Architecture](images/workflow.png)

test.
