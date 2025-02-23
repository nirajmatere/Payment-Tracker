from django import forms
from .models import Category, PaymentMethod, Expenses
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from datetime import date
from django.core.exceptions import ValidationError

class LoginForm(forms.Form):
    class Meta:
        model = User
        fields = ['username', 'password']
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )

class UserRegistrationForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    Confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'Confirm_password']


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expenses
        fields = ['created_at','item', 'price', 'category', 'payment_method']
        widgets = {
            'created_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'item': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user, deleted=0)
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(user=user, deleted=0)

        if 'created_at' in self.fields:
            self.fields['created_at'].label = 'Expense Date' 
    
    def clean_created_at(self):
        created_at = self.cleaned_data.get('created_at')
        if created_at and created_at.date() > date.today():  # Ensure created_at is treated as a date
            raise ValidationError("Expense date cannot be in the future.")
        return created_at
    
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SpendingForm(forms.Form):
    class Meta:
        model = Expenses
        fields = ['start_date', 'end_date', 'selected_category', 'selected_payment_method']
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'selected_category': forms.Select(attrs={'class': 'form-control'}),
            'selected_payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    start_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}) )

    selected_category = forms.ModelChoiceField(queryset=None, widget=forms.Select(attrs={'class': 'form-control'}))
    selected_payment_method = forms.ModelChoiceField(queryset=None, widget=forms.Select(attrs={'class': 'form-control'}))
