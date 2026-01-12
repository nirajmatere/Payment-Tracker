from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification

@login_required
def notification_list(request):
    # Fetch all notifications for the user
    notifications = Notification.objects.filter(user=request.user)
    
    # Mark all unread notifications as read when visiting the dashboard
    # Alternatively, we can let user manually mark them. 
    # Let's keep manual marking for now, but maybe bulk mark all button.
    
    return render(request, 'notifications.html', {'notifications': notifications})

@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    # If AJAX request, return JSON, else redirect back
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications')

@login_required
def mark_all_as_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')
