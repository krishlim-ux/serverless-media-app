# Serverless Media Hub

A serverless media management application deployed on AWS via Infrastructure as Code. Users can browse and upload JPG and PDF assets through a secure web interface, with all storage, compute, and networking provisioned through AWS CDK and deployed automatically via a GitHub Actions CI/CD pipeline.

---

## System Architecture

Amazon Route 53 resolves krish.cc to the CloudFront distribution at the DNS layer. All application traffic flows directly through CloudFront, which routes requests to the appropriate origin based on path behaviour rules.

### File Listing

```text
Browser ──(GET /api/media)──> CloudFront ──> HTTP API Gateway ──> ListMedia Lambda ──> S3
Browser <──(JSON 200 OK)───── CloudFront <── HTTP API Gateway <── Lambda <────────────── S3
```
### File Upload

```text
Browser ──(POST /api/upload)──> CloudFront ──> HTTP API Gateway ──> UploadURL Lambda
Browser <──(Presigned URL)───── CloudFront <── HTTP API Gateway <── Lambda

Browser ──(PUT binary payload)──> S3 directly (CORS + signature verified)
```
