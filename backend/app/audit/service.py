import logging
logger = logging.getLogger("audit")

def log_action(user_id: str, action: str):
    logger.info(f"user={user_id} action={action}")