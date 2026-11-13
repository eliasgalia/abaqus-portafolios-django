"""Write operations: validate the complete workbook before an atomic import."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

from django.db import transaction
from openpyxl import load_workbook

from .models import Asset, Portfolio, Position, Price

INITIAL_DATE = date(2022, 2, 15)
INITIAL_VALUE = Decimal("1000000000")


def number(value, label):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label}: falta un número válido.")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{label}: número inválido.") from exc
    if not result.is_finite():
        raise ValueError(f"{label}: valor no finito.")
    return result


def excel_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError("Fecha de Excel inválida: se requiere una celda de fecha.")


def parse_workbook(path):
    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        sheets = {name.casefold(): workbook[name] for name in workbook.sheetnames}
        if not {"weights", "precios"} <= sheets.keys():
            raise ValueError("Se requieren las hojas weights y Precios.")
        rows = list(sheets["weights"].iter_rows(values_only=True))
        if tuple(str(v).strip().casefold() for v in rows[0][:4]) != ("fecha", "activos", "portafolio 1", "portafolio 2"):
            raise ValueError("Cabecera de weights no reconocida.")
        weights = {}
        for row in rows[1:]:
            if all(v is None for v in row):
                continue  # Excel contains formatted but empty rows.
            when, name, w1, w2 = row[:4]
            if excel_date(when) != INITIAL_DATE or not isinstance(name, str) or not name.strip():
                raise ValueError("Fecha inicial o nombre de activo inválido en weights.")
            name = name.strip()
            if name in weights:
                raise ValueError(f"Activo repetido: {name}.")
            pair = tuple(number(w, name).quantize(Decimal("0.000000000001")) for w in (w1, w2))
            if any(w < 0 or w > 1 for w in pair):
                raise ValueError("Los pesos deben estar entre 0 y 1.")
            weights[name] = pair
        if len(weights) != 17:
            raise ValueError("El enunciado requiere exactamente 17 activos.")
        if any(sum(pair[i] for pair in weights.values()) != 1 for i in (0, 1)):
            raise ValueError("Los pesos iniciales de cada portafolio deben sumar 1.")
        price_rows = iter(sheets["precios"].iter_rows(values_only=True))
        header = next(price_rows)
        if str(header[0]).strip().casefold() != "dates":
            raise ValueError("Cabecera de fechas no reconocida.")
        assets = [str(v).strip() for v in header[1:]]
        if len(assets) != 17 or len(set(assets)) != 17 or set(assets) != set(weights):
            raise ValueError("Los nombres de activos de ambas hojas deben coincidir, sin duplicados.")
        prices = {}
        for row in price_rows:
            if all(v is None for v in row):
                continue
            when = excel_date(row[0])
            if when < INITIAL_DATE or when in prices:
                raise ValueError("Fecha de precios repetida o anterior al inicio.")
            values = [number(v, f"{when}/{name}") for name, v in zip(assets, row[1:], strict=True)]
            if any(v <= 0 for v in values):
                raise ValueError("Todos los precios deben ser positivos.")
            if any(v != v.quantize(Decimal("0.00000001")) for v in values):
                raise ValueError("Un precio supera la precisión de 8 decimales admitida.")
            prices[when] = dict(zip(assets, values, strict=True))
        if INITIAL_DATE not in prices:
            raise ValueError("Faltan precios en la fecha inicial.")
        return weights, prices
    finally:
        workbook.close()


def import_workbook(*, path):
    weights, prices = parse_workbook(path)
    with transaction.atomic(), localcontext() as context:
        context.prec = 40
        assets = {name: Asset.objects.get_or_create(name=name)[0] for name in weights}
        # Replace only prices in the imported universe to avoid stale dates on reimport.
        Price.objects.filter(asset__in=assets.values()).delete()
        Price.objects.bulk_create([
            Price(asset=assets[name], date=when, value=value)
            for when, daily in prices.items() for name, value in daily.items()
        ], batch_size=250)
        for i in (0, 1):
            portfolio, _ = Portfolio.objects.update_or_create(
                name=f"Portafolio {i + 1}",
                defaults={"initial_date": INITIAL_DATE, "initial_value": INITIAL_VALUE},
            )
            portfolio.positions.exclude(asset__in=assets.values()).delete()
            for name, pair in weights.items():
                quantity = (pair[i] * INITIAL_VALUE / prices[INITIAL_DATE][name]).quantize(Decimal("0.000000000001"))
                Position.objects.update_or_create(portfolio=portfolio, asset=assets[name], defaults={"initial_weight": pair[i], "quantity": quantity})
    return {"assets": len(assets), "portfolios": 2, "positions": 34, "price_dates": len(prices), "prices": len(prices) * len(assets)}
