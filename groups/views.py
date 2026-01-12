from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from .models import groups, GroupExpense, ExpenseSplit, ExpensePayment
from .forms import GroupExpenseForm
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Sum

# Create your views here.

@login_required
def group_list(request):
    user = request.user
    groups_data = []
    user_groups = groups.objects.filter(users=user, deleted=0)
    
    for group in user_groups:
        # Calculate net balance for this user in this group PER CURRENCY
        # Identify currencies in this group
        currencies = GroupExpense.objects.filter(group=group, deleted=0).values_list('currency', flat=True).distinct()
        if not currencies:
             currencies = ['USD']
            
        balances = []
        for currency in currencies:
            paid = ExpensePayment.objects.filter(expense__group=group, expense__currency=currency, user=user, expense__deleted=0).aggregate(Sum('amount'))['amount__sum'] or 0
            owed = ExpenseSplit.objects.filter(expense__group=group, expense__currency=currency, user=user, expense__deleted=0).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
            net = float(paid - owed)
            if abs(net) > 0.01:
                balances.append({'currency': currency, 'amount': net})
        
        groups_data.append({
            'group': group,
            'balances': balances # List of {currency, amount}
        })
        
    return render(request, 'group_list.html', {'groups_data': groups_data})

@login_required
def group_detail(request, group_id):
    group = get_object_or_404(groups, pk=group_id, users=request.user, deleted=0)
    group_expenses = GroupExpense.objects.filter(group=group, deleted=0).order_by('-created_at')
    
    # Identify currencies used in this group
    currencies = GroupExpense.objects.filter(group=group, deleted=0).values_list('currency', flat=True).distinct()
    if not currencies:
        currencies = ['USD'] # Default if no expenses

    balances_by_currency = {}
    
    members = group.users.all()

    for currency in currencies:
        # 1. Calculate net balance for everyone in this currency
        net_balances = {}
        for member in members:
            # Filter by currency
            paid = ExpensePayment.objects.filter(expense__group=group, expense__currency=currency, user=member, expense__deleted=0).aggregate(Sum('amount'))['amount__sum'] or 0
            owed = ExpenseSplit.objects.filter(expense__group=group, expense__currency=currency, user=member, expense__deleted=0).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
            net_balances[member] = float(paid - owed)
        
        # Check Ledger Integrity
        total_system_balance = sum(net_balances.values())
        ledger_error = abs(total_system_balance) > 0.05
        
        debts = []
        if not ledger_error:
             # Calculate debts "Who Owes Whom"
            debtors = []
            creditors = []
            for member, balance in net_balances.items():
                if balance < -0.01:
                    debtors.append({'user': member, 'amount': abs(balance)})
                elif balance > 0.01:
                    creditors.append({'user': member, 'amount': balance})
            
            debtors.sort(key=lambda x: x['amount'], reverse=True)
            creditors.sort(key=lambda x: x['amount'], reverse=True)

            i = 0 
            j = 0 

            while i < len(debtors) and j < len(creditors):
                debtor = debtors[i]
                creditor = creditors[j]
                amount = min(debtor['amount'], creditor['amount'])
                
                debts.append({
                    'debtor': debtor['user'],
                    'creditor': creditor['user'],
                    'amount': round(amount, 2)
                })
                
                debtor['amount'] -= amount
                creditor['amount'] -= amount
                
                if debtor['amount'] < 0.01: i += 1
                if creditor['amount'] < 0.01: j += 1
        
        balances_by_currency[currency] = {
            'net_balances': net_balances,
            'debts': debts,
            'ledger_error': ledger_error
        }

    return render(request, 'group_detail.html', {
        'group': group,
        'expenses': group_expenses,
        'balances_by_currency': balances_by_currency,
        # 'debts': debts, # Deprecated
        # 'ledger_error': ledger_error, # Deprecated
        # 'net_balances': net_balances # Deprecated
    })
    


@login_required
def add_group_expense(request, group_id):
    group = get_object_or_404(groups, pk=group_id, users=request.user, deleted=0)
    members = group.users.all()

    if request.method == 'POST':
        form = GroupExpenseForm(request.POST, group=group)
        if form.is_valid():
            # Validate BEFORE saving
            split_type = form.cleaned_data['split_type']
            amount = form.cleaned_data['amount']
            
            involved_members = members
            split_data = {} # Store captured split data to avoid reading POST twice

            if split_type == 'EXACT':
                total_split = 0
                for member in involved_members:
                    amount_str = request.POST.get(f'split_amount_{member.id}')
                    if amount_str:
                        try:
                            val = float(amount_str)
                            total_split += val
                            split_data[member.id] = val
                        except ValueError:
                            pass # Ignored or handled as 0
                
                # Check tolerance
                if abs(total_split - float(amount)) > 0.05:
                    messages.error(request, f"Error: Total split ({total_split}) must equal expense amount ({amount}).")
                    return render(request, 'add_group_expense.html', {
                        'group': group,
                        'form': form,
                        'members': members
                    })

            # Payment Logic
            payment_type = request.POST.get('payment_type', 'SINGLE')
            # If SINGLE, paid_by is from form (or we fetch it)
            # Form handles 'paid_by' field but we should verify.
            
            # We need to save ExpensePayment records.
            # First, check validation for payments if MULTIPLE
            payment_data = {}
            if payment_type == 'MULTIPLE':
                total_paid = 0
                for member in members:
                    pay_amt = request.POST.get(f'payment_amount_{member.id}')
                    if pay_amt:
                        try:
                            val = float(pay_amt)
                            total_paid += val
                            payment_data[member.id] = val
                        except ValueError:
                            pass
                
                if abs(total_paid - float(amount)) > 0.05:
                     messages.error(request, f"Error: Total payments ({total_paid}) must equal expense amount ({amount}).")
                     # Delete the expense we just created? Or use atomic transaction?
                     # Since we did form.save(commit=False), it's not in DB yet? 
                     # Wait, I did form.save() earlier for the old logic.
                     # I should move save after validation.
                     return render(request, 'add_group_expense.html', {
                        'group': group,
                        'form': form,
                        'members': members
                    })
            
            # --- SAVE EXPENSE ---
            expense = form.save(commit=False)
            expense.group = group
            expense.save() 
            # Note: expense.paid_by might be set if SINGLE, but we can ignore it or keep it as "primary".
            
            # Create ExpensePayment records
            if payment_type == 'MULTIPLE':
                 for member in members:
                    if member.id in payment_data:
                        ExpensePayment.objects.create(
                            expense=expense,
                            user=member,
                            amount=payment_data[member.id]
                        )
            else: # SINGLE
                # Use the user from the form
                payer = form.cleaned_data['paid_by']
                ExpensePayment.objects.create(
                    expense=expense,
                    user=payer,
                    amount=amount
                )

            # --- SPLIT LOGIC ---
            if split_type == 'EQUAL':
                split_amount = amount / involved_members.count()
                for member in involved_members:
                    ExpenseSplit.objects.create(
                        expense=expense,
                        user=member,
                        amount_owed=split_amount
                    )
            elif split_type == 'EXACT':
                for member in involved_members:
                    if member.id in split_data:
                         ExpenseSplit.objects.create(
                            expense=expense,
                            user=member,
                            amount_owed=split_data[member.id]
                        )

            messages.success(request, 'Expense added successfully!')
            return redirect('group_detail', group_id=group.id)
    else:
        # Pre-select current user as default
        form = GroupExpenseForm(group=group, initial={'paid_by': request.user})

    return render(request, 'add_group_expense.html', {
        'group': group,
        'form': form,
        'members': members
    })

@login_required
def edit_group_expense(request, expense_id):
    expense = get_object_or_404(GroupExpense, pk=expense_id, deleted=0)
    group = expense.group
    
    # Check if user is member of the group
    if request.user not in group.users.all():
         messages.error(request, "You do not have permission to edit this expense.")
         return redirect('group_detail', group_id=group.id)

    members = group.users.all()

    if request.method == 'POST':
        form = GroupExpenseForm(request.POST, instance=expense, group=group)
        if form.is_valid():
            # Validate Exact Splits if applicable
            split_type = form.cleaned_data['split_type']
            amount = form.cleaned_data['amount']
            involved_members = members
            split_data = {}

            if split_type == 'EXACT':
                total_split = 0
                for member in involved_members:
                    amount_str = request.POST.get(f'split_amount_{member.id}')
                    if amount_str:
                        try:
                            val = float(amount_str)
                            total_split += val
                            split_data[member.id] = val
                        except ValueError:
                            pass
                
                if abs(total_split - float(amount)) > 0.05:
                    messages.error(request, f"Error: Total split ({total_split}) must equal expense amount ({amount}).")
                    return render(request, 'add_group_expense.html', {
                        'group': group,
                        'form': form,
                        'members': members,
                        'editing': True,
                        'expense': expense
                    })

            # Payment Logic
            payment_type = request.POST.get('payment_type', 'SINGLE')
            payment_data = {}
            if payment_type == 'MULTIPLE':
                total_paid = 0
                for member in members:
                    pay_amt = request.POST.get(f'payment_amount_{member.id}')
                    if pay_amt:
                        try:
                            val = float(pay_amt)
                            total_paid += val
                            payment_data[member.id] = val
                        except ValueError:
                            pass
                
                if abs(total_paid - float(amount)) > 0.05:
                     messages.error(request, f"Error: Total payments ({total_paid}) must equal expense amount ({amount}).")
                     # Pass context back
                     return render(request, 'add_group_expense.html', {
                        'group': group,
                        'form': form,
                        'members': members,
                        'editing': True,
                        'expense': expense
                    })

            # Save Expense
            expense = form.save()

            # Update Payments (Delete Old, Create New)
            ExpensePayment.objects.filter(expense=expense).delete()
            
            if payment_type == 'MULTIPLE':
                 for member in members:
                    if member.id in payment_data:
                        ExpensePayment.objects.create(
                            expense=expense,
                            user=member,
                            amount=payment_data[member.id]
                        )
            else: # SINGLE
                payer = form.cleaned_data['paid_by']
                ExpensePayment.objects.create(
                    expense=expense,
                    user=payer,
                    amount=amount
                )

            # Re-Calculate Splits
            # Crude approach: Delete all existing splits and recreate
            # In a better app, we might try to update existing ones, but recreation is safer for consistency
            ExpenseSplit.objects.filter(expense=expense).delete()

            if split_type == 'EQUAL':
                split_amount = amount / involved_members.count()
                for member in involved_members:
                    ExpenseSplit.objects.create(
                        expense=expense,
                        user=member,
                        amount_owed=split_amount
                    )
            elif split_type == 'EXACT':
                 for member in involved_members:
                    if member.id in split_data:
                         ExpenseSplit.objects.create(
                            expense=expense,
                            user=member,
                            amount_owed=split_data[member.id]
                        )
            
            messages.success(request, 'Expense updated successfully!')
            return redirect('group_detail', group_id=group.id)
    else:
        # Pre-populate form
        form = GroupExpenseForm(instance=expense, group=group)

    return render(request, 'add_group_expense.html', {
        'group': group,
        'form': form,
        'members': members,
        'editing': True,
        'expense': expense
    })

@login_required
def delete_group_expense(request, expense_id):
    expense = get_object_or_404(GroupExpense, pk=expense_id, deleted=0)
    group = expense.group
    
    if request.user not in group.users.all():
         messages.error(request, "You do not have permission to delete this expense.")
         return redirect('group_detail', group_id=group.id)

    if request.method == 'POST':
        expense.deleted = True
        expense.save()
        # Also mark splits as deleted? No, they are cascaded or just ignored if expense is deleted.
        # But wait, splits don't have 'deleted' field.
        # But our queries duplicate filter: ExpenseSplit.objects.filter(expense__deleted=0)
        # So it should be fine.
        messages.success(request, 'Expense deleted successfully!')
        return redirect('group_detail', group_id=group.id)

    return render(request, 'group_expense_confirm_delete.html', {'expense': expense})
