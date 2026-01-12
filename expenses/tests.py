from django.test import TestCase
from django.contrib.auth.models import User
from .models import Category, PaymentMethod, Expenses
from django.utils import timezone

class ExpensesModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(user=self.user, name='Food')
        self.payment_method = PaymentMethod.objects.create(user=self.user, name='Cash')

    def test_category_creation(self):
        self.assertEqual(self.category.name, 'Food')
        self.assertEqual(str(self.category), 'Food')
        self.assertFalse(self.category.deleted)

    def test_payment_method_creation(self):
        self.assertEqual(self.payment_method.name, 'Cash')
        self.assertEqual(str(self.payment_method), 'Cash')
        self.assertFalse(self.payment_method.deleted)

    def test_expense_creation(self):
        expense = Expenses.objects.create(
            user=self.user,
            item='Lunch',
            price=25.50,
            category=self.category,
            payment_method=self.payment_method,
            created_at=timezone.now()
        )
        self.assertEqual(expense.item, 'Lunch')
        self.assertEqual(expense.price, 25.50)
        self.assertEqual(expense.category, self.category)
        self.assertEqual(str(expense), 'Lunch - 25.5')

    def test_soft_delete(self):
        self.category.deleted = True
        self.category.save()
        self.assertTrue(Category.objects.get(id=self.category.id).deleted)
