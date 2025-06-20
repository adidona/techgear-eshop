import boto3
import os
from dotenv import load_dotenv

load_dotenv()

dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv('AWS_DEFAULT_REGION'),    # From the .env file we get the AWS region and the AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY load automatically
)

def get_table(table_name):
    return dynamodb.Table(table_name)
