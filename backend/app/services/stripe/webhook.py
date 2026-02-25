def handle_webhook(event: dict):
    return {"processed": True, "type": event.get("type")}