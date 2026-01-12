from django.urls import path
from . import views

urlpatterns = [
    path('', views.group_list, name='groups'),
    path('add/', views.group_add, name='group_add'),
    path('<int:group_id>/edit/', views.group_edit, name='group_edit'),
    path('<int:group_id>/delete/', views.group_delete, name='group_delete'),
    path('<int:group_id>/', views.group_detail, name='group_detail'),
    path('<int:group_id>/leave/', views.leave_group, name='leave_group'),
    path('<int:group_id>/settle-up/<int:user_id>/<str:currency>/', views.settle_up, name='settle_up'),
    path('<int:group_id>/add_expense/', views.add_group_expense, name='add_group_expense'),
    path('expense/<int:expense_id>/edit/', views.edit_group_expense, name='edit_group_expense'),
    path('expense/<int:expense_id>/delete/', views.delete_group_expense, name='delete_group_expense'),
]
