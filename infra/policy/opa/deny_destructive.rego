package terraform.deny

deny[msg] {
  rc := input.resource_changes[_]
  actions := rc.change.actions
  destructive(actions)
  not explicitly_allowed(rc)
  msg := sprintf("Destructive change blocked: %s (%s) actions=%v", [rc.address, rc.type, actions])
}

destructive(actions) {
  actions[_] == "delete"
}

destructive(actions) {
  actions[_] == "delete"
  actions[_] == "create"
}

explicitly_allowed(rc) {
  startswith(rc.address, "module.sandbox.")
}

explicitly_allowed(rc) {
  contains(rc.address, "preview")
}
