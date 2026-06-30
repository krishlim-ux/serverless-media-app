from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,                     # Added to print the URL to the logs
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations
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

        # 3. Provision the two separate Serverless Backend Lambda Functions
        self.list_lambda = _lambda.Function(
            self, "ListMediaFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="list_media.handler",
            code=_lambda.Code.from_asset("lambda")
        )

        self.upload_lambda = _lambda.Function(
            self, "GetUploadUrlFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="get_upload_url.handler",
            code=_lambda.Code.from_asset("lambda")
        )

        # 4. Create a high-performance, cost-effective HTTP API Gateway (No CORS configured here)
        self.http_api = apigwv2.HttpApi(
            self, "MediaAppHttpApi",
            api_name="MediaAppHttpApi"
        )

        # 5. Route specific paths to their respective dedicated Lambda functions
        self.http_api.add_routes(
            path="/api/media",
            methods=[apigwv2.HttpMethod.GET],
            integration=integrations.HttpLambdaIntegration("ListIntegration", self.list_lambda)
        )

        self.http_api.add_routes(
            path="/api/upload",
            methods=[apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("UploadIntegration", self.upload_lambda)
        )

        # 6. Explicitly output the HTTP API URL to our deployment logs
        CfnOutput(
            self, "MediaAppHttpApiUrl",
            value=self.http_api.url,
            description="The root URL of our high-performance HTTP API Gateway"
        )