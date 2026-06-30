import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Incoming event data: {json.dumps(event)}")
    
    # Simple router check for HTTP requests via API Gateway
    http_method = event.get("httpMethod", "GET")
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"  # Enabling CORS for frontend integration later
        },
        "body": json.dumps({
            "message": "Hello from your serverless backend logic!",
            "method_received": http_method
        })
    }