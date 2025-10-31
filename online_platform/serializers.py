from rest_framework import serializers
from .models import Product, NetworkUnit

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'model', 'release_date']


class NetworkUnitSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Product.objects.all(), required=False
    )
    debt = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    level = serializers.IntegerField(read_only=True)

    class Meta:
        model = NetworkUnit
        fields = [
            'id', 'name',
            'email', 'country', 'city', 'street', 'building',
            'products', 'supplier', 'debt', 'created_at', 'level'
        ]
        read_only_fields = ['debt', 'created_at', 'level']
