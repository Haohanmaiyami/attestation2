from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

class Product(models.Model):
    name = models.CharField(max_length=200)
    model = models.CharField(max_length=200)
    release_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.model})"


class NetworkUnit(models.Model):
    """
    Как звено сети. завод / розничная сеть / ИП
    завод=0, вычисляем на лету
    """
    # Название
    name = models.CharField(max_length=255)

    # Контакты
    email = models.EmailField()
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=100)
    building = models.CharField(max_length=50)

    # Продукция
    products = models.ManyToManyField(Product, blank=True, related_name='network_units')

    # Иерархия
    supplier = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clients',
        help_text=_("Поставщик (предыдущий по иерархии объект сети)"),
    )

    # ДОлги
    debt = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Служебное
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Звено сети"
        verbose_name_plural = "Звенья сети"

    def __str__(self):
        return self.name

    @property
    def level(self) -> int:
        lvl, node = 0, self.supplier
        while node is not None:
            lvl += 1
            node = node.supplier
        return lvl

    def clean(self):
        if self.pk and self.supplier_id:
            node = self.supplier
            while node is not None:
                if node.pk == self.pk:
                    raise ValidationError(_("петля недопустима, циклическая ссылка в иерархии поставщиков"))
                node = node.supplier

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
