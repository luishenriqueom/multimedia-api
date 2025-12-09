AWS Deployment and Network Guide

Overview

- Deploy the FastAPI app on EC2 instances behind an Application Load Balancer (ALB).
- Store metadata in RDS (PostgreSQL).
- Store media objects in S3.
- Use Auto Scaling Group (ASG) connected to ALB for horizontal scaling.
- Create IAM roles/credentials with least-privilege for EC2 and for server-side S3/RDS access.

High-level steps

1. VPC

   - Create a VPC with at least two subnets per availability zone: public subnets for load balancer/ bastion, private subnets for EC2 and RDS.
   - Internet Gateway attached to VPC for public subnets.
   - Route table: public route table routes 0.0.0.0/0 to IGW and is associated with public subnets.
   - Private subnets use NAT Gateway in a public subnet to reach the internet (for updates, pulling images) if necessary.

2. Security Groups

   - ALB SG: allow inbound HTTP/HTTPS from 0.0.0.0/0.
   - EC2 SG: allow inbound from ALB SG on application port (e.g., 8000).
   - RDS SG: allow inbound from EC2 SG on PostgreSQL port (5432) only.

3. IAM

   - Create an IAM policy that allows S3 GetObject/PutObject/ListBucket on the application bucket, and RDS access as needed.
   - Create an IAM role for EC2 instances and attach the policy. Use Instance Profile for EC2.
   - For stronger security, use STS with temporary credentials or leverage AWS Secrets Manager for DB credentials.

4. RDS

   - Create a PostgreSQL instance in private subnets (multi-AZ recommended).
   - Configure the DB security group to allow only EC2 SG.
   - Store DB credentials in AWS Secrets Manager and inject at runtime.

5. S3

   - Create an S3 bucket with proper bucket policy. Enable versioning and lifecycle rules for cost control.
   - Configure CORS for the bucket if the frontend will access objects directly.

6. EC2 and ASG

   - Create a launch template/launch configuration with the Dockerized app or run a user-data script to pull the Docker image and run it.
   - Create an Auto Scaling Group spanning private subnets and attach it to the ALB target group.

7. Load Balancer

   - Create an Application Load Balancer in public subnets.
   - Configure listeners (80/443) and target group pointing to the ASG instances on the application port.

8. Networking and Routes
   - Public subnet route to IGW.
   - Private subnet route to NAT Gateway (if instances need outbound access).

IAM Example Policy (S3 minimal)
{
"Version":"2012-10-17",
"Statement":[
{
"Effect":"Allow",
"Action":[
"s3:PutObject",
"s3:GetObject",
"s3:DeleteObject",
"s3:ListBucket"
],
"Resource":[
"arn:aws:s3:::your-bucket-name",
"arn:aws:s3:::your-bucket-name/*"
]
}
]
}

Notes

- Use HTTPS (TLS) on ALB; terminate TLS at the ALB and forward to EC2 over HTTP inside the VPC.
- Store secrets (DB credentials, JWT secret) in AWS Secrets Manager or Parameter Store.
- Configure health checks on ALB and use graceful shutdown in the FastAPI app for instance termination.
- Use CloudWatch and alarms to scale by CPU/Requests.

Terraform or CloudFormation templates are recommended to codify this.
