import re
from datetime import date
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Portfolio
from .selectors import portfolio_evolution


def parse_date(value):
    if not value or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Use fecha_inicio y fecha_fin con formato YYYY-MM-DD.")
    return date.fromisoformat(value)


@require_GET
def evolution_api(request):
    try:
        start, end = parse_date(request.GET.get("fecha_inicio")), parse_date(request.GET.get("fecha_fin"))
        if start > end:
            raise ValueError("fecha_inicio debe ser anterior o igual a fecha_fin.")
        raw = request.GET.get("portfolio_id")
        portfolio_id = int(raw) if raw else None
        if portfolio_id is not None and portfolio_id <= 0:
            raise ValueError("portfolio_id debe ser un entero positivo.")
        return JsonResponse(portfolio_evolution(start=start, end=end, portfolio_id=portfolio_id))
    except LookupError as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except (ValueError, OverflowError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_GET
def portfolio_list_api(request):
    return JsonResponse({"portfolios": list(Portfolio.objects.order_by("id").values("id", "name", "initial_date", "initial_value"))})


@require_GET
def initial_positions_api(request, portfolio_id):
    try:
        portfolio = Portfolio.objects.get(pk=portfolio_id)
    except Portfolio.DoesNotExist:
        return JsonResponse({"error": "Portafolio no encontrado."}, status=404)
    return JsonResponse({"portfolio": portfolio.name, "initial_date": portfolio.initial_date, "positions": [
        {"asset": p.asset.name, "initial_weight": str(p.initial_weight), "quantity": str(p.quantity)}
        for p in portfolio.positions.select_related("asset").order_by("asset__name")
    ]})
