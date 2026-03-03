###############################################################################
# FusionEMS – Remote state backend (dr)
###############################################################################

terraform {
  backend "s3" {
    bucket         = "fusionems-terraform-state-dr"
    key            = "fusionems/dr/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "fusionems-terraform-locks"
    encrypt        = true
  }
}
