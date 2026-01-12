from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from .models import groups, GroupExpense, ExpenseSplit, ExpensePayment
from .forms import GroupExpenseForm, GroupForm
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Sum
from notifications.models import Notification

# Create your views here.

from decimal import Decimal

# Helper function to check member debt
def get_user_balance_in_group(user, group):
    """
    Returns True if the user has a non-zero balance (owe or owed) in ANY currency.
    """
    currencies = GroupExpense.objects.filter(group=group, deleted=0).values_list('currency', flat=True).distinct()
    for currency in currencies:
        # Filter ExpensePayment and ExpenseSplit by deleted=0 as well for robustness
        paid = ExpensePayment.objects.filter(
            expense__group=group, 
            expense__currency=currency, 
            user=user, 
            expense__deleted=0,
            deleted=0
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        owed = ExpenseSplit.objects.filter(
            expense__group=group, 
            expense__currency=currency, 
            user=user, 
            expense__deleted=0,
            deleted=0
        ).aggregate(Sum('amount_owed'))['amount_owed__sum'] or Decimal('0.00')
        
        if abs(paid - owed) > Decimal('0.01'):
            return True # User has outstanding balance
    return False

@login_required
def group_list(request):
    user = request.user
    groups_data = []
    user_groups = groups.objects.filter(users=user, deleted=0)
    
    # --- Bulk Fetch Balances to fix N+1 Query Issue ---
    
    # 1. Fetch total paid by user per (group, currency)
    payments = ExpensePayment.objects.filter(
        expense__group__in=user_groups,
        user=user,
        expense__deleted=0,
        deleted=0
    ).values('expense__group', 'expense__currency').annotate(total_paid=Sum('amount'))
    
    # Map: (group_id, currency) -> amount
    payment_map = {}
    for p in payments:
        k = (p['expense__group'], p['expense__currency'])
        payment_map[k] = p['total_paid']

    # 2. Fetch total owed by user per (group, currency)
    splits = ExpenseSplit.objects.filter(
        expense__group__in=user_groups,
        user=user,
        expense__deleted=0,
        deleted=0
    ).values('expense__group', 'expense__currency').annotate(total_owed=Sum('amount_owed'))
    
    # Map: (group_id, currency) -> amount
    split_map = {}
    for s in splits:
        k = (s['expense__group'], s['expense__currency'])
        split_map[k] = s['total_owed']
        
    # 3. Identify all unique currencies per group to display
    # This is a bit tricky since we need currencies even if balance is 0?
    # Usually we only care about non-zero balances or active currencies.
    # Let's fetch all currencies used in these groups.
    group_currencies = GroupExpense.objects.filter(
        group__in=user_groups, 
        deleted=0
    ).values_list('group', 'currency').distinct()
    
    currency_map = {} # group_id -> set(currencies)
    for g_id, curr in group_currencies:
        if g_id not in currency_map: currency_map[g_id] = set()
        currency_map[g_id].add(curr)

    for group in user_groups:
        balances = []
        # Get currencies for this group, default to USD if none
        currencies = currency_map.get(group.id, {'USD'})
        if not currencies: currencies = {'USD'} # Fallback if set is empty
        
        for currency in currencies:
            paid = payment_map.get((group.id, currency), Decimal('0.00'))
            owed = split_map.get((group.id, currency), Decimal('0.00'))
            
            net = paid - owed
            if abs(net) > Decimal('0.01'):
                balances.append({'currency': currency, 'amount': net})
        
        groups_data.append({
            'group': group,
            'balances': balances 
        })
        
    return render(request, 'group_list.html', {'groups_data': groups_data})

@login_required
def group_add(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            new_group = form.save()
            # Ensure the creator is part of the group
            new_group.users.add(request.user)
            
            # Notify members
            for user in form.cleaned_data['users']:
                if user != request.user:
                    Notification.objects.create(
                        user=user,
                        message=f"You have been added to the group '{new_group.name}' by {request.user.username}.",
                        notification_type='GROUP_ADD',
                        related_link=f"/groups/{new_group.id}/"
                    )

            messages.success(request, 'Group created successfully!')
            return redirect('groups')
    else:
        form = GroupForm()
    
    return render(request, 'group_form.html', {'form': form})

@login_required
def group_edit(request, group_id):
    group = get_object_or_404(groups, pk=group_id, users=request.user, deleted=0)
    
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            # Validate user removal
            original_members = set(group.users.all())
            new_members = set(form.cleaned_data['users'])
            removed_members = original_members - new_members
            
            error_found = False
            for member in removed_members:
                if get_user_balance_in_group(member, group):
                    messages.error(request, f"Cannot remove {member.username} because they have an outstanding balance.")
                    error_found = True
            
            if not error_found:
                form.save()
                
                # Notify NEW members
                added_members = new_members - original_members
                for member in added_members:
                    if member != request.user:
                         Notification.objects.create(
                            user=member,
                            message=f"You have been added to the group '{group.name}' by {request.user.username}.",
                            notification_type='GROUP_ADD',
                            related_link=f"/groups/{group.id}/"
                        )

                messages.success(request, 'Group updated successfully!')
                return redirect('group_detail', group_id=group.id)
    else:
        form = GroupForm(instance=group)
    
    return render(request, 'group_form.html', {'form': form, 'group': group})

@login_required
def group_delete(request, group_id):
    group = get_object_or_404(groups, pk=group_id, users=request.user, deleted=0)
    
    if request.method == 'POST':
        # Check if anyone in the group has a balance
        # If any user in the group has a non-zero balance in any currency, cannot delete.
        members = group.users.all()
        for member in members:
            if get_user_balance_in_group(member, group):
                messages.error(request, "Cannot delete group because there are unsettled debts.")
                return redirect('group_detail', group_id=group.id)

        group.deleted = True
        group.save()
        messages.success(request, 'Group deleted successfully!')
        return redirect('groups')
    
    return render(request, 'group_confirm_delete.html', {'group': group})

@login_required
def group_detail(request, group_id):
    group = get_object_or_404(groups, pk=group_id, users=request.user, deleted=0)
    # Filter only non-deleted expenses
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
             # Add deleted=0 filter
            paid = ExpensePayment.objects.filter(
                expense__group=group, 
                expense__currency=currency, 
                user=member, 
                expense__deleted=0,
                deleted=0
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            
            owed = ExpenseSplit.objects.filter(
                expense__group=group, 
                expense__currency=currency, 
                user=member, 
                expense__deleted=0,
                deleted=0
            ).aggregate(Sum('amount_owed'))['amount_owed__sum'] or Decimal('0.00')
            
            net_balances[member] = paid - owed
        
        # Check Ledger Integrity
        total_system_balance = sum(net_balances.values())
        ledger_error = abs(total_system_balance) > Decimal('0.05')
        
        debts = []
        if not ledger_error:
             # Calculate debts "Who Owes Whom"
            debtors = []
            creditors = []
            for member, balance in net_balances.items():
                if balance < Decimal('-0.01'):
                    debtors.append({'user': member, 'amount': abs(balance)})
                elif balance > Decimal('0.01'):
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
                
                if debtor['amount'] < Decimal('0.01'): i += 1
                if creditor['amount'] < Decimal('0.01'): j += 1
        
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
            amount = form.cleaned_data['amount'] # This is already Decimal
            
            involved_members = members
            split_data = {} # Store captured split data to avoid reading POST twice

            if split_type == 'EXACT':
                total_split = Decimal('0.00')
                for member in involved_members:
                    amount_str = request.POST.get(f'split_amount_{member.id}')
                    if amount_str:
                        try:
                            val = Decimal(amount_str)
                            total_split += val
                            split_data[member.id] = val
                        except Exception:
                            pass # Ignored or handled as 0
                
                # Check tolerance
                if abs(total_split - amount) > Decimal('0.05'):
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
                total_paid = Decimal('0.00')
                for member in members:
                    pay_amt = request.POST.get(f'payment_amount_{member.id}')
                    if pay_amt:
                        try:
                            val = Decimal(pay_amt)
                            total_paid += val
                            payment_data[member.id] = val
                        except Exception:
                            pass
                
                if abs(total_paid - amount) > Decimal('0.05'):
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
                split_amount = amount / Decimal(involved_members.count())
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
            
            # Notify group members
            for member in group.users.all():
                if member != request.user:
                    Notification.objects.create(
                        user=member,
                        message=f"New expense '{expense.description}' added in '{group.name}' by {request.user.username}.",
                        notification_type='EXPENSE_ADD',
                        related_link=f"/groups/{group.id}/"
                    )

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
                total_split = Decimal('0.00')
                for member in involved_members:
                    amount_str = request.POST.get(f'split_amount_{member.id}')
                    if amount_str:
                        try:
                            val = Decimal(amount_str)
                            total_split += val
                            split_data[member.id] = val
                        except Exception:
                            pass
                
                if abs(total_split - amount) > Decimal('0.05'):
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
                total_paid = Decimal('0.00')
                for member in members:
                    pay_amt = request.POST.get(f'payment_amount_{member.id}')
                    if pay_amt:
                        try:
                            val = Decimal(pay_amt)
                            total_paid += val
                            payment_data[member.id] = val
                        except Exception:
                            pass
                
                if abs(total_paid - amount) > Decimal('0.05'):
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

            # Update Payments (SOFT DELETE Old, Create New)
            # Use update(deleted=True) instead of delete()
            ExpensePayment.objects.filter(expense=expense).update(deleted=True)
            
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

            # Re-Calculate Splits (SOFT DELETE Old)
            # Crude approach: Delete all existing splits and recreate
            # In a better app, we might try to update existing ones, but recreation is safer for consistency
            ExpenseSplit.objects.filter(expense=expense).update(deleted=True)

            if split_type == 'EQUAL':
                split_amount = amount / Decimal(involved_members.count())
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

@login_required
def leave_group(request, group_id):
    group = get_object_or_404(groups, pk=group_id, users=request.user, deleted=0)
    
    # Check if user has any outstanding balance in ANY currency
    if get_user_balance_in_group(request.user, group):
        messages.error(request, "Cannot leave group because you have unsettled debts. Please settle up first.")
        return redirect('group_detail', group_id=group.id)

    # Remove user from group
    group.users.remove(request.user)
    
    # Notify other members
    for member in group.users.all():
         Notification.objects.create(
            user=member,
            message=f"{request.user.username} has left the group '{group.name}'.",
            notification_type='SYSTEM', 
            related_link=f"/groups/{group.id}/"
        )
        
    messages.success(request, f"You have left '{group.name}'.")
    return redirect('groups')

@login_required
def settle_up(request, group_id, user_id, currency):
    group = get_object_or_404(groups, pk=group_id, users=request.user, deleted=0)
    target_user = get_object_or_404(User, pk=user_id)
    
    if target_user not in group.users.all():
        messages.error(request, "Target user is not in this group.")
        return redirect('group_detail', group_id=group.id)

    # 1. Calculate exactly how much is owed to this user in this currency
    # We need to reuse the calculation logic or replicate it carefully.
    # Reuse filter logic from group_detail
    
    paid = ExpensePayment.objects.filter(
        expense__group=group, 
        expense__currency=currency, 
        user=request.user, 
        expense__deleted=0,
        deleted=0
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    owed = ExpenseSplit.objects.filter(
        expense__group=group, 
        expense__currency=currency, 
        user=request.user, 
        expense__deleted=0,
        deleted=0
    ).aggregate(Sum('amount_owed'))['amount_owed__sum'] or Decimal('0.00')
    
    net_self = paid - owed # If negative, I owe money.
    
    # But wait, this is MY total balance. I need to know how much I owe specifically to target_user?
    # The current system calculates "Who Owes Whom" based on minimizing transactions locally in `group_detail`.
    # It does NOT track bilateral debts persistently.
    # So "Settle Up" with a specific user is actually "Pay off my debt to the system, and giving it to User X".
    # In a centralized debt simplification (which we implemented in group_detail), 
    # if I show up as "Owe User B $50", it means I should pay User B $50.
    
    # However, since we don't store bilateral debt, we can't easily verify "I owe B $50" from the DB alone 
    # without re-running the simplification algorithm.
    # For now, let's assume the UI button is only shown if the Simplification Alg says I owe B.
    # But for safety, we should re-run the algo here? Or just trust the request amount?
    # Trusting request amount is dangerous.
    # Let's re-run the algo simply to find the matched debt.
    
    # --- Re-run Simplification for this currency ---
    members = group.users.all()
    net_balances = {}
    for member in members:
        p = ExpensePayment.objects.filter(expense__group=group, expense__currency=currency, user=member, expense__deleted=0, deleted=0).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        o = ExpenseSplit.objects.filter(expense__group=group, expense__currency=currency, user=member, expense__deleted=0, deleted=0).aggregate(Sum('amount_owed'))['amount_owed__sum'] or Decimal('0.00')
        net_balances[member] = p - o

    debtors = []
    creditors = []
    for member, balance in net_balances.items():
        if balance < Decimal('-0.01'): debtors.append({'user': member, 'amount': abs(balance)})
        elif balance > Decimal('0.01'): creditors.append({'user': member, 'amount': balance})
    
    debtors.sort(key=lambda x: x['amount'], reverse=True)
    creditors.sort(key=lambda x: x['amount'], reverse=True)

    amount_to_pay = Decimal('0.00')
    
    # Run matching
    i = 0; j = 0
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        amount = min(debtor['amount'], creditor['amount'])
        
        # Check if this match is ME -> Target
        if debtor['user'] == request.user and creditor['user'] == target_user:
            amount_to_pay = amount
            break # Found the match. 
            # Note: In complex scenarios, I might owe multiple people. 
            # This simplistic greedy algo is deterministic, so if it showed up in UI, it should show up here.
        
        debtor['amount'] -= amount
        creditor['amount'] -= amount
        if debtor['amount'] < Decimal('0.01'): i += 1
        if creditor['amount'] < Decimal('0.01'): j += 1
    
    if amount_to_pay < Decimal('0.01'):
         messages.error(request, f"You do not seem to owe {target_user.username} anything in {currency}.")
         return redirect('group_detail', group_id=group.id)

    # 2. Create Settlement Expense
    expense = GroupExpense.objects.create(
        group=group,
        description=f"Settlement to {target_user.username}",
        amount=amount_to_pay,
        currency=currency,
        paid_by=request.user,
        # We can mark it as a special type if we had one, but Description is fine for now.
    )
    
    # 3. Create Payment (I PAID)
    # Wait, "Settlement" means I paid money to Target.
    # So in the system: I Paid X, Target Gets X (or Split is X?)
    # If I record an expense "Settlement":
    #   Determined Payer: ME (Amount X) -> Adds +X to my balance
    #   Split: TARGET (Amount X) -> Subtracts -X from target's balance
    # Result: My Net Balance (+X), Target Net Balance (-X).
    # Since I was (-X) and Target was (+X), this neutralizes both! Correct.
    
    ExpensePayment.objects.create(expense=expense, user=request.user, amount=amount_to_pay)
    ExpenseSplit.objects.create(expense=expense, user=target_user, amount_owed=amount_to_pay)
    
    # 4. Notify Target
    Notification.objects.create(
        user=target_user,
        message=f"{request.user.username} settled up {currency} {amount_to_pay} with you.",
        notification_type='SETTLEMENT',
        related_link=f"/groups/{group.id}/"
    )

    messages.success(request, f"Settled up {currency} {amount_to_pay} with {target_user.username}!")
    return redirect('group_detail', group_id=group.id)
