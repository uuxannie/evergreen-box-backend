import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.services.timelapse_service import clean_old_files, generate_timelapse_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def init_scheduler():
    """
    Initialize and start the background scheduler with maintenance tasks.
    Called during application startup in main.py
    """
    global scheduler
    
    try:
        scheduler = BackgroundScheduler()
        
        # Task 1: Cleanup old files daily at 3:00 AM
        scheduler.add_job(
            func=cleanup_task,
            trigger=CronTrigger(hour=3, minute=0),
            id="cleanup_task",
            name="Daily cleanup of old images and videos",
            replace_existing=True,
            max_instances=1
        )
        
        # Task 2: Generate timelapse video daily at 4:00 AM (after cleanup)
        scheduler.add_job(
            func=timelapse_task,
            trigger=CronTrigger(hour=4, minute=0),
            id="timelapse_task",
            name="Daily timelapse video generation",
            replace_existing=True,
            max_instances=1
        )
        
        scheduler.start()
        logger.info("[SCHEDULER] Background scheduler initialized with 2 scheduled tasks")
        logger.info("[SCHEDULER] - Cleanup task: Daily at 03:00 AM")
        logger.info("[SCHEDULER] - Timelapse task: Daily at 04:00 AM")
        
    except Exception as e:
        logger.error(f"[SCHEDULER] Failed to initialize scheduler: {e}", exc_info=True)
        raise

def shutdown_scheduler():
    """
    Gracefully shutdown the scheduler.
    Called during application shutdown.
    """
    global scheduler
    
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("[SCHEDULER] Scheduler shut down successfully")
        except Exception as e:
            logger.error(f"[SCHEDULER] Error during scheduler shutdown: {e}", exc_info=True)

def cleanup_task():
    """
    Wrapper for cleanup task to be executed by scheduler.
    """
    try:
        logger.info("[SCHEDULER] Running cleanup task...")
        result = clean_old_files()
        logger.info(f"[SCHEDULER] Cleanup task completed: {result}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Cleanup task failed: {e}", exc_info=True)

def timelapse_task():
    """
    Wrapper for timelapse generation task to be executed by scheduler.
    """
    try:
        logger.info("[SCHEDULER] Running timelapse generation task...")
        result = generate_timelapse_video()
        logger.info(f"[SCHEDULER] Timelapse task completed: {result}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Timelapse task failed: {e}", exc_info=True)
