package main

import rego.v1

deny contains msg if {
  resource := input.resource_changes[_]
  resource.change.actions[_] == "create"
  not resource.change.after.tags.Project
  msg := sprintf("Resource %s is missing required 'Project' tag", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.change.actions[_] == "create"
  not resource.change.after.tags.Environment
  msg := sprintf("Resource %s is missing required 'Environment' tag", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.change.actions[_] == "create"
  not resource.change.after.tags.ManagedBy
  msg := sprintf("Resource %s is missing required 'ManagedBy' tag", [resource.address])
}
