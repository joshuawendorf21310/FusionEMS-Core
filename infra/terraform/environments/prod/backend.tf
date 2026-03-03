###############################################################################
# FusionEMS – Remote state backend (prod)
###############################################################################

terraform {
  backend "s3" {
    bucket         = "fusionems-terraform-state-prod"
    key            = "fusionems/prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "fusionems-terraform-locks"
    encrypt        = true
  }
}
