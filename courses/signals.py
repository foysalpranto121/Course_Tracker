import logging
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

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


# 2. PRE_SAVE Signal for Course Status Auto-Sync & Instructor Email Notification
@receiver(pre_save, sender=Course)
def auto_sync_course_status(sender, instance, **kwargs):
    """
    Automatically synchronizes Course.status based on Course.progress:
    - progress >= 100 -> status = 'completed'
    - 0 < progress < 100 -> status = 'in_progress' (unless explicitly set)
    Sends automated completion email to instance.instructor_email if newly completed.
    """
    if instance.progress >= 100:
        instance.status = "completed"
        logger.info(f"Signal (pre_save): Course '{instance.title}' progress is 100%, status set to 'completed'")
    elif instance.progress > 0 and instance.status != "completed":
        instance.status = "in_progress"
        logger.info(f"Signal (pre_save): Course '{instance.title}' progress > 0, status set to 'in_progress'")

    # Send completion notification email to instructor if newly completed or email added
    if instance.status == "completed" and instance.instructor_email:
        already_notified = False
        if instance.pk:
            prev = Course.objects.filter(pk=instance.pk).first()
            if prev and prev.status == "completed" and prev.instructor_email == instance.instructor_email:
                already_notified = True

        if not already_notified:
            student_name = (
                instance.user.get_full_name() or instance.user.username
                if instance.user
                else "A student"
            )
            student_email = instance.user.email if (instance.user and instance.user.email) else "Not provided"
            subject = f"🎓 Course Completion Notice: {instance.title}"
            message = (
                f"Dear Instructor,\n\n"
                f"This is an official automated completion notice from the AI Course Tracker platform.\n\n"
                f"Student Details:\n"
                f"- Name: {student_name}\n"
                f"- Student Email: {student_email}\n\n"
                f"Course Summary:\n"
                f"- Title: {instance.title}\n"
                f"- Category: {instance.category or 'General'}\n"
                f"- Progress: 100% Completed\n"
                f"- Completion Date: {timezone.now().strftime('%B %d, %Y at %H:%M UTC')}\n\n"
                f"Thank you for guiding the student!\n\n"
                f"Best regards,\n"
                f"AI Course Tracker System"
            )
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[instance.instructor_email],
                    fail_silently=True,
                )
                logger.info(f"Completion email sent to instructor '{instance.instructor_email}' for course '{instance.title}'")
            except Exception as e:
                logger.error(f"Failed to send completion email to '{instance.instructor_email}': {e}")


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
