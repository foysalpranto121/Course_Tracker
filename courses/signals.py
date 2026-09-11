import logging
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import Course, Task, UserProfile

logger = logging.getLogger(__name__)


# 1. POST_SAVE Signal for User Profile Creation
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Automatically creates or retrieves UserProfile when a User is created/updated.
    """
    if created:
        UserProfile.objects.create(user=instance)
        logger.info(f"Signal (post_save): UserProfile auto-created for user '{instance.username}'")
    else:
        UserProfile.objects.get_or_create(user=instance)


# 2. PRE_SAVE Signal for Course Status Auto-Sync
@receiver(pre_save, sender=Course)
def auto_sync_course_status(sender, instance, **kwargs):
    """
    Automatically synchronizes Course.status based on Course.progress:
    - progress >= 100 -> status = 'completed'
    - 0 < progress < 100 -> status = 'in_progress' (unless explicitly set)
    """
    if instance.progress >= 100:
        instance.status = "completed"
        logger.info(f"Signal (pre_save): Course '{instance.title}' progress is 100%, status set to 'completed'")
    elif instance.progress > 0 and instance.status != "completed":
        instance.status = "in_progress"
        logger.info(f"Signal (pre_save): Course '{instance.title}' progress > 0, status set to 'in_progress'")


# 3. POST_SAVE & POST_DELETE Signals for Task -> Course Progress Auto-Calculation
@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def update_course_progress_on_task_change(sender, instance, **kwargs):
    """
    Automatically recalculates parent Course.progress percentage when tasks are added, updated, or deleted.
    """
    course = instance.course
    if not course:
        return

    total_tasks = course.tasks.count()
    if total_tasks > 0:
        completed_tasks = course.tasks.filter(completed=True).count()
        new_progress = int(round((completed_tasks / total_tasks) * 100))
        if course.progress != new_progress:
            course.progress = new_progress
            if new_progress >= 100:
                course.status = "completed"
            elif new_progress > 0:
                course.status = "in_progress"
            else:
                course.status = "not_started"
            course.save()
            logger.info(f"Signal (task change): Course '{course.title}' progress updated to {new_progress}%")



# 4. PRE_DELETE Signal for Course Deletion Audit Logging
@receiver(pre_delete, sender=Course)
def log_course_pre_deletion(sender, instance, **kwargs):
    """
    Logs audit details before a Course is deleted.
    """
    task_count = instance.tasks.count()
    logger.info(f"Signal (pre_delete): Course '{instance.title}' (ID: {instance.pk}) with {task_count} task(s) is being deleted.")
