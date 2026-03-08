# AWS Infrastructure Direction

This project is best deployed on AWS as a split backend architecture:

- **FastAPI application service** on ECS Fargate or App Runner
- **Aurora PostgreSQL** for tenant, user, scenario, and result persistence
- **Redis / ElastiCache** for caching and job state
- **S3** for reports, exports, and uploaded source files
- **SQS** for long-running Monte Carlo and optimization jobs
- **CloudWatch / X-Ray** for tracing and observability

## Why Not Frontend-Only on AWS?

The ideal commercial topology is:
- **Vercel** for the SaaS frontend
- **AWS** for the analytics backend and stateful services

This preserves frontend speed while giving the backend the controls needed for enterprise procurement workloads.
