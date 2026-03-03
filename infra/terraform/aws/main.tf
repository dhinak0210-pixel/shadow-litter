"""
infra/terraform/aws/main.tf
──────────────────────────────
Terraform configuration for Shadow Litter Production.
Provisioning the Orbital Compute Foundation on AWS.
"""

provider "aws" {
  region = var.aws_region
}

# 1. VPC for Secure Networking
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  name   = "shadow-litter-vpc"
  cidr   = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}

# 2. EKS Cluster for Scalable Inference & Agent
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "shadow-litter-orbital"
  cluster_version = "1.29"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    gpu_nodes = {
      instance_types = ["g4dn.xlarge"] # NVIDIA T4 for Prithvi-2.0 inference
      min_size     = 1
      max_size     = 10
      desired_size = 2
    }
    cpu_nodes = {
      instance_types = ["t3.medium"]
      min_size     = 2
      max_size     = 5
      desired_size = 2
    }
  }
}

# 3. S3 Bucket for Satellite Imagery (The Orbital Data Lake)
resource "aws_s3_bucket" "satellite_data" {
  bucket = "shadow-litter-satellite-data-${var.environment}"
}

resource "aws_s3_bucket_lifecycle_configuration" "imagery_lifecycle" {
  bucket = aws_s3_bucket.satellite_data.id

  rule {
    id     = "archive_old_imagery"
    status = "Enabled"
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
  }
}

# 4. RDS Instance for Traceable Detections
resource "aws_db_instance" "detections_db" {
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.t3.micro"
  db_name              = "shadowlitter"
  username             = var.db_username
  password             = var.db_password
  skip_final_snapshot  = true
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name = aws_db_subnet_group.db_subnet.name
}
