import boto3
import datetime
import json

# AWS Clients
iam = boto3.client('iam')
sns = boto3.client('sns')
lambda_client = boto3.client('lambda')

# Constants
THRESHOLD_DAYS = 90
SNS_TOPIC_ARN =   
ROTATE_LAMBDA_NAME = 

def lambda_handler(event, context):
    try:
        users = iam.list_users()['Users']
        old_keys = []

        for user in users:
            username = user['UserName']
            keys = iam.list_access_keys(UserName=username)['AccessKeyMetadata']

            for key in keys:
                created_date = key['CreateDate'].replace(tzinfo=None)
                age_days = (datetime.datetime.utcnow() - created_date).days

                if age_days >= THRESHOLD_DAYS:
                    old_keys.append({
                        "User": username,
                        "AccessKeyId": key["AccessKeyId"],
                        "Age": age_days
                    })

        if old_keys:
            # Send SNS Notification with old keys
            message = "🚨 **AWS IAM Access Key Rotation Alert!** 🚨\n\n"
            message += "\n".join([f"User: {key['User']}, Key ID: {key['AccessKeyId']}, Age: {key['Age']} days" for key in old_keys])
            
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="AWS IAM Access Key Expiry Notification",
                Message=message
            )

            # Trigger Second Lambda for Key Rotation
            lambda_client.invoke(
                FunctionName=ROTATE_LAMBDA_NAME,
                InvocationType="Event",  # Async invocation
                Payload=json.dumps({"old_keys": old_keys})
            )

        else:
            # Send SNS Notification when no old keys are found
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="No Old IAM Access Keys Found",
                Message="✅ All IAM access keys are up-to-date. No keys are older than 90 days."
            )

        return {"statusCode": 200, "body": "IAM Access Key Check Completed"}

    except Exception as e:
        return {"statusCode": 500, "body": str(e)}


