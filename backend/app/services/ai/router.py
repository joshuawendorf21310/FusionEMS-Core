def route_task(task_type: str):
    routes = {
        "clinical": "ai_clinical_extractor",
        "billing": "ai_revenue_engine",
        "support": "ai_support_assistant"
    }
    return routes.get(task_type, "unknown")