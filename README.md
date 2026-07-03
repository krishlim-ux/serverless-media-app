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
