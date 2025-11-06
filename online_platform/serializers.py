from rest_framework import serializers
from .models import Product, NetworkUnit
from django.core.exceptions import ValidationError as DjangoValidationError

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

        # предвалидация, чтобы поймать цикл до save()
    def validate(self, attrs):
        supplier = attrs.get('supplier') or getattr(self.instance, 'supplier', None)
        instance = self.instance
        if instance and supplier:
            cur = supplier
            while cur is not None:
                if getattr(cur, 'pk', None) == instance.pk:
                    # вернём корректный 400 JSON
                    raise serializers.ValidationError({'supplier': 'Циклическая ссылка в иерархии недопустима.'})
                cur = cur.supplier
        return attrs

    # перехват DjangoValidationError → 400 JSON
    def create(self, validated_data):
        products = validated_data.pop('products', [])
        obj = NetworkUnit(**validated_data)
        try:
            obj.full_clean()  # вызовет model.clean(), где тоже проверка цикла
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict or e.messages)
        obj.save()
        if products:
            obj.products.set(products)
        return obj

    # для update
    def update(self, instance, validated_data):
        products = validated_data.pop('products', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        try:
            instance.full_clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict or e.messages)
        instance.save()
        if products is not None:
            instance.products.set(products)
        return instance
