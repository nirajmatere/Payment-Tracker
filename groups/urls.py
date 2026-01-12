from django.urls import path
from . import views

urlpatterns = [
    path('', views.group_list, name='groups'),
    path('<int:group_id>/', views.group_detail, name='group_detail'),
    path('<int:group_id>/add_expense/', views.add_group_expense, name='add_group_expense'),
    path('expense/<int:expense_id>/edit/', views.edit_group_expense, name='edit_group_expense'),
    path('expense/<int:expense_id>/delete/', views.delete_group_expense, name='delete_group_expense'),
]
