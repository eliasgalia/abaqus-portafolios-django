"""Independent Excel arithmetic versus ORM/API output; also exports answers."""
import csv
import hashlib
import json
import os
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.test import Client
from openpyxl import load_workbook
from portfolios.models import Position

root = Path(__file__).resolve().parent
source = root / "data" / "datos.xlsx"
outputs = root / "outputs"
outputs.mkdir(exist_ok=True)
book = load_workbook(source, data_only=True, read_only=True)
weights = {
    row[1]: [Decimal(str(row[2])).quantize(Decimal("0.000000000001")), Decimal(str(row[3])).quantize(Decimal("0.000000000001"))]
    for row in book["weights"].iter_rows(min_row=2, values_only=True) if row[1] is not None
}
price_rows = iter(book["Precios"].iter_rows(values_only=True))
names = list(next(price_rows)[1:])
raw_prices = {row[0].date(): dict(zip(names, map(lambda v: Decimal(str(v)), row[1:]), strict=True)) for row in price_rows if row[0] is not None}
book.close()
response = Client().get("/api/evolution/", {"fecha_inicio": "2022-02-15", "fecha_fin": "2023-02-16"})
assert response.status_code == 200, response.content
data = response.json()
max_value_error = Decimal(0)
max_weight_error = Decimal(0)
with localcontext() as context:
    context.prec = 40
    for i, portfolio in enumerate(data["portfolios"]):
        assert len(portfolio["points"]) == len(raw_prices) == 367
        quantities = {name: pair[i] * Decimal("1000000000") / raw_prices[date(2022,2,15)][name] for name,pair in weights.items()}
        for point in portfolio["points"]:
            day = raw_prices[date.fromisoformat(point["date"])]
            amounts = {name: quantities[name] * day[name] for name in weights}
            total = sum(amounts.values())
            error = abs(Decimal(point["value"]) - total)
            max_value_error = max(max_value_error,error)
            assert error < Decimal("0.001"), (portfolio["name"],point["date"],error)
            assert abs(sum(map(Decimal, point["weights"].values())) - 1) < Decimal("0.00000000002")
            for name,amount in amounts.items():
                error = abs(Decimal(point["weights"][name])-amount/total)
                max_weight_error = max(max_weight_error,error)
                assert error < Decimal("0.000000000002")
with (outputs/"cantidades_iniciales.csv").open("w",newline="",encoding="utf-8-sig") as handle:
    writer = csv.writer(handle)
    writer.writerow(["portafolio","activo","peso_inicial","cantidad_inicial"])
    for p in Position.objects.select_related("asset","portfolio").order_by("portfolio__name","asset__name"):
        writer.writerow([p.portfolio.name,p.asset.name,p.initial_weight,p.quantity])
(outputs/"evolucion.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")
report = {"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"assets":17,"portfolios":2,"positions":34,"dates":367,"prices":6239,"validated_portfolio_days":734,"max_absolute_value_error_usd":str(max_value_error),"max_absolute_weight_error":str(max_weight_error),"summary":[{"portfolio":p["name"],"initial":p["points"][0]["value"],"final":p["points"][-1]["value"],"last_date":p["points"][-1]["date"]} for p in data["portfolios"]]}
(outputs/"validacion_datos_reales.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps(report,ensure_ascii=False,indent=2))
