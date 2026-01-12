import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from groups.models import groups, GroupExpense, ExpenseSplit
from django.db.models import Sum

def verify():
    print("Setting up test data...")
    # Setup
    u1, _ = User.objects.get_or_create(username='test_user1')
    u2, _ = User.objects.get_or_create(username='test_user2')
    group, _ = groups.objects.get_or_create(name='Test Verify Group')
    group.users.add(u1, u2)

    # Clean previous runs
    GroupExpense.objects.filter(group=group).delete()

    print("Creating expense...")
    # Create Expense (User1 pays 100)
    expense = GroupExpense.objects.create(
        group=group,
        paid_by=u1,
        amount=100.00,
        description='Test Dinner'
    )

    # Create Splits (Equally: 50 each)
    ExpenseSplit.objects.create(expense=expense, user=u1, amount_owed=50.00)
    ExpenseSplit.objects.create(expense=expense, user=u2, amount_owed=50.00)

    # Verification
    print(f"Expense created: {expense}")
    splits = expense.splits.all()
    print(f"Splits count: {splits.count()}")
    for s in splits:
        print(f"- {s}")

    # Check Balances Logic (mimic view)
    print("\nCalculating Balances...")
    
    # User 1
    total_paid = GroupExpense.objects.filter(group=group, paid_by=u1).aggregate(Sum('amount'))['amount__sum'] or 0
    total_owed = ExpenseSplit.objects.filter(expense__group=group, user=u1).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
    net = total_paid - total_owed
    print(f"User1 (Payer): Paid={total_paid}, Owed={total_owed}, Net={net} (Expected +50.00)")

    # User 2
    total_paid2 = GroupExpense.objects.filter(group=group, paid_by=u2).aggregate(Sum('amount'))['amount__sum'] or 0
    total_owed2 = ExpenseSplit.objects.filter(expense__group=group, user=u2).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
    net2 = total_paid2 - total_owed2
    print(f"User2 (Ower): Paid={total_paid2}, Owed={total_owed2}, Net={net2} (Expected -50.00)")

    if net == 50.00 and net2 == -50.00:
        print("\nSUCCESS: Balances verified correctly.")
    else:
        print("\nFAILURE: Balances calculation incorrect.")

if __name__ == "__main__":
    verify()
