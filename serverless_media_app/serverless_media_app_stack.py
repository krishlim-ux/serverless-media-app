from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm
)
from constructs import Construct

class ServerlessMediaAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1a. Provision the private storage buckets
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

        # 1b. Reference the existing Route 53 Hosted Zone
        self.hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, "CustomHostedZone",
            hosted_zone_id="Z071914222KED4Z77OKZE",
            zone_name="krish.cc"
        )

        # 1c. Provision a secure, auto-renewing SSL certificate with automated DNS validation
        self.certificate = acm.Certificate(
            self, "AppCertificate",
            domain_name="krish.cc",
            validation=acm.CertificateValidation.from_dns(self.hosted_zone)
        )

        # 2. Deploy CloudFront pointing to S3 with OAC, Custom Domains, and SSL enabled
        self.distribution = cloudfront.Distribution(
            self, "MediaAppDistribution",
            default_root_object="index.html",
            domain_names=["krish.cc"],
            certificate=self.certificate,
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
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "JPG_BUCKET_NAME": self.jpg_bucket.bucket_name,
                "PDF_BUCKET_NAME": self.pdf_bucket.bucket_name
            }
        )

        # 4. Provision the upload engine Lambda function
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

        # 5. Create a high-performance, cost-effective HTTP API Gateway
        self.http_api = apigwv2.HttpApi(
            self, "MediaAppHttpApi",
            api_name="MediaAppHttpApi"
        )

        # 6. Route specific paths to their respective dedicated Lambda functions
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

        # 7. Secure IAM Permissions (Principle of Least Privilege)
        self.jpg_bucket.grant_read(self.list_lambda)
        self.pdf_bucket.grant_read(self.list_lambda)
        self.jpg_bucket.grant_put(self.upload_lambda)
        self.pdf_bucket.grant_put(self.upload_lambda)

        # 8. Bridge the gap: Route all /api/* requests with complete query string forwarding
        self.distribution.add_behavior(
            path_pattern="/api/*",
            origin=origins.HttpOrigin(f"{self.http_api.api_id}.execute-api.{self.region}.amazonaws.com"),
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER
        )

        # 9. Point the custom domain apex (krish.cc) directly to the CloudFront distribution
        route53.ARecord(
            self, "CloudFrontAliasRecord",
            zone=self.hosted_zone,
            target=route53.RecordTarget.from_alias(targets.CloudFrontTarget(self.distribution))
        )

        # 10. Explicitly output our production entry point
        CfnOutput(
            self, "ProductionUrl",
            value="https://krish.cc",
            description="The live, secure production URL for the unified application"
        )