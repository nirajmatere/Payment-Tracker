from django.db import models
from django.contrib.auth.models import User

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('GROUP_ADD', 'Added to Group'),
        ('EXPENSE_ADD', 'New Expense Added'),
        ('SETTLEMENT', 'Debt Settled'),
        ('SYSTEM', 'System Notification'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='SYSTEM')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_link = models.CharField(max_length=255, blank=True, null=True, help_text="Link to the related object (e.g. /groups/1)")

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

    class Meta:
        ordering = ['-created_at']
