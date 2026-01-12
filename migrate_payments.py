import os
import django
import sys

# Setup Django environment
sys.path.append(r'c:\Users\gunja\OneDrive\Desktop\Projects\Django\project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from groups.models import GroupExpense, ExpensePayment

def migrate_payments():
    expenses = GroupExpense.objects.filter(deleted=False)
    count = 0
    for expense in expenses:
        # Check if payments already exist?
        if expense.payments.exists():
            continue
            
        if expense.paid_by:
            ExpensePayment.objects.create(
                expense=expense,
                user=expense.paid_by,
                amount=expense.amount
            )
            count += 1
            print(f"Migrated payment for: {expense.description}")

    print(f"Migration complete. {count} payments created.")

if __name__ == '__main__':
    migrate_payments()
