import boto3
import json

# AWS Clients
iam = boto3.client('iam')
ssm = boto3.client('ssm')

# Parameter Store path
PARAMETER_PATH = "/IAM/AccessKeys/"

def get_iam_keys():
    """Fetch all IAM access keys that are ACTIVE."""
    iam_keys = set()
    users = iam.list_users()['Users']
    
    for user in users:
        username = user['UserName']
        keys = iam.list_access_keys(UserName=username)['AccessKeyMetadata']

        for key in keys:
            if key['Status'] == 'Active':  # Only keep active keys
                iam_keys.add(f"{PARAMETER_PATH}{username}/{key['AccessKeyId']}")

    return iam_keys

def get_parameter_store_keys():
    """Fetch all keys currently stored in AWS Parameter Store."""
    param_keys = set()
    next_token = None

    while True:
        params = ssm.get_parameters_by_path(Path=PARAMETER_PATH, Recursive=True, WithDecryption=False, NextToken=next_token) if next_token else \
                 ssm.get_parameters_by_path(Path=PARAMETER_PATH, Recursive=True, WithDecryption=False)

        for param in params.get('Parameters', []):
            param_keys.add(param['Name'])  # Store full parameter path

        next_token = params.get('NextToken')
        if not next_token:
            break

    return param_keys

def sync_iam_with_parameter_store():
    """Ensure Parameter Store reflects the exact state of IAM."""
    iam_keys = get_iam_keys()
    param_store_keys = get_parameter_store_keys()

    # 🔹 Step 1: Delete keys in Parameter Store that are no longer in IAM
    keys_to_delete = param_store_keys - iam_keys
    for key in keys_to_delete:
        ssm.delete_parameter(Name=key)
        print(f"🗑️ Deleted from Parameter Store: {key}")

    # 🔹 Step 2: Add missing IAM keys to Parameter Store
    for key in iam_keys - param_store_keys:
        parts = key.split('/')
        username = parts[-2]  # Extract username
        access_key_id = parts[-1]  # Extract Access Key ID

        param_value = json.dumps({
            "AccessKeyId": access_key_id
        })

        ssm.put_parameter(
            Name=key,
            Value=param_value,
            Type="SecureString",
            Overwrite=True
        )
        print(f"✅ Added to Parameter Store: {key}")

if __name__ == "__main__":
    sync_iam_with_parameter_store()
