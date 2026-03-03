package main

import rego.v1

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  resource.change.after.publicly_accessible == true
  msg := sprintf("RDS instance %s must not be publicly accessible", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  not resource.change.after.storage_encrypted
  msg := sprintf("RDS instance %s must have encryption enabled", [resource.address])
}
