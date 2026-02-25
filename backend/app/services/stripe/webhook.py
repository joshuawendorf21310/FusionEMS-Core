def handle_event(event: dict):
    return {"processed": True, "type": event.get("type")}