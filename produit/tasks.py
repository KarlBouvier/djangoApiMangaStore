from celery import shared_task
import time
import logging

logger = logging.getLogger(__name__)


@shared_task
def test_task(message="Hello from Celery!"):
    """
    A simple test task that simulates some work and returns a result.
    """
    logger.info(f"Starting test task with message: {message}")
    
    # Simulate some work
    time.sleep(5)
    
    result = {
        'status': 'completed',
        'message': message,
        'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'task_duration': '5 seconds'
    }
    
    logger.info(f"Test task completed: {result}")
    return result


@shared_task
def send_email_task(email, subject, message):
    """
    A task to simulate sending an email asynchronously.
    """
    logger.info(f"Sending email to {email} with subject: {subject}")
    
    # Simulate email sending delay
    time.sleep(3)
    
    result = {
        'status': 'sent',
        'email': email,
        'subject': subject,
        'sent_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    logger.info(f"Email sent successfully: {result}")
    return result


@shared_task
def process_order_task(order_id):
    """
    A task to simulate order processing.
    """
    logger.info(f"Processing order {order_id}")
    
    # Simulate order processing
    time.sleep(10)
    
    result = {
        'status': 'processed',
        'order_id': order_id,
        'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'processing_time': '10 seconds'
    }
    
    logger.info(f"Order processed successfully: {result}")
    return result
