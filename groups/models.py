from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class groups(models.Model):
    # One group can have many users. One user can be in multiple groups.
    # This is a many-to-many relationship.
    users = models.ManyToManyField(User, related_name='group_users')
    name = models.CharField(max_length=255)
    group_image = models.ImageField(upload_to='group_images/', null=True, blank=True)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.name} - {self.users.count()} members'

class GroupExpense(models.Model):
    group = models.ForeignKey(groups, on_delete=models.CASCADE, related_name='expenses')
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_expenses_paid', null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD', choices=[
        ('USD', 'USD ($)'),
        ('INR', 'INR (₹)'),
        ('EUR', 'EUR (€)'),
        ('GBP', 'GBP (£)')
    ])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.description} - {self.amount} {self.currency}"

class ExpensePayment(models.Model):
    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} paid {self.amount} for {self.expense.description}"

class ExpenseSplit(models.Model):
    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_splits')
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} owes {self.amount_owed} for {self.expense.description}"
