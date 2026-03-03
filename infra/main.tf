# infra/main.tf
# ── shadow-litter Production Infrastructure ──────────────────────────

provider "aws" {
  region = "ap-south-1" # Mumbai (closest to Madurai)
}

# 1. Image Storage (Sentinel/Landsat Raw & Processed)
resource "aws_s3_bucket" "waste_imagery" {
  bucket = "shadow-litter-imagery-madurai"
}

# 2. Database for Detections (Postgres migration from SQLite)
resource "aws_db_instance" "waste_db" {
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = "db.t3.micro" # Keep it low-budget
  db_name              = "shadow_litter"
  username             = "admin"
  password             = var.db_password
  skip_final_snapshot  = true
}

# 3. Processing Node (The Agent + Model Inference)
resource "aws_instance" "processing_node" {
  ami           = "ami-0da59f1af71ea4ad2" # Deep Learning AMI Ubuntu
  instance_type = "g4dn.xlarge"          # NVIDIA T4 for fast Siamese inference
  
  tags = {
    Name = "ShadowLitter-Processor-01"
  }
}

# 4. API Gateway & Dashboard Node
resource "aws_instance" "gateway_node" {
  ami           = "ami-02eb7a4783e7e9317" # Ubuntu 22.04
  instance_type = "t3.medium"
  
  tags = {
    Name = "ShadowLitter-Gateway-01"
  }
}

variable "db_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true
}

output "api_endpoint" {
  value = aws_instance.gateway_node.public_ip
}
