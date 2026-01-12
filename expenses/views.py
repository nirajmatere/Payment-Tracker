from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from .models import Expenses, Category, PaymentMethod
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from .forms import ExpenseForm, CategoryForm, PaymentMethodForm, SpendingForm, LoginForm
from django.core.paginator import Paginator
from django.contrib import messages
from datetime import datetime
from django.utils import timezone


def investments(request):
    return render(request, 'investments.html')

def logs(request):
    return render(request, 'logs.html')

def login_view(request):
    form = LoginForm()
    return render(request, 'login.html', {'form': form})

@login_required
def expense_list(request):
    expenses = Expenses.objects.filter(user=request.user, deleted=0).order_by('-created_at')

    # Retrieve filter values
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    category_filter = request.GET.get('category', '')
    payment_method = request.GET.get('payment_method', '')

    # Apply filters
    if start_date:
        expenses = expenses.filter(created_at__gte=start_date)
    if end_date:
        expenses = expenses.filter(created_at__lte=end_date)
    if category_filter:
        expenses = expenses.filter(category__name=category_filter)
    if payment_method:
        expenses = expenses.filter(payment_method__name=payment_method)

    # Calculate total expense before pagination (so it includes all filtered results)
    total_expense = 0
    for expense in expenses:
        total_expense += expense.price

    # Pagination
    paginator = Paginator(expenses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Fetch categories & payment methods
    categories = Category.objects.filter(user=request.user, deleted=0)
    payment_methods = PaymentMethod.objects.filter(user=request.user, deleted=0)

    if request.method == 'POST':
        form2 = ExpenseForm(request.POST, user=request.user)
        if form2.is_valid():
            expense = form2.save(commit=False)
            expense.user = request.user
            expense.created_at = timezone.now()
            expense.updated_at = timezone.now()
            expense.save()
            return redirect('expenses')
    else:
        form2 = ExpenseForm(user=request.user)
    
    return render(request, 'expense_list.html', {
        'expenses': page_obj,
        'total_expense': total_expense,
        'categories': categories,
        'payment_methods': payment_methods,
        'start_date': start_date,
        'end_date': end_date,
        'category_filter': category_filter,
        'payment_method': payment_method,
        'form2': form2,
    })

@login_required
def expense_add(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        print(form_type)
        if form_type == "expense":
            form = ExpenseForm(request.POST, user=request.user)
            expense = form.save(commit=False)
            expense.user = request.user
            expense.created_at = timezone.now()
            expense.updated_at = timezone.now()
            expense.save()
            return redirect('expenses') 
        elif form_type == "category":
            form2 = CategoryForm(request.POST)
            category_name = form2['name'].value()
            print(category_name)
            if Category.objects.filter(name=category_name, user=request.user, deleted=0).exists():
                messages.error(request, "This category already exists.")
                return redirect('expense_add')
            else:
                category = form2.save(commit=False)
                category.user = request.user
                category.save()
                messages.error(request, "Category added successfully.")
                return redirect('expense_add')
        elif form_type == "payment_method":
            form3 = PaymentMethodForm(request.POST)
            payment_method_name = form3['name'].value()
            print(payment_method_name)
            if PaymentMethod.objects.filter(name=payment_method_name, user=request.user, deleted=0).exists():
                messages.error(request, "This payment method already exists.")
                return redirect('expense_add')
            else:
                payment_method = form3.save(commit=False)
                payment_method.user = request.user
                payment_method.save()
                messages.error(request, "Payment method added successfully.")
                return redirect('expense_add')
    else:
        form = ExpenseForm(user=request.user)
        form2 = CategoryForm()
        form3 = PaymentMethodForm()
    return render(request, 'expense_form.html', {'form': form, 'form2': form2, 'form3': form3})

@login_required
def expense_update(request, expense_id):
    expense = get_object_or_404(Expenses, pk=expense_id, user=request.user, deleted=0)
    expense_created_time = expense.created_at
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            edited_expense = form.save(commit=False)
            edited_expense.user = request.user
            edited_expense.created_at = expense_created_time
            edited_expense.updated_at = timezone.now()
            edited_expense.save()
            return redirect('expenses')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    return render(request, 'expense_form.html', {'form': form})

@login_required
def expense_delete(request, expense_id):
    expense = get_object_or_404(Expenses, pk=expense_id, user=request.user, deleted=0)
    if request.method == 'POST':
        expense.deleted = True
        # expense.delete()
        expense.save()
        return redirect('expenses')
    return render(request, 'expense_confirm_delete.html', {'expense': expense})

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user, deleted=0)
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == "category":
                form = CategoryForm(request.POST)
                category_name = form['name'].value()
                print(category_name)
                if Category.objects.filter(name=category_name, user=request.user, deleted=0).exists():
                    messages.error(request, "This category already exists.")
                    return redirect('category_list')
                else:
                    category = form.save(commit=False)
                    category.user = request.user
                    category.save()
                    messages.error(request, "Category added successfully.")
                    return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'category_list.html', {'categories': categories, 'form': form})

@login_required
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category_name = form.cleaned_data['name']
            user = request.user
            if Category.objects.filter(name=category_name, user=user, deleted=0).exists():
                messages.error(request, "This category already exists.")
                return redirect('category_update')
            else:
                category = form.save(commit=False)
                category.user = user
                category.save()
                return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'category_form.html', {'form': form})

@login_required
def category_update(request, category_id):
    category = get_object_or_404(Category, pk=category_id, user=request.user, deleted=0)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            edited_category = form.save(commit=False)
            if Category.objects.filter(name=edited_category.name, user=request.user, deleted=0).exists():
                messages.error(request, "This category already exists. Try different name.")
                return redirect('category_update', category_id=category_id)
            else:
                edited_category.user = request.user
                edited_category.save()
                return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'category_form.html', {'form': form})

@login_required
def category_delete(request, category_id):
    category = get_object_or_404(Category, pk=category_id, user=request.user, deleted=0)
    if request.method == 'POST':
        category.deleted = True
        category.save()
        # category.delete()
        return redirect('category_list')
    return render(request, 'category_confirm_delete.html', {'category': category})

@login_required
def payment_method_list(request):
    payment_methods = PaymentMethod.objects.filter(user=request.user, deleted=0)
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == "payment_method":
                form = PaymentMethodForm(request.POST)
                payment_method_name = form['name'].value()
                print(payment_method_name)
                if PaymentMethod.objects.filter(name=payment_method_name, user=request.user, deleted=0).exists():
                    messages.error(request, "This payment method already exists.")
                    return redirect('payment_method_list')
                else:
                    payment_method = form.save(commit=False)
                    payment_method.user = request.user
                    payment_method.save()
                    messages.error(request, "Payment method added successfully.")
                    return redirect('payment_method_list')
    else:
        form = PaymentMethodForm()
    return render(request, 'payment_method_list.html', {'payment_methods': payment_methods, 'form': form})

@login_required
def payment_method_add(request):
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method_name = form.cleaned_data['name']
            user = request.user
            if PaymentMethod.objects.filter(name=payment_method_name, user=user, deleted=0).exists():
                messages.error(request, "This payment method already exists.")
                return redirect('payment_method_add')
            else:
                payment_method = form.save(commit=False)
                payment_method.user = user
                payment_method.save()
                return redirect('payment_method_list')
    else:
        form = CategoryForm()
    return render(request, 'payment_method_form.html', {'form': form})

@login_required
def payment_method_update(request, payment_method_id):
    payment_method = get_object_or_404(PaymentMethod, pk=payment_method_id, user=request.user, deleted=0)
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=payment_method)
        if form.is_valid():
            edited_payment_method = form.save(commit=False)
            if PaymentMethod.objects.filter(name=edited_payment_method.name, user=request.user, deleted=0).exists():
                messages.error(request, "This payment method already exists. Try different name.")
                return redirect('payment_method_update', payment_method_id=payment_method_id)
            else:
                edited_payment_method.user = request.user
                edited_payment_method.save()
                return redirect('payment_method_list')
    else:
        form = PaymentMethodForm(instance=payment_method)
    return render(request, 'payment_method_form.html', {'form': form})

@login_required
def payment_method_delete(request, payment_method_id):
    payment_method = get_object_or_404(PaymentMethod, pk=payment_method_id, user=request.user, deleted=0)
    if request.method == 'POST':
        payment_method.deleted = True
        payment_method.save()
        # payment_method.delete()
        return redirect('payment_method_list')
    return render(request, 'payment_method_confirm_delete.html', {'payment_method': payment_method})

from django.db.models import Sum

@login_required
def spending(request):
    # Get the start and end date from the request parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Filter expenses by user and optional date range
    expenses = Expenses.objects.filter(user=request.user, deleted=0)

    # If start_date is provided, filter the expenses from that date
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        expenses = expenses.filter(created_at__gte=start_date_obj)
    
    # If end_date is provided, filter the expenses up to that date
    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        expenses = expenses.filter(created_at__lte=end_date_obj)

    # Calculate total expense
    total_expense = expenses.aggregate(Sum('price'))['price__sum'] or 0

    # Category-wise Aggregation
    category_data = expenses.values('category__name').annotate(total=Sum('price'))
    total_expense_category = {
        (item['category__name'] if item['category__name'] else 'Category Not Selected'): item['total'] 
        for item in category_data
    }
    
    # Payment Method-wise Aggregation
    payment_method_data = expenses.values('payment_method__name').annotate(total=Sum('price'))
    total_expense_payment_method = {
        (item['payment_method__name'] if item['payment_method__name'] else 'Payment Method Not Selected'): item['total'] 
        for item in payment_method_data
    }

    # These totals are mathematically identical to total_expense logic-wise
    total_expense_category_wise = total_expense
    total_expense_payment_method_wise = total_expense

    # Return the response with filtered expenses and date range
    return render(
        request, 
        'spending.html', 
        {
            'total_expense': total_expense,
            'total_expense_category': total_expense_category,
            'total_expense_payment_method': total_expense_payment_method,
            'total_expense_category_wise': total_expense_category_wise,
            'total_expense_payment_method_wise': total_expense_payment_method_wise,
            'start_date': start_date,
            'end_date': end_date
        }
    )
