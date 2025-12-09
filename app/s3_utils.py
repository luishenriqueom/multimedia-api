import boto3
from .config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
from botocore.exceptions import ClientError

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def upload_fileobj(fileobj, key, content_type):
    s3 = get_s3_client()
    s3.upload_fileobj(fileobj, S3_BUCKET_NAME, key, ExtraArgs={"ContentType": content_type})

def generate_presigned_url(key, expires_in=3600):
    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': key}, ExpiresIn=expires_in)
        return url
    except ClientError:
        return None

def delete_object(key):
    s3 = get_s3_client()
    s3.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
