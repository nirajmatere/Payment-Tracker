from django.test import TestCase, Client
from django.contrib.auth.models import User
from notifications.models import Notification
from groups.models import groups

class NotificationTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        self.client = Client()
        self.client.login(username='user1', password='password')

    def test_notification_model(self):
        notification = Notification.objects.create(
            user=self.user1,
            message="Test Notification",
            notification_type='SYSTEM'
        )
        self.assertEqual(notification.is_read, False)
        self.assertEqual(str(notification), "Notification for user1: Test Notification")

    def test_notification_view(self):
        n = Notification.objects.create(user=self.user1, message="Hello")
        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello")
        # Verify Mark as Read button link is present
        self.assertContains(response, f'/notifications/mark-read/{n.id}/')

    def test_mark_as_read(self):
        notification = Notification.objects.create(user=self.user1, message="To Read")
        response = self.client.get(f'/notifications/mark-read/{notification.id}/')
        self.assertEqual(response.status_code, 302) # Redirects
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_group_add_trigger(self):
        # User1 creates a group and adds User2
        response = self.client.post('/groups/add/', {
            'name': 'Test Group',
            'users': [self.user2.id] # Select User2
        })
        self.assertEqual(response.status_code, 302)

        # check if User2 got a notification
        notifications = Notification.objects.filter(user=self.user2)
        self.assertEqual(notifications.count(), 1)
        self.assertIn("added to the group", notifications.first().message)
        
        # User1 (creator) should NOT get a notification for adding themselves
        notifications_creator = Notification.objects.filter(user=self.user1)
        self.assertEqual(notifications_creator.count(), 0)

    def test_context_processor(self):
        # Create unread notification
        Notification.objects.create(user=self.user1, message="Context Check", is_read=False)
        Notification.objects.create(user=self.user1, message="Read Msg", is_read=True)
        
        # Check context
        response = self.client.get('/expenses/') # Any page that renders layout
        self.assertIn('unread_notification_count', response.context)
        self.assertEqual(response.context['unread_notification_count'], 1)
