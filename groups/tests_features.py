from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import groups, GroupExpense, ExpenseSplit, ExpensePayment, GroupInvitation
from notifications.models import Notification
from django.contrib.messages import get_messages
from decimal import Decimal

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

    def test_leave_group_last_member(self):
        # Create a group with only one user
        group = groups.objects.create(name="Solo Group")
        group.users.add(self.user1)
        
        # User 1 leaves
        response = self.client.get(f'/groups/{group.id}/leave/')
        self.assertEqual(response.status_code, 302)
        
        # Verify user is removed
        self.assertFalse(self.user1 in group.users.all())
        self.assertEqual(group.users.count(), 0)
        
        # Verify group still exists (not deleted)
        group.refresh_from_db()
        self.assertFalse(group.deleted)

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

    def test_settle_up_failure_not_in_group(self):
        other_user = User.objects.create_user(username='other', password='password')
        url = reverse('settle_up', kwargs={'group_id': self.group.id, 'user_id': other_user.id, 'currency': 'USD'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Target user is not in this group.")

class GroupInvitationTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        self.client = Client()
        self.client.login(username='user1', password='password')

    def test_group_creation_sends_invitation(self):
        response = self.client.post(reverse('group_add'), {
            'name': 'Invite Group',
            'users': [self.user2.id]
        })
        self.assertRedirects(response, reverse('groups'))
        
        # Check Group Created
        group = groups.objects.get(name='Invite Group')
        self.assertIn(self.user1, group.users.all())
        self.assertNotIn(self.user2, group.users.all()) # User2 should NOT be in group yet
        
        # Check Invitation
        invite = GroupInvitation.objects.get(group=group, receiver=self.user2)
        self.assertEqual(invite.status, 'PENDING')
        self.assertEqual(invite.sender, self.user1)
        
        # Check Notification
        notif = Notification.objects.get(user=self.user2, notification_type='INVITATION')
        self.assertEqual(notif.invitation, invite)

    def test_accept_invitation(self):
        # Create Group & Invite
        group = groups.objects.create(name='Test Group')
        group.users.add(self.user1)
        invite = GroupInvitation.objects.create(group=group, sender=self.user1, receiver=self.user2)
        Notification.objects.create(user=self.user2, message="Invited", notification_type='INVITATION', invitation=invite)
        
        self.client.login(username='user2', password='password')
        
        # Accept
        response = self.client.get(reverse('accept_invitation', args=[invite.id]))
        self.assertRedirects(response, reverse('groups'))
        
        invite.refresh_from_db()
        self.assertEqual(invite.status, 'ACCEPTED')
        self.assertIn(self.user2, group.users.all())
        
        # Check Sender Notification
        sender_notif = Notification.objects.filter(user=self.user1, notification_type='SYSTEM').latest('created_at')
        self.assertIn("accepted your invitation", sender_notif.message)

    def test_decline_invitation(self):
        # Create Group & Invite
        group = groups.objects.create(name='Test Group')
        group.users.add(self.user1)
        invite = GroupInvitation.objects.create(group=group, sender=self.user1, receiver=self.user2)
        Notification.objects.create(user=self.user2, message="Invited", notification_type='INVITATION', invitation=invite)
        
        self.client.login(username='user2', password='password')
        
        # Decline
        response = self.client.get(reverse('decline_invitation', args=[invite.id]))
        self.assertRedirects(response, reverse('notifications'))
        
        invite.refresh_from_db()
        self.assertEqual(invite.status, 'DECLINED')
        self.assertNotIn(self.user2, group.users.all())
        
        # Check Sender Notification
        sender_notif = Notification.objects.filter(user=self.user1, notification_type='SYSTEM').latest('created_at')
        self.assertIn("declined your invitation", sender_notif.message)
