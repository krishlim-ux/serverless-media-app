import json
import os
import boto3
from botocore.config import Config

# Initialize S3 client with Signature Version 4 explicitly required for secure presigned URLs
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))

def handler(event, context):
    # 1. Parse the requested filename from the HTTP query string parameters (?filename=test.jpg)
    query_params = event.get('queryStringParameters', {}) or {}
    filename = query_params.get('filename')
    
    if not filename:
        return {
            "statusCode": 400,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({ "error": "Missing required 'filename' query parameter" })
        }
    
    # 2. Extract extension to automatically route the file to the correct bucket
    file_extension = filename.split('.')[-1].lower()
    
    if file_extension in ['jpg', 'jpeg']:
        bucket_name = os.environ.get('JPG_BUCKET_NAME')
    elif file_extension == 'pdf':
        bucket_name = os.environ.get('PDF_BUCKET_NAME')
    else:
        return {
            "statusCode": 400,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({ "error": "Unsupported file type. Only JPG, JPEG, and PDF are allowed." })
        }

    try:
        # 3. Generate a secure, temporary PUT URL valid for 5 minutes (300 seconds)
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket_name,
                'Key': filename
            },
            ExpiresIn=300
        )
        
        return {
            "statusCode": 200,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({
                "upload_url": presigned_url,
                "filename": filename,
                "target_bucket": bucket_name
            })
        }
        
    except Exception as e:
        print(f"Error generating upload link: {str(e)}")
        return {
            "statusCode": 500,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({ "error": "Failed to generate secure upload link" })
        }