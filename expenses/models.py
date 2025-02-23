from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Each category belongs to a user
    name = models.CharField(max_length=255)
    deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
class PaymentMethod(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Each payment method belongs to a user
    name = models.CharField(max_length=255)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
class Expenses(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Each transaction belongs to a user
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now_add=True)
    item = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=3)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.item} - {self.price}"