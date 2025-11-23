from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('staff-login/', views.staff_login, name='staff_login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register_info, name='register'),
    path('profile/', views.user_profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('search/', views.search_users, name='search_users'),
]
