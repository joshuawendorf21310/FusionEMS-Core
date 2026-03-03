###############################################################################
# FusionEMS – Remote state backend (dev)
###############################################################################

terraform {
  backend "s3" {
    bucket         = "fusionems-terraform-state-dev"
    key            = "fusionems/dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "fusionems-terraform-locks"
    encrypt        = true
  }
}
