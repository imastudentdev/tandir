from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.split_namespaces if hasattr(admin.site, 'split_namespaces') else admin.site.urls),
    path('', include('apps.dashboard.urls', namespace='dashboard')),
    # # ERP Apps URL-lari
    path('users/', include('apps.users.urls', namespace='users')),
    path('products/', include('apps.products.urls', namespace='products')),
    path('recipes/', include('apps.recipes.urls', namespace='recipes')),
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
    path('production/', include('apps.production.urls', namespace='production')),   
    path('sales/', include('apps.sales.urls', namespace='sales')),
    path('expenses/', include('apps.expenses.urls', namespace='expenses')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    # path('notifications/', include('apps.notifications.urls', namespace='notifications')),
]

# Development davrida media fayllarni ko'rish uchun
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)