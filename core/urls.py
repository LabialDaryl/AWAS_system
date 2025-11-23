from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('home/', views.home, name='home'),
    path('connection-request/', views.connection_request, name='connection_request'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('notifications/mark-viewed/', views.mark_notifications_viewed, name='mark_notifications_viewed'),
    path('notifications/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
