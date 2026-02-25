FEATURE_FLAGS = {
    "advanced_billing_ai": True,
    "roi_intelligence": True,
    "accreditation_engine": True
}

def is_enabled(flag: str):
    return FEATURE_FLAGS.get(flag, False)