from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
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

        # 3. Provision the two separate Serverless Backend Lambda Functions (With Bucket Environment Variables)
        self.list_lambda = _lambda.Function(
            self, "ListMediaFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="list_media.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "JPG_BUCKET_NAME": self.jpg_bucket.bucket_name,
                "PDF_BUCKET_NAME": self.pdf_bucket.bucket_name
            }
        )

        self.upload_lambda = _lambda.Function(
            self, "GetUploadUrlFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="get_upload_url.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "JPG_BUCKET_NAME": self.jpg_bucket.bucket_name,
                "PDF_BUCKET_NAME": self.pdf_bucket.bucket_name
            }
        )

        # 4. Create a high-performance, cost-effective HTTP API Gateway
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

        # 6. Secure IAM Permissions (Principle of Least Privilege)
        self.jpg_bucket.grant_read(self.list_lambda)
        self.pdf_bucket.grant_read(self.list_lambda)
        self.jpg_bucket.grant_put(self.upload_lambda)
        self.pdf_bucket.grant_put(self.upload_lambda)

        # 7. Bridge the gap: Route all /api/* requests from CloudFront directly to the HTTP API Gateway origin
        self.distribution.add_behavior(
            path_pattern="/api/*",
            origin=origins.HttpOrigin(f"{self.http_api.api_id}.execute-api.{self.region}.amazonaws.com"),
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED  # No CDN caching for dynamic backend endpoints
        )

        # 8. Explicitly output both endpoints to our deployment logs
        CfnOutput(
            self, "MediaAppHttpApiUrl",
            value=self.http_api.url,
            description="The root URL of our high-performance HTTP API Gateway"
        )

        CfnOutput(
            self, "CloudFrontDomainName",
            value=self.distribution.distribution_domain_name,
            description="The default cloudfront.net URL for testing the unified app"
        )