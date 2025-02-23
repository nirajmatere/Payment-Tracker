from django.http import HttpResponse
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from expenses.forms import UserRegistrationForm
from django.contrib.auth.models import User
from expenses.models import Expenses, Category, PaymentMethod

def home(request):
    # return HttpResponse('Hello, Django!')
    return render(request, 'layout.html')

def user_registration(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                form.cleaned_data['username'],
                form.cleaned_data['email'],
                form.cleaned_data['password']
            )
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('expenses')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})
