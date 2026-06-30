from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_lambda as _lambda,
    aws_apigateway as apigateway  # Added for API Gateway support
)
from constructs import Construct

class ServerlessMediaAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Provision the private storage buckets
        self.frontend_bucket = s3.Bucket(
            self, "StaticWebsiteBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        self.jpg_bucket = s3.Bucket(
            self, "JpgMediaBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        self.pdf_bucket = s3.Bucket(
            self, "PdfMediaBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        # 2. Deploy CloudFront pointing to the frontend bucket with Origin Access Control (OAC)
        self.distribution = cloudfront.Distribution(
            self, "MediaAppDistribution",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
            )
        )

        # 3. Provision the Serverless Backend Lambda Function
        self.media_processor_lambda = _lambda.Function(
            self, "MediaProcessorFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="process_media.handler",       # filename.function_name
            code=_lambda.Code.from_asset("lambda") # Looks inside our 'lambda' folder
        )

        # 4. Create the API Gateway and connect it directly to our Lambda function
        self.api = apigateway.LambdaRestApi(
            self, "MediaAppApi",
            handler=self.media_processor_lambda,
            proxy=True,                            # Routes all incoming web paths directly to our Lambda
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            )
        )