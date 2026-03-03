# SHADOW LITTER: PRODUCTION PLAYBOOK 🛰️🏙️⚖️
"Zero budget. Global scale. Bulletproof infrastructure."

---

## 🏛️ The Cloud Architecture
The system is designed to run on **AWS** with extreme cost-efficiency and performance:

1.  **Orchestration**: AWS EKS (Kubernetes) running **g4dn.xlarge** nodes (for GPU inference) and **t3.medium** (for agent scheduling).
2.  **Telemetry**: All orbital data flows from ESA to an **S3 Data Lake** with automated Glacier archiving policies (saves 90% in storage costs).
3.  **Persistence**: **RDS PostgreSQL** for the immutable chain of detections and stakeholder resolution tracking.
4.  **Scaling**: Horizontal Pod Autoscaler (HPA) triggers based on the queue depth of satellite scenes waiting for processing.

---

## 🚀 Deployment Checklist

### 1. Provision Infrastructure
```bash
cd infra/terraform/aws
terraform init
terraform plan
terraform apply
```

### 2. Configure Secrets
Ensure the following GitHub Secrets are set:
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- `COPERNICUS_USER` / `COPERNICUS_PASS`
- `GEE_PROJECT_ID`
- `ECR_REGISTRY`

### 3. CI/CD Rollout
Pushing to the `main` branch triggers the [`.github/workflows/production_deployment.yml`](./.github/workflows/production_deployment.yml), which:
1.  Applies Infrastructure-as-Code.
2.  Builds the production-hardened Docker image.
3.  Rolls out a **Canary Deployment** to the EKS cluster.

### 4. Monitor & Governance
Once deployed, access the dashboard via the EKS LoadBalancer URL:
```bash
kubectl get svc -n shadow-litter
```

---

## 🏗️ Scaling Madurai and Beyond
To replicate Shadow Litter in a new city (e.g., Coimbatore), simply update the `infra/terraform/aws/variables.tf` and run the CI/CD pipeline. The **Auto-Training Foundation** will automatically begin adapting the Prithvi-2.0 weights to the new city's specific land-cover patterns.

---
*Autonomous orbital intelligence for the common good. Built for Madurai.*
