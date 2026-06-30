import json
import os
import boto3

# Initialize the S3 client outside the handler so it stays warm between rapid requests
s3_client = boto3.client('s3')

def handler(event, context):
    # 1. Retrieve the dynamic bucket names injected by our CDK Stack environment variables
    jpg_bucket_name = os.environ.get('JPG_BUCKET_NAME')
    pdf_bucket_name = os.environ.get('PDF_BUCKET_NAME')
    
    jpg_files = []
    pdf_files = []
    
    try:
        # 2. Scan the JPG bucket for existing items
        jpg_response = s3_client.list_objects_v2(Bucket=jpg_bucket_name)
        if 'Contents' in jpg_response:
            jpg_files = [obj['Key'] for obj in jpg_response['Contents']]
            
        # 3. Scan the PDF bucket for existing items
        pdf_response = s3_client.list_objects_v2(Bucket=pdf_bucket_name)
        if 'Contents' in pdf_response:
            pdf_files = [obj['Key'] for obj in pdf_response['Contents']]
            
        # 4. Consolidate and return the dynamic list
        return {
            "statusCode": 200,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({
                "images": jpg_files,
                "documents": pdf_files
            })
        }
        
    except Exception as e:
        print(f"Error fetching storage lists: {str(e)}")
        return {
            "statusCode": 500,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({ "error": "Failed to look up media files" })
        }