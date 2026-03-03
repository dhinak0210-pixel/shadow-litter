# infrastructure/terraform/main.tf
# Production cloud infrastructure for Shadow Litter

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# GKE Cluster with GPU nodes
resource "google_container_cluster" "shadow_litter" {
  name     = "shadow-litter-prod"
  location = "asia-south1-a"
  
  node_pool {
    name = "cpu-pool"
    machine_type = "n2-standard-8"
    initial_node_count = 3
  }
  
  node_pool {
    name = "gpu-pool"
    machine_type = "n1-standard-8"
    guest_accelerator {
      type  = "nvidia-tesla-t4"
      count = 1
    }
    initial_node_count = 2
  }
}

# Cloud Storage for satellite data
resource "google_storage_bucket" "satellite_archive" {
  name     = "shadow-litter-satellite-archive"
  location = "ASIA-SOUTH1"
  
  lifecycle_rule {
    condition { age = 90 }
    action { type = "SetStorageClass", storage_class = "COLDLINE" }
  }
}

# Cloud SQL PostgreSQL
resource "google_sql_database_instance" "main" {
  name             = "shadow-litter-db"
  database_version = "POSTGRES_15"
  region           = "asia-south1"
  
  settings {
    tier = "db-custom-4-16384"
    availability_type = "REGIONAL"
    
    backup_configuration {
      enabled = true
      point_in_time_recovery_enabled = true
    }
  }
}
