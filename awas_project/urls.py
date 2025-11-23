"""
URL configuration for awas_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('billing/', include('billing.urls')),
    path('payments/', include('payments.urls')),
    path('complaints/', include('complaints.urls')),
]

# Serve media and static files in development
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    
    # Serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Serve static files from all static directories
    urlpatterns += staticfiles_urlpatterns()

# Customize admin site
admin.site.site_header = "AWAS Administration"
admin.site.site_title = "AWAS Admin Portal"
admin.site.index_title = "Welcome to AWAS Water Billing System"
