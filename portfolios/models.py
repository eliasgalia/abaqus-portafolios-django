from django.db import models


class Asset(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Portfolio(models.Model):
    name = models.CharField(max_length=100, unique=True)
    initial_date = models.DateField()
    initial_value = models.DecimalField(max_digits=24, decimal_places=8)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(initial_value__gt=0), name="positive_initial_value")]


class Price(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT)
    date = models.DateField(db_index=True)
    value = models.DecimalField(max_digits=24, decimal_places=8)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["asset", "date"], name="unique_asset_date"),
            models.CheckConstraint(condition=models.Q(value__gt=0), name="positive_price"),
        ]


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="positions")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT)
    initial_weight = models.DecimalField(max_digits=16, decimal_places=12)
    quantity = models.DecimalField(max_digits=30, decimal_places=12)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "asset"], name="unique_portfolio_asset"),
            models.CheckConstraint(condition=models.Q(initial_weight__gte=0, initial_weight__lte=1), name="weight_between_zero_one"),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="nonnegative_quantity"),
        ]
