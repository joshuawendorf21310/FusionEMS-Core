package main

import rego.v1

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_security_group_rule"
  resource.change.after.type == "ingress"
  resource.change.after.cidr_blocks[_] == "0.0.0.0/0"
  resource.change.after.from_port != 443
  msg := sprintf("Security group rule %s allows 0.0.0.0/0 ingress on non-HTTPS port", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_security_group"
  ingress := resource.change.after.ingress[_]
  ingress.cidr_blocks[_] == "0.0.0.0/0"
  ingress.from_port != 443
  msg := sprintf("Security group %s allows 0.0.0.0/0 ingress on non-HTTPS port %d", [resource.address, ingress.from_port])
}
