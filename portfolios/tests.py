from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase
from openpyxl import Workbook, load_workbook
from .models import Asset, Portfolio, Position, Price
from .selectors import portfolio_evolution
from .services import import_workbook, parse_workbook


class PortfolioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.temp = TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "fixture.xlsx"
        book = Workbook(); weights = book.active; weights.title = "weights"
        weights.append(["Fecha", "activos", "portafolio 1", "portafolio 2"])
        for i in range(17):
            weights.append([datetime(2022, 2, 15), f"A{i:02}", .5 if i < 2 else 0, 1 if i == 0 else 0])
        prices = book.create_sheet("Precios")
        # Deliberately reverse columns, so positional joins would fail.
        names = [f"A{i:02}" for i in reversed(range(17))]
        prices.append(["Dates", *names])
        prices.append([datetime(2022, 2, 15), *[10 if n == "A00" else 20 for n in names]])
        prices.append([datetime(2022, 2, 16), *[20 for _ in names]])
        book.save(cls.path)
        import_workbook(path=cls.path)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.temp.cleanup()

    def test_buy_and_hold_and_weights_drift(self):
        data = portfolio_evolution(start=date(2022, 2, 15), end=date(2022, 2, 16))
        first, second = data["portfolios"]
        self.assertEqual(Decimal(first["points"][0]["value"]), Decimal("1000000000"))
        self.assertEqual(Decimal(first["points"][1]["value"]), Decimal("1500000000"))
        self.assertEqual(Decimal(second["points"][1]["value"]), Decimal("2000000000"))
        self.assertAlmostEqual(Decimal(first["points"][1]["weights"]["A00"]), Decimal(2)/3, places=11)
        self.assertEqual(Position.objects.get(portfolio__name="Portafolio 1", asset__name="A00").quantity, Decimal("50000000"))

    def test_queries_do_not_grow_per_day_or_asset(self):
        with self.assertNumQueries(3):
            portfolio_evolution(start=date(2022, 2, 15), end=date(2022, 2, 16))

    def test_reimport_does_not_duplicate(self):
        import_workbook(path=self.path)
        self.assertEqual((Asset.objects.count(), Portfolio.objects.count(), Position.objects.count(), Price.objects.count()), (17, 2, 34, 34))

    def test_import_rolls_back_if_write_fails(self):
        before = list(Price.objects.order_by("pk").values_list("pk", "value"))
        with patch("portfolios.services.Position.objects.update_or_create", side_effect=RuntimeError("interrupted")):
            with self.assertRaises(RuntimeError):
                import_workbook(path=self.path)
        self.assertEqual(before, list(Price.objects.order_by("pk").values_list("pk", "value")))

    def mutate_workbook(self, mutation):
        book = load_workbook(self.path); mutation(book)
        altered = Path(self.temp.name) / "invalid.xlsx"; book.save(altered); book.close()
        return altered

    def test_rejects_missing_price_without_changing_database(self):
        altered = self.mutate_workbook(lambda b: setattr(b["Precios"]["B3"], "value", None))
        with self.assertRaises(ValueError): import_workbook(path=altered)
        self.assertEqual(Price.objects.count(), 34)

    def test_rejects_invalid_weight_sum(self):
        altered = self.mutate_workbook(lambda b: setattr(b["weights"]["C2"], "value", .4))
        with self.assertRaisesRegex(ValueError, "sumar 1"): parse_workbook(altered)

    def test_rejects_duplicate_date(self):
        altered = self.mutate_workbook(lambda b: setattr(b["Precios"]["A3"], "value", datetime(2022,2,15)))
        with self.assertRaisesRegex(ValueError, "repetida"): parse_workbook(altered)

    def test_rejects_nonpositive_price(self):
        altered = self.mutate_workbook(lambda b: setattr(b["Precios"]["B3"], "value", 0))
        with self.assertRaisesRegex(ValueError, "positivos"): parse_workbook(altered)

    def test_api_date_validation(self):
        for params in ({}, {"fecha_inicio":"bad","fecha_fin":"2022-02-16"}, {"fecha_inicio":"2022-02-30","fecha_fin":"2022-03-01"}, {"fecha_inicio":"2022-02-16","fecha_fin":"2022-02-15"}, {"fecha_inicio":"2021-02-15","fecha_fin":"2022-02-16"}, {"fecha_inicio":"2022-02-15","fecha_fin":"2022-02-16","portfolio_id":"0"}):
            with self.subTest(params=params): self.assertEqual(self.client.get("/api/evolution/",params).status_code,400)

    def test_api_filter_and_inclusive_endpoints(self):
        p = Portfolio.objects.get(name="Portafolio 1")
        response = self.client.get("/api/evolution/",{"fecha_inicio":"2022-02-16","fecha_fin":"2022-02-16","portfolio_id":p.id})
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()["portfolios"]),1)
        self.assertEqual(len(response.json()["portfolios"][0]["points"]),1)

    def test_empty_range_is_not_zero_value(self):
        data=portfolio_evolution(start=date(2023,1,1),end=date(2023,1,2))
        self.assertEqual(data["portfolios"][0]["points"],[])

    def test_missing_portfolio_404(self):
        self.assertEqual(self.client.get("/api/evolution/",{"fecha_inicio":"2022-02-15","fecha_fin":"2022-02-16","portfolio_id":999}).status_code,404)
        self.assertEqual(self.client.get("/api/portfolios/999/initial/").status_code,404)

    def test_incomplete_day_is_error_not_silently_partial(self):
        Price.objects.filter(asset__name="A00",date=date(2022,2,16)).delete()
        with self.assertRaisesRegex(ValueError,"incompletos"):
            portfolio_evolution(start=date(2022,2,15),end=date(2022,2,16))

    def test_dashboard_and_read_only_api(self):
        self.assertContains(self.client.get("/"),"Evolución de portafolios")
        self.assertEqual(len(self.client.get("/api/portfolios/").json()["portfolios"]),2)
        p=Portfolio.objects.first()
        self.assertEqual(len(self.client.get(f"/api/portfolios/{p.id}/initial/").json()["positions"]),17)
        self.assertEqual(self.client.post("/api/evolution/").status_code,405)
