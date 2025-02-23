from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_list, name='expenses'),
    path('investments/', views.investments, name='investments'),
    path('add/', views.expense_add, name='expense_add'),
    path('update/<int:expense_id>/', views.expense_update, name='expense_update'),
    path('delete/<int:expense_id>/', views.expense_delete, name='expense_delete'),
    path('category/', views.category_list, name='category_list'),
    path('category/add/', views.category_add, name='category_add'),
    path('category/update/<int:category_id>/', views.category_update, name='category_update'),
    path('category/delete/<int:category_id>/', views.category_delete, name='category_delete'),
    path('payment-method/', views.payment_method_list, name='payment_method_list'),
    path('payment-method/add/', views.payment_method_add, name='payment_method_add'),
    path('payment-method/update/<int:payment_method_id>/', views.payment_method_update, name='payment_method_update'),
    path('payment-method/delete/<int:payment_method_id>/', views.payment_method_delete, name='payment_method_delete'),
    path('spending/', views.spending, name='spendings'),
]
