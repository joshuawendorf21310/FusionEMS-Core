###############################################################################
# FusionEMS – Remote state backend (staging)
###############################################################################

terraform {
  backend "s3" {
    bucket         = "fusionems-terraform-state-staging"
    key            = "fusionems/staging/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "fusionems-terraform-locks"
    encrypt        = true
  }
}
