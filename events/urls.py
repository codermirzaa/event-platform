from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # F-04: Discovery
    path('', views.event_list, name='list'),
    path('<int:pk>/', views.event_detail, name='detail'),

    # F-03: Organizer management
    path('create/', views.event_create, name='create'),
    path('<int:pk>/edit/', views.event_edit, name='edit'),
    path('<int:pk>/cancel/', views.event_cancel, name='cancel'),
    path('my-events/', views.my_events, name='my_events'),
    path('<int:pk>/attendees/', views.event_attendees, name='attendees'),

    # F-05: Booking
    path('<int:pk>/book/', views.book_ticket, name='book'),
    path('booking/<int:pk>/confirmation/', views.booking_confirmation, name='booking_confirmation'),
    path('booking/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),

    # F-07: Admin
    path('admin/events/', views.admin_events, name='admin_events'),
    path('admin/events/<int:pk>/action/', views.admin_event_action, name='admin_event_action'),
]
