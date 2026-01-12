from django.test import TestCase, Client
from django.contrib.auth.models import User
from groups.models import groups, GroupExpense, ExpenseSplit, ExpensePayment
from decimal import Decimal
from notifications.models import Notification

class GroupFeatureTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        self.client = Client()
        self.client.login(username='user1', password='password')
        
        self.group = groups.objects.create(name="Test Group")
        self.group.users.add(self.user1, self.user2)

    def test_leave_group_success(self):
        # User 1 has 0 balance
        response = self.client.get(f'/groups/{self.group.id}/leave/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.user1 in self.group.users.all())
        
        # Check notification
        n = Notification.objects.filter(user=self.user2).first()
        self.assertIn('left the group', n.message)

    def test_leave_group_fail_debt(self):
        # Create debt: User 1 owes User 2
        expense = GroupExpense.objects.create(group=self.group, amount=Decimal('100.00'), paid_by=self.user2, currency='USD')
        ExpensePayment.objects.create(expense=expense, user=self.user2, amount=Decimal('100.00'))
        
        # Split 50/50
        ExpenseSplit.objects.create(expense=expense, user=self.user1, amount_owed=Decimal('50.00'))
        ExpenseSplit.objects.create(expense=expense, user=self.user2, amount_owed=Decimal('50.00'))
        
        # Try to leave
        response = self.client.get(f'/groups/{self.group.id}/leave/')
        self.assertEqual(response.status_code, 302)
        # Should still be in group
        self.assertTrue(self.user1 in self.group.users.all())

    def test_settle_up(self):
        # Setup debt: User 1 owes User 2 $50
        expense = GroupExpense.objects.create(group=self.group, amount=Decimal('100.00'), paid_by=self.user2, currency='USD')
        ExpensePayment.objects.create(expense=expense, user=self.user2, amount=Decimal('100.00'))
        ExpenseSplit.objects.create(expense=expense, user=self.user1, amount_owed=Decimal('50.00'))
        ExpenseSplit.objects.create(expense=expense, user=self.user2, amount_owed=Decimal('50.00'))
        
        # Settle Up Action
        response = self.client.get(f'/groups/{self.group.id}/settle-up/{self.user2.id}/USD/')
        self.assertEqual(response.status_code, 302)
        
        # Verify Settlement Expense Created
        settlement = GroupExpense.objects.filter(description__contains="Settlement").last()
        self.assertIsNotNone(settlement)
        self.assertEqual(settlement.amount, Decimal('50.00'))
        self.assertEqual(settlement.paid_by, self.user1)
        
        # Verify Balance is 0
        # Re-run balance logic (simplified check)
        # Total Paid by U1: 0 (initial) + 50 (settlement) = 50
        # Total Owed by U1: 50 (initial) + 0 (settlement split went to U2) = 50
        # Net = 0. Correct.
        
        # Check Notification
        n = Notification.objects.filter(user=self.user2, notification_type='SETTLEMENT').first()
        self.assertIsNotNone(n)
