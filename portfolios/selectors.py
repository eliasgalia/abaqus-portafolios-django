"""Read operations and buy-and-hold calculations from ORM records, never Excel."""
from collections import defaultdict
from decimal import Decimal, localcontext
from .models import Portfolio, Position, Price


def portfolio_evolution(*, start, end, portfolio_id=None):
    portfolios = list(Portfolio.objects.filter(**({"pk": portfolio_id} if portfolio_id else {})).order_by("id"))
    if not portfolios:
        raise LookupError("No hay portafolios para la selección. Cargue primero datos.xlsx.")
    if any(start < p.initial_date for p in portfolios):
        raise ValueError("La fecha de inicio no puede ser anterior al inicio del portafolio.")
    positions = list(Position.objects.filter(portfolio__in=portfolios).select_related("asset").order_by("asset__name"))
    by_portfolio = defaultdict(list)
    for position in positions:
        by_portfolio[position.portfolio_id].append(position)
    asset_ids = {position.asset_id for position in positions}
    daily_prices = defaultdict(dict)
    for price in Price.objects.filter(asset_id__in=asset_ids, date__range=(start, end)).order_by("date", "asset_id"):
        daily_prices[price.date][price.asset_id] = price.value
    result = []
    with localcontext() as context:
        context.prec = 40
        for portfolio in portfolios:
            holdings = by_portfolio[portfolio.id]
            if not holdings:
                raise ValueError("Portafolio sin posiciones.")
            points = []
            for when, price_map in daily_prices.items():
                if any(p.asset_id not in price_map for p in holdings):
                    raise ValueError(f"Precios incompletos para {when}; no se rellenan ni ignoran activos.")
                amounts = [(p, p.quantity * price_map[p.asset_id]) for p in holdings]
                total = sum((amount for _, amount in amounts), Decimal(0))
                if total <= 0:
                    raise ValueError("No es posible calcular pesos con valor total cero.")
                points.append({
                    "date": when.isoformat(), "value": str(total.quantize(Decimal("0.000001"))),
                    "weights": {p.asset.name: str((amount / total).quantize(Decimal("0.000000000001"))) for p, amount in amounts},
                })
            result.append({"id": portfolio.id, "name": portfolio.name, "points": points})
    return {"start": start.isoformat(), "end": end.isoformat(), "currency": "USD", "strategy": "buy_and_hold", "portfolios": result}
