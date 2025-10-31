from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from online_platform.views import ProductViewSet, NetworkUnitViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'units', NetworkUnitViewSet, basename='networkunit')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
