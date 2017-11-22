import re
from datetime import timedelta
from decimal import Decimal
from numbers import Number

from django.db import models
from django.utils import timezone

from .fields import MoneyAmountField
from . import settings as cur_settings


class _ExchangeRateCacher(object):
    items = None
    recache_at = None


class CurrencyExchangeRate(models.Model):
    iso_code = models.CharField(max_length=6)
    name = models.CharField(max_length=64)
    symbol = models.CharField(max_length=6)
    exchange_rate = models.DecimalField(decimal_places=4, max_digits=10)
    decimal_mark = models.CharField(max_length=6, default=',', help_text="Character to separate decimal. For example ',' or '.'")
    thousand_mark = models.CharField(max_length=6, default=' ', help_text="Character to separate thousands. For example ' ' ',' or '.'")
    decimal_places = models.IntegerField(default=2, help_text="Number of decimals to show")
    remove_decimal_zero = models.BooleanField(default=True, help_text="Removes extra decimal zeros")
    active = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)

    @classmethod
    def base_currency(cls):
        """Returns the base currency of the system"""
        return cur_settings.BASE_CURRENCY

    @classmethod
    def get_exchange_rate(cls, currency):
        """Returns active exchange rate for the given currency"""
        return cls.get_exchange_rate_item(currency).exchange_rate

    @classmethod
    def get_exchange_rate_item(cls, currency):
        """Returns active exchange rate item for the given currency"""
        currency = currency.upper()
        if cur_settings.CACHE_EXCHANGE:
            if _ExchangeRateCacher.items is None:
                # init the cache
                _ExchangeRateCacher.items = {}
                if cur_settings.CACHE_EXCHANGE_DURATION > 0:
                    # to fetch data now
                    _ExchangeRateCacher.recache_at = timezone.now() + timedelta(minutes=-1)
            if currency not in _ExchangeRateCacher.items or (_ExchangeRateCacher.recache_at is not None and _ExchangeRateCacher.recache_at > timezone.now()):
                for item in cls.objects.filter(active=True):
                    _ExchangeRateCacher.items[item.iso_code] = item
                if cur_settings.CACHE_EXCHANGE_DURATION > 0:
                    _ExchangeRateCacher.recache_at = timezone.now() + timedelta(minutes=cur_settings.CACHE_EXCHANGE_DURATION)
            if currency in _ExchangeRateCacher.items:
                return _ExchangeRateCacher.items[currency]
        return cls.objects.get(iso_code=currency, active=True)

    @classmethod
    def convert(cls, amount, from_currency=None, to_currency=None):
        """
        Converts the amount to new currency, by default it converts to base currency
        """
        if amount == 0.0:
            return Decimal(0.0), 1
        base_currency = cls.base_currency()
        to_currency = (to_currency or base_currency).upper()
        from_currency = (from_currency or base_currency).upper()
        new_amount = amount
        exchange_rate = 1
        if to_currency == from_currency:
            return Decimal(new_amount), 1
        if from_currency != base_currency:
            exchange_rate = cls.get_exchange_rate(from_currency)
            new_amount = Decimal(new_amount) * Decimal(exchange_rate)
        if to_currency != base_currency:
            exchange_rate = cls.get_exchange_rate(to_currency)
            new_amount = Decimal(new_amount) / Decimal(exchange_rate)
        return Decimal(new_amount), exchange_rate

    @classmethod
    def to_base_currency(cls, amount, currency):
        """
        Convert the given amount to base currency
        """
        return cls.convert(amount, currency)

    @classmethod
    def from_base_currency(cls, amount, currency):
        """
        Create new amount for the given currency from base currency
        """
        return cls.convert(amount, cls.base_currency(), currency)

    @classmethod
    def format(cls, amount, currency):
        """
        Returns formated price string based on currency format settings
        """
        exch = cls.get_exchange_rate_item(currency)
        parts = divmod(amount, 1)
        parts = int(parts[0]), int(parts[1] * pow(10, exch.decimal_places))
        val = str(parts[0])
        if exch.thousand_mark:
            val = exch.thousand_mark.join(re.findall('((?:\d+\.)?\d{1,3})', val[::-1]))[::-1]
        if exch.decimal_places:
            dec = str(parts[1])
            if exch.remove_decimal_zero:
                dec = dec.rstrip('0')
            elif len(dec) < exch.decimal_places:
                dec += '0' * (exch.decimal_places-len(dec))
            if dec:
                val = val + exch.decimal_mark + dec
        return val


class MoneyAmount(models.Model):
    """
    Model for storing data about monetary amounts and their currencies and exchange rates.
    To be used as OneToOneField relation in models that store monetary amounts.
    """
    amount = models.DecimalField(default=0.0, max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, choices=cur_settings.CURRENCIES, default=CurrencyExchangeRate.base_currency,
        help_text="Stored as ISO codes (SEK, EUR, etc) in the DB")
    base_amount = models.DecimalField(default=0.0, editable=False, decimal_places=2, max_digits=10, help_text="Amount in system base currency")
    base_currency = models.CharField(default=CurrencyExchangeRate.base_currency, editable=False, max_length=6, help_text="System base currency")
    base_exchange_rate = models.DecimalField(default=1, editable=False, decimal_places=4, max_digits=10)

    def __cmp__(self, other):
        if isinstance(other, MoneyAmount):
            base_currency = CurrencyExchangeRate.base_currency()
            diff = self.amount_as(base_currency) - other.amount_as(base_currency)
        elif isinstance(other, Number):
            diff = self.amount - Decimal(other)
        else:
            return NotImplemented
        if diff < 0:
            return -1
        elif diff > 0:
            return 1
        else:
            return 0

    def __eq__(self, other):
        if isinstance(other, MoneyAmount):
            base_currency = CurrencyExchangeRate.base_currency()
            return self.amount_as(base_currency) == other.amount_as(base_currency)
        elif isinstance(other, Number):
            return self.amount == Decimal(other)
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, MoneyAmount):
            base_currency = CurrencyExchangeRate.base_currency()
            return self.amount_as(base_currency) != other.amount_as(base_currency)
        elif isinstance(other, Number):
            return self.amount != Decimal(other)
        else:
            return NotImplemented

    def __add__(self, other):
        if isinstance(other, MoneyAmount):
            return MoneyAmount(amount=self.amount + other.amount_as(self.currency), currency=self.currency)
        elif isinstance(other, Number):
            return MoneyAmount(amount=self.amount + Decimal(other), currency=self.currency)
        else:
            return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, MoneyAmount):
            return MoneyAmount(amount=self.amount - other.amount_as(self.currency), currency=self.currency)
        elif isinstance(other, Number):
            return MoneyAmount(amount=self.amount - Decimal(other), currency=self.currency)
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, MoneyAmount):
            return MoneyAmount(amount=other.amount_as(self.currency) - self.amount, currency=self.currency)
        elif isinstance(other, Number):
            return MoneyAmount(amount=Decimal(other) - self.amount, currency=self.currency)
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, MoneyAmount):
            return MoneyAmount(amount=self.amount * other.amount_as(self.currency), currency=self.currency)
        elif isinstance(other, Number):
            return MoneyAmount(amount=self.amount * Decimal(other), currency=self.currency)
        else:
            return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __unicode__(self):
        return " ".join([str(self.amount), self.currency, ])

    def __float__(self):
        return float(self.amount)

    def save(self, *args, **kwargs):
        self.base_amount, self.base_exchange_rate = CurrencyExchangeRate.to_base_currency(self.amount, self.currency)
        super(MoneyAmount, self).save(*args, ** kwargs)

    def convert_to(self, currency):
        currency = currency.upper()
        return MoneyAmount(
            amount=self.amount_as(currency),
            currency=currency
        )

    def amount_as(self, currency):
        currency = currency.upper()
        if currency == self.base_currency:
            return self.base_amount
        elif currency == self.currency:
            return self.amount
        return CurrencyExchangeRate.convert(self.base_amount, self.base_currency, currency)[0]

    @property
    def amount_as_base(self):
        return self.amount_as(CurrencyExchangeRate.base_currency())
