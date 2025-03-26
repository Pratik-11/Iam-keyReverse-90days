import boto3
import json

# AWS Clients
iam = boto3.client('iam')
sns = boto3.client('sns')

# SNS Topic ARN
SNS_TOPIC_ARN =

def lambda_handler(event, context):
    try:
        old_keys = event.get("old_keys", [])  # Receive old keys list from event
        results = []

        sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="2 - No Old IAM Access Keys Found",
                Message="✅ All IAM access keys are up-to-date. No keys are older than 90 days."
            )

        for key_data in old_keys:
            username = key_data["User"]
            access_key_id = key_data["AccessKeyId"]

            # List access keys for user
            keys = iam.list_access_keys(UserName=username)['AccessKeyMetadata']
            if len(keys) >= 2:
                # If 2 keys exist, deactivate and notify only
                iam.update_access_key(UserName=username, AccessKeyId=access_key_id, Status='Inactive')
                results.append(f"User: {username}, Key ID {access_key_id} deactivated. No new key created (limit reached).")
            else:
                # If less than 2 keys, deactivate old key and create a new one
                iam.update_access_key(UserName=username, AccessKeyId=access_key_id, Status='Inactive')
                new_key = iam.create_access_key(UserName=username)
                results.append(f"User: {username}, Old Key {access_key_id} deactivated. New Key ID: {new_key['AccessKey']['AccessKeyId']} created.")

        # Ensure a message is always sent
        if results:
            message = "\n".join(results)
        else:
            message = "✅ No IAM access keys were rotated because no eligible keys were found."

        # Send results via SNS
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="AWS IAM Key Rotation Report",
            Message=message
        )

        return {"statusCode": 200, "body": json.dumps(results)}

    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
