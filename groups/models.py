from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class groups(models.Model):
   
    name = models.CharField(max_length=100)
    group_image = models.ImageField(upload_to='group_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    users = models.ManyToManyField(User, related_name='user_groups')
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class GroupExpense(models.Model):
    group = models.ForeignKey(groups, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, choices=[('USD', 'USD'), ('EUR', 'EUR'), ('INR', 'INR'), ('GBP', 'GBP')], default='USD')
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.description} - {self.amount} {self.currency}"

class ExpenseSplit(models.Model):
    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} owes {self.amount_owed}"

class ExpensePayment(models.Model):
    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} paid {self.amount}"

class GroupInvitation(models.Model):
    group = models.ForeignKey(groups, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined')], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitation from {self.sender} to {self.receiver} for {self.group}"
