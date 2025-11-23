from django.urls import path
from . import views

app_name = 'complaints'

urlpatterns = [
    # Customer views
    path('', views.complaint_list, name='complaint_list'),
    path('create/', views.create_complaint, name='create_complaint'),
    path('<int:complaint_id>/', views.complaint_detail, name='complaint_detail'),
    path('<int:complaint_id>/comment/', views.add_comment, name='add_comment'),
    
    # Staff views
    path('staff/', views.staff_complaint_list, name='staff_complaint_list'),
    path('staff/<int:complaint_id>/respond/', views.respond_to_complaint, name='respond_to_complaint'),
]
