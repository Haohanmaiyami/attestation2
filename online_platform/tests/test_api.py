from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from online_platform.models import Product, NetworkUnit


User = get_user_model()


class BaseAPITest(APITestCase):
    def setUp(self):
        # users
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True, is_active=True
        )
        self.user = User.objects.create_user(
            username="user", password="pass", is_staff=False, is_active=True
        )

        # products
        self.tv = Product.objects.create(name="Бум-ТВ 3000", model="BOOM-TV3000", release_date="2024-01-15")
        self.phone = Product.objects.create(name="Космофон X", model="COSMO-X", release_date="2024-03-10")
        self.laptop = Product.objects.create(name="ТурбоТивка", model="TURBO-1", release_date="2023-11-20")
        self.vac = Product.objects.create(name="Ураган 9000", model="VAC-9000", release_date="2022-07-01")
        self.fridge = Product.objects.create(name="Ледяной Куб", model="ICE-CUBE", release_date="2021-05-05")

        # hierarchy: factories -> retail -> IP
        self.factory_a = NetworkUnit.objects.create(
            name="ЭлектроПапа", email="a@fab.ru", country="USA", city="NYC", street="Main", building="1"
        )
        self.factory_b = NetworkUnit.objects.create(
            name="ПандаТех", email="b@fab.cn", country="China", city="Shenzhen", street="Tech", building="2"
        )
        self.retail_mix = NetworkUnit.objects.create(
            name="РозеткаMix", email="mix@retail.us", country="USA", city="NYC",
            street="Broadway", building="10", supplier=self.factory_a
        )
        self.gadgetograd = NetworkUnit.objects.create(
            name="Гаджетоград", email="gad@retail.us", country="USA", city="Los Angeles",
            street="Sunset", building="77", supplier=self.factory_b
        )
        self.ip_ivan = NetworkUnit.objects.create(
            name="Иван Паяльник", email="ivan@ip.us", country="USA", city="Brooklyn",
            street="Kings Hwy", building="125", supplier=self.retail_mix
        )
        self.ip_mrs = NetworkUnit.objects.create(
            name="Миссис Отвёртка", email="mrs@ip.cn", country="China", city="Shenzhen",
            street="Market", building="5", supplier=self.gadgetograd
        )

        # bind products for variety
        self.retail_mix.products.set([self.tv, self.phone])
        self.ip_ivan.products.set([self.laptop])
        self.gadgetograd.products.set([self.vac, self.fridge])


class TestAuthAndPermissions(BaseAPITest):
    def test_auth_required(self):
        resp = self.client.get("/api/units/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Authentication credentials were not provided", str(resp.data))

    def test_only_staff_allowed(self):
        # non-staff -> 403
        self.client.force_authenticate(self.user)
        resp = self.client.get("/api/units/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # staff -> 200
        self.client.force_authenticate(self.staff)
        resp = self.client.get("/api/units/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class TestProductsAPI(BaseAPITest):
    def test_product_crud(self):
        self.client.force_authenticate(self.staff)

        # create
        resp = self.client.post(
            "/api/products/",
            {"name": "ХолодОК", "model": "ICE-OK", "release_date": "2024-09-09"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        pid = resp.data["id"]

        # list
        resp = self.client.get("/api/products/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(any(p["id"] == pid for p in resp.data))

        # patch
        resp = self.client.patch(f"/api/products/{pid}/", {"name": "ХолодОК Pro"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "ХолодОК Pro")


class TestNetworkUnitsAPI(BaseAPITest):
    def test_filter_by_country(self):
        self.client.force_authenticate(self.staff)
        resp = self.client.get("/api/units/?country=USA")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(all(u["country"] == "USA" for u in resp.data))

    def test_readonly_debt(self):
        self.client.force_authenticate(self.staff)

        # set some debt directly (как будто появилась задолженность)
        self.ip_ivan.debt = Decimal("123.45")
        self.ip_ivan.save()

        # попытка изменить через API и параллельно изменим name
        resp = self.client.patch(
            f"/api/units/{self.ip_ivan.id}/",
            {"debt": "9999.99", "name": "Иван-профи"},
            format="json",
        )
        # update проходит, но debt должен остаться прежним
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_202_ACCEPTED))
        self.ip_ivan.refresh_from_db()
        self.assertEqual(self.ip_ivan.name, "Иван-профи")
        self.assertEqual(self.ip_ivan.debt, Decimal("123.45"))

    def test_level_calculation_in_api(self):
        self.client.force_authenticate(self.staff)

        # factory level 0
        r = self.client.get(f"/api/units/{self.factory_a.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["level"], 0)

        # retail level 1
        r = self.client.get(f"/api/units/{self.retail_mix.id}/")
        self.assertEqual(r.data["level"], 1)

        # ip level 2
        r = self.client.get(f"/api/units/{self.ip_ivan.id}/")
        self.assertEqual(r.data["level"], 2)

    def test_assign_products_to_unit(self):
        self.client.force_authenticate(self.staff)
        r = self.client.patch(
            f"/api/units/{self.gadgetograd.id}/",
            {"products": [self.tv.id, self.phone.id, self.vac.id]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        r = self.client.get(f"/api/units/{self.gadgetograd.id}/")
        self.assertCountEqual(r.data["products"], [self.tv.id, self.phone.id, self.vac.id])

    def test_cycle_is_blocked_with_400(self):
        """Пытаемся сделать корневой завод потомком своего потомка -> 400."""
        self.client.force_authenticate(self.staff)

        # Убедимся в текущей цепочке:  self.ip_ivan -> self.retail_mix -> self.factory_a
        self.assertEqual(self.ip_ivan.supplier_id, self.retail_mix.id)
        self.assertEqual(self.retail_mix.supplier_id, self.factory_a.id)

        # Пытаемся замкнуть: factory_a.supplier = ip_ivan  => цикл
        resp = self.client.patch(
            f"/api/units/{self.factory_a.id}/",
            {"supplier": self.ip_ivan.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Циклическая", str(resp.data))
