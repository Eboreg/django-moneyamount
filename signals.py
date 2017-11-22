from django.db.models.signals import post_init
from django.dispatch import receiver

from .models import MoneyAmount, CurrencyExchangeRate


@receiver(post_init, sender=MoneyAmount)
def set_base_moneyamount_values(sender, instance, **kwargs):
    if instance.amount is not None:
        if not instance.currency:
            instance.currency = CurrencyExchangeRate.base_currency
        instance.base_amount, instance.base_exchange_rate = CurrencyExchangeRate.to_base_currency(instance.amount, instance.currency)
