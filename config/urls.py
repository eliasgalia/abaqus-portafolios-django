from django.urls import path
from portfolios.apis import evolution_api, initial_positions_api, portfolio_list_api
from portfolios.views import dashboard

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("api/portfolios/", portfolio_list_api, name="portfolio-list"),
    path("api/portfolios/<int:portfolio_id>/initial/", initial_positions_api, name="initial-positions"),
    path("api/evolution/", evolution_api, name="evolution"),
]
