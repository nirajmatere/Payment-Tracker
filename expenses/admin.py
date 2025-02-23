from django.contrib import admin

from .models import Category, PaymentMethod, Expenses

# Register your models here.
admin.site.register(Category)
admin.site.register(PaymentMethod)
admin.site.register(Expenses)