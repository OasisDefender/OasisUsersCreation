import json
import sys
import time
import os
import logging
from dotenv import load_dotenv

import boto3
from botocore.exceptions import ClientError


PROFILE_FILE = "oasis_aws_profile.json"
OASIS_USER_NAME = "OasisUser"
OASIS_POLICY= "OasisPolicy"
LOG_FILE = "oasis_create_user.log"
LOGGER = None

def progress_bar(seconds):
    """Shows a simple progress bar in the command window."""
    for _ in range(seconds):
        time.sleep(1)
        print('.', end='')
        sys.stdout.flush()
    print()

def setup(iam):
    global LOGGER
    """
    Creates a new user with no permissions.
    Creates an access key pair for the user.
    Creates an inline policy for the user.
    """
    try:
        LOGGER.info(f"create user {OASIS_USER_NAME}")
        user = iam.create_user(UserName=f"{OASIS_USER_NAME}")
    except ClientError as error:
        print(f"Couldn't create a user: {error.response['Error']['Message']}")
        LOGGER.error(f"Couldn't create a user: {error.response['Error']['Message']}")
        raise
    
    username = user["User"]["UserName"]
    print(f"Created user {username}.")

    try:
        LOGGER.info(f"create access key pair for user {username}")
        user_key = iam.create_access_key(UserName=username)
        print(f"Created access key pair for user {username}.")
    except ClientError as error:
        print(f"Couldn't create access keys for user {username}: {error.response['Error']['Message']}")
        LOGGER.error(f"Couldn't create access keys for user {username}: {error.response['Error']['Message']}")
        raise

    print("Wait for user to be ready.", end = '')
    progress_bar(5)

    try:
        LOGGER.info(f"open profile file {PROFILE_FILE} for {username}")
        f = open(PROFILE_FILE)
    except OSError:
        print (f"Couldn't open file {PROFILE_FILE}")
        LOGGER.error(f"Couldn't open file {PROFILE_FILE}")
        raise
    
    try:
        LOGGER.info(f"load profile")
        data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON syntax: {e}")
        LOGGER.error(f"Invalid JSON syntax: {e}")
        f.close()
        raise

    f.close()
    
    try:
        LOGGER.info(f"create inline policy for {username}")
        policy = iam.create_policy(PolicyName=OASIS_POLICY, PolicyDocument=json.dumps(data))
        # log(response)
        print(f"Created an inline policy for {username}")
    except ClientError as error:
        print(f"Couldn't create an inline policy for user {username}: "
              f"{error.response['Error']['Message']}")
        LOGGER.error(f"Couldn't create an inline policy for user {username}: "
              f"{error.response['Error']['Message']}")
        raise

    print("Give AWS time to propagate these new resources and connections.",  end = '')
    progress_bar(5)

    try:
        arn = policy["Policy"]["Arn"]
        LOGGER.info(f"attach policy {arn} to user {username}")
        response = iam.attach_user_policy(PolicyArn=arn, UserName=username)
        print(f"Policy attached to user {username}")
    except ClientError as error:
        print(f"Couldn't attach policy to user {username}: "
              f"{error.response['Error']['Message']}")
        LOGGER.error(f"Couldn't attach policy to user {username}: "
              f"{error.response['Error']['Message']}")
        raise

    return username, user_key

def teardown(user, role):
    try:
        for attached in role.attached_policies.all():
            policy_name = attached.policy_name
            role.detach_policy(PolicyArn=attached.arn)
            attached.delete()
            print(f"Detached and deleted {policy_name}.")
        role.delete()
        print(f"Deleted {role.name}.")
    except ClientError as error:
        print("Couldn't detach policy, delete policy, or delete role. Here's why: "
              f"{error.response['Error']['Message']}")
        raise

    try:
        for user_pol in user.policies.all():
            user_pol.delete()
            print("Deleted inline user policy.")
        for key in user.access_keys.all():
            key.delete()
            print("Deleted user's access key.")
        user.delete()
        print(f"Deleted {user.name}.")
    except ClientError as error:
        print("Couldn't delete user policy or delete user. Here's why: "
              f"{error.response['Error']['Message']}")


def create_user():
    global LOGGER
    #  Initialize log subsystem 
    logging.basicConfig(filename=LOG_FILE,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)
    
    LOGGER = logging.getLogger('create_oasis_user')
    LOGGER.info("User Management Script Started")
    
    try:
        LOGGER.info("Load environment data from aws.env")
        # Initialize a session using AWS credentials
        load_dotenv("aws.env")
    except Exception:
        print("Coudn't load env file!")
        LOGGER.error("Coudn't load env file!")

    try:
        LOGGER.info("Load access keys")
        access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
        secret_access_key = os.environ["AWS_SECRET_KEY"]
        reg_name = os.environ["AWS_REGION_NAME"]
    except Exception:
        print("Data load error!")
        LOGGER.error("Data load error!")

    try:
        LOGGER.info("Create boto3 session")
        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=reg_name  # choose your preferred region
            )
    except Exception:
        print("Coudn't create boto3 session!")
        LOGGER.error("Coudn't create boto3 session!")

    try:
        LOGGER.info("create IAM client")
        iam = session.client('iam')
    except Exception:
        print("Coudn't create IAM client")
        LOGGER.error("Coudn't create IAM client")

    user = None
    try:
        user, user_key = setup(iam)
        print(f"Created {user} with key pair AccessKey:{user_key['AccessKey']['AccessKeyId']} / SecretKey:{user_key['AccessKey']['SecretAccessKey']}")
    except Exception:
       print("Something went wrong!")
       LOGGER.error("fatal error")

if __name__ == '__main__':
    create_user()
