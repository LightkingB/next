import logging

from celery import shared_task

from stepper.models import UserActionLog

logger = logging.getLogger('stepper')


@shared_task
def save_user_log(log_data):
    try:
        UserActionLog.objects.create(**log_data)
    except Exception as e:
        logger.error(f"Failed to save user log: {e}")
