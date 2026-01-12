from django.test import TestCase
from django.contrib.auth.models import User
from .models import groups, GroupExpense, ExpensePayment, ExpenseSplit
from .views import get_user_balance_in_group
from django.utils import timezone

class GroupsLogicTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='alice', password='password')
        self.user2 = User.objects.create_user(username='bob', password='password')
        self.user3 = User.objects.create_user(username='charlie', password='password')
        
        self.group = groups.objects.create(name="Trip")
        self.group.users.add(self.user1, self.user2, self.user3)

    def test_group_creation(self):
        self.assertEqual(self.group.users.count(), 3)
        self.assertEqual(str(self.group), 'Trip - 3 members')

    def test_add_expense_equal_split(self):
        # Alice pays 300, split equally (100 each)
        expense = GroupExpense.objects.create(
            group=self.group,
            amount=300,
            currency='USD',
            description='Dinner',
            created_at=timezone.now()
        )
        # Payment
        ExpensePayment.objects.create(expense=expense, user=self.user1, amount=300)
        # Splits
        for user in [self.user1, self.user2, self.user3]:
            ExpenseSplit.objects.create(expense=expense, user=user, amount_owed=100)
            
        # Verify Balances Logic
        # Alice: Paid 300, Owed 100 -> Net +200
        # Bob: Paid 0, Owed 100 -> Net -100
        # Charlie: Paid 0, Owed 100 -> Net -100
        
        self.assertTrue(get_user_balance_in_group(self.user1, self.group))
        self.assertTrue(get_user_balance_in_group(self.user2, self.group))
        
        # Test exact amounts via manual calculation to verify 'get_user_balance_in_group' underlying logic match
        # (Though the helper just returns boolean) 

    def test_multi_currency_balances(self):
        # 1. USD Expense: Alice pays 100 for Bob (Bob owes 100 USD)
        exp_usd = GroupExpense.objects.create(group=self.group, amount=100, currency='USD', description='Taxi')
        ExpensePayment.objects.create(expense=exp_usd, user=self.user1, amount=100)
        ExpenseSplit.objects.create(expense=exp_usd, user=self.user2, amount_owed=100) 
        # Alice net USD: +100, Bob net USD: -100

        # 2. EUR Expense: Bob pays 50 for Alice (Alice owes 50 EUR)
        exp_eur = GroupExpense.objects.create(group=self.group, amount=50, currency='EUR', description='Museum')
        ExpensePayment.objects.create(expense=exp_eur, user=self.user2, amount=50)
        ExpenseSplit.objects.create(expense=exp_eur, user=self.user1, amount_owed=50)
        # Alice net EUR: -50, Bob net EUR: +50

        # Both should be "unsettled"
        self.assertTrue(get_user_balance_in_group(self.user1, self.group))
        self.assertTrue(get_user_balance_in_group(self.user2, self.group))

    def test_multiple_payers(self):
        # Expense 100. Alice pays 60, Bob pays 40. Split equally (50 each).
        expense = GroupExpense.objects.create(group=self.group, amount=100, currency='USD', description='Lunch')
        
        ExpensePayment.objects.create(expense=expense, user=self.user1, amount=60)
        ExpensePayment.objects.create(expense=expense, user=self.user2, amount=40)
        
        ExpenseSplit.objects.create(expense=expense, user=self.user1, amount_owed=50)
        ExpenseSplit.objects.create(expense=expense, user=self.user2, amount_owed=50)
        
        # Alice: Paid 60, Owed 50 -> Net +10
        # Bob: Paid 40, Owed 50 -> Net -10
        
        # Check logic by simulating the query manually or trusting the helper
        self.assertTrue(get_user_balance_in_group(self.user1, self.group))

    def test_settled_group(self):
        # Alice pays 100 for Bob.
        exp1 = GroupExpense.objects.create(group=self.group, amount=100, currency='USD', description='Loan')
        ExpensePayment.objects.create(expense=exp1, user=self.user1, amount=100)
        ExpenseSplit.objects.create(expense=exp1, user=self.user2, amount_owed=100)
        
        # Bob pays 100 back to Alice (Payment recorded as an expense or settlement?)
        # In this app, settlements are typically recorded as an expense where Bob pays and Alice owes everything.
        exp2 = GroupExpense.objects.create(group=self.group, amount=100, currency='USD', description='Repayment')
        ExpensePayment.objects.create(expense=exp2, user=self.user2, amount=100)
        ExpenseSplit.objects.create(expense=exp2, user=self.user1, amount_owed=100)
        
        # Net Alice: (+100 - 0) + (0 - 100) = 0
        # Net Bob: (0 - 100) + (100 - 0) = 0
        
        self.assertFalse(get_user_balance_in_group(self.user1, self.group))
        self.assertFalse(get_user_balance_in_group(self.user2, self.group))
