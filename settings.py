from django.conf import settings

BASE_CURRENCY = getattr(settings, "BASE_CURRENCY", "SEK")
CACHE_EXCHANGE = getattr(settings, "CACHE_EXCHANGE", True)
CACHE_EXCHANGE_DURATION = getattr(settings, "CACHE_EXCHANGE_DURATION", 2)
CURRENCIES = getattr(settings, "CURRENCIES", (
        ('SEK', 'SEK'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('INR', 'INR'),
    )
)
