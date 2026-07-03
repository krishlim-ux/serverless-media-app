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
---

## Core Tech Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend Hosting** | Amazon S3 + CloudFront | Static assets are served from a private S3 bucket via CloudFront edge locations globally, eliminating server overhead and reducing latency. |
| **API Routing** | Amazon API Gateway (HTTP) | HTTP API was chosen over REST API for lower latency and reduced cost, sufficient for the two-route API surface this application requires. |
| **Compute** | AWS Lambda (Python 3.11) | Serverless, event-driven functions handle media listing and presigned URL generation with no idle cost and automatic scaling. |
| **Storage** | Amazon S3 | Separate private buckets isolate JPG and PDF assets by type, with public access blocked entirely and access enforced through OAC and presigned URLs. |
| **Infrastructure as Code** | AWS CDK (Python) | The entire stack is defined and deployed in code, ensuring reproducibility and eliminating configuration drift from manual console changes. |
| **DNS and SSL** | Route 53 + AWS Certificate Manager | Route 53 manages apex domain resolution and ACM provides an auto-renewing SSL certificate validated via DNS, attached to the CloudFront distribution. |
| **CI/CD** | GitHub Actions | A push to main triggers automatic CDK deployment and frontend asset synchronisation in a single pipeline run. |

---

## Architectural Decisions and Trade-offs

### API Gateway: HTTP API vs. REST API
HTTP API Gateway was chosen over REST API for this project. The application requires only two routes. `/api/media` and `/api/upload`. With no need for the advanced features REST API provides, such as request validation, API keys, or AWS service integrations. HTTP API delivers lower latency and reduced cost for straightforward Lambda proxy routing.

### Upload Path: Direct S3 vs. CloudFront Proxying
File uploads are sent directly from the browser to the native S3 bucket endpoint, bypassing CloudFront and API Gateway entirely. Presigned URLs are cryptographically bound to a specific host, routing the upload through CloudFront would invalidate the signature. Direct upload also eliminates intermediate data transfer costs and avoids Lambda timeout constraints on large file transfers.

### CORS Scope: Apex Domain Only
The S3 bucket CORS configuration permits requests exclusively from `https://krish.cc`. The `www` subdomain is deliberately excluded because the Route 53 zone and CloudFront distribution are configured for apex-only traffic. Restricting CORS to a single authoritative origin keeps the permitted attack surface minimal.

---

## Production Security Hardening

### CloudFront Origin Access Control (OAC)
All S3 buckets have public access blocked at both the bucket and account level. CloudFront Origin Access Control (OAC) is configured so that S3 bucket policies permit `s3:GetObject` exclusively when the request originates from the specific CloudFront distribution ARN. No direct S3 access is possible from the public internet.

### IAM Least Privilege
Lambda execution roles are scoped to the minimum permissions required for each function. The ListMedia function is granted read-only access to query object metadata from the media buckets. The UploadURL function has no read or list permissions, its execution role is granted `s3:PutObject` privileges strictly on the target storage buckets, which is the required permission embedded into the cryptographically generated presigned upload signature. Neither function has cross-bucket access.

### S3 CORS Hardening
CORS rules on the JPG and PDF media buckets restrict direct upload access to a single authorised origin. Permitted methods are limited to `PUT` only, allowed headers are restricted to `Content-Type`, and the allowed origin is locked to `https://krish.cc` exclusively. This prevents any unauthorised web application from writing directly to the storage layer.

---

## Automated CI/CD Lifecycle

Infrastructure provisioning and frontend deployment are managed entirely through a GitHub Actions pipeline. A push to the `main` branch triggers a workflow that sequentially deploys both infrastructure changes and static frontend assets in a single run.

### Pipeline Steps

* **Environment Setup:** The GitHub runner initialises a Linux environment with Python 3.11, installs project dependencies, and configures the AWS CDK CLI.
* **Infrastructure Deployment:** The pipeline authenticates with AWS using credentials stored as GitHub Secrets and runs `cdk deploy`. This synthesises the Python CDK code into CloudFormation templates and applies any infrastructure changes deterministically, with no manual console intervention required.
* **Frontend Asset Synchronisation:** The CDK `BucketDeployment` construct automatically syncs the contents of the `frontend/` directory to the static hosting S3 bucket as part of the same deployment run. Infrastructure changes and frontend updates are delivered atomically in a single pipeline execution.

---

## Technical Verification

The application has been verified across all architectural layers to confirm routing, security, and compute integration are functioning as designed.

### 1. CI/CD Pipeline
The GitHub Actions workflow completes the full CDK synthesis and frontend asset deployment with no errors or warnings on every push to `main`.

### 2. DNS and SSL
The apex domain `https://krish.cc` resolves correctly over an encrypted HTTPS connection. The ACM certificate is attached to the CloudFront distribution and enforced at the edge.

### 3. API Layer
Browser network console verification confirms expected responses across both routes:
* `GET /api/media` returns a well-formed JSON array of media objects with a `200 OK` status.
* `POST /api/upload` returns a valid presigned S3 URL with a `200 OK` status.

### 4. Direct S3 Upload
The browser executes a `PUT` request directly to the native S3 endpoint using the presigned URL. S3 validates the signature and verifies the request origin against the bucket CORS policy, completing the upload with a `200 OK`. Uploaded objects are confirmed present in the target media buckets via the S3 console.
