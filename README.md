# GuardDuty Remediation Workflow with Step Functions

This serverless application...

## Architecture

![Architecture](images/aws-gd-remediation-arch.png)

### State Machine Workflow Details

![Architecture](images/workflow.png)

## Prerequisites

Below are the necessary prerequisites:

*	[AWS Account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/)
*	[AWS CLI](https://aws.amazon.com/cli/)
*	[pip](https://pypi.org/project/pip/)

### Cloud9 Environment

If you have trouble installing any of the prerequisites or dependencies, you can spin up an [AWS Cloud9](https://aws.amazon.com/cloud9/) environment, which is a cloud-based IDE that comes prepackaged with a number of essential packages.

## Install Dependencies

After cloning the repo, change to the aws-ct-processing directory and run the following to install the dependencies:

```
pip install -r requirements.txt -t ./
```

## Setup Environment

Before you deploy the SAM template for your serverless application you need to setup a number of resources manually.

### Create a Slack Bot

Go to your Slack client:

1. Click the top left corner drop down.
2. Under **Administration** click **Manage Apps**.
3. In the left navigation click **Custom Integrations** and click **Bots**.
4. Click **Add Configuration**
5. Type **guardduty** for the Username and click **Add Bot Integration**.
6. Securely copy the API Token.  You'll be adding this to paramter store later on.
7. Customize Name and Icon as you see fit and click **Save Integration**.

### AWS Resources

#### Create an S3 Bucket

In order to package and deploy SAM templates you need to have an S3 bucket where you can upload your artifacts.  If you don't already have a bucket you plan on using you can run the command below to create one.

```
aws s3api create-bucket --bucket <BUCKET NAME> --region <REGION>
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
aws cloudformation package \
    --template-file guardduty_workflow.yml \
    --s3-bucket <BUCKET NAME> \
    --output-template-file guardduty_workflow_output.yml
```

Deploy

```
aws cloudformation deploy \
    --template-file guardduty_workflow_output.yml \
    --stack-name sam-gd-remediation-workflow \
    --capabilities CAPABILITY_NAMED_IAM
```
