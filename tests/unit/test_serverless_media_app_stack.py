import aws_cdk as core
import aws_cdk.assertions as assertions

from serverless_media_app.serverless_media_app_stack import ServerlessMediaAppStack

# example tests. To run these tests, uncomment this file along with the example
# resource in serverless_media_app/serverless_media_app_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ServerlessMediaAppStack(app, "serverless-media-app")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
