from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated

from .models import Product, NetworkUnit
from .serializers import ProductSerializer, NetworkUnitSerializer
from .permissions import IsActiveStaff

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('id')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated & IsActiveStaff]


class NetworkUnitViewSet(viewsets.ModelViewSet):
    """
    CRUD для звена сети.
    - `debt` редактировать через API нельзя (read_only).
    - Фильтрация по стране: ?country=USA
    """
    queryset = NetworkUnit.objects.select_related('supplier').prefetch_related('products').order_by('id')
    serializer_class = NetworkUnitSerializer
    permission_classes = [IsAuthenticated & IsActiveStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['country']
