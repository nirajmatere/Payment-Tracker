import os
import django
import sys

# Setup Django environment
sys.path.append(r'c:\Users\gunja\OneDrive\Desktop\Projects\Django\project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from groups.models import GroupExpense, ExpenseSplit, groups
from django.db.models import Sum

def check_ledger(group):
    print(f"--- Group: {group.name} (ID: {group.id}) ---")
    
    members = group.users.all()
    total_system_balance = 0
    has_activity = False
    
    for member in members:
        paid = GroupExpense.objects.filter(group=group, paid_by=member, deleted=0).aggregate(Sum('amount'))['amount__sum'] or 0
        owed = ExpenseSplit.objects.filter(expense__group=group, user=member, expense__deleted=0).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
        
        if paid == 0 and owed == 0:
            continue
            
        has_activity = True
        net = float(paid - owed)
        total_system_balance += net
        print(f"User: {member.username} | Paid: {paid} | Owed: {owed} | Net: {net}")
        
    print(f"Sum of Net Balances: {total_system_balance}")
    
    if abs(total_system_balance) > 0.05:
        print(">> CRITICAL: Ledger IMBALANCED <<")
    else:
        print(">> Ledger Balanced <<")
    print("\n")

all_groups = groups.objects.all()
for g in all_groups:
    check_ledger(g)
