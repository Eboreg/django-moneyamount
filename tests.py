from decimal import Decimal

from django.test import TestCase

from .models import CurrencyExchangeRate

class CurrencyExchangeRateTestCase(TestCase):
    def test_base_currency_is_valid(self):
        """ Tests so settings.BASE_CURRENCY is set, and is one of the valid currencies """
        base_currency = CurrencyExchangeRate.base_currency()
        obj = CurrencyExchangeRate.objects.get(iso_code=base_currency)
        self.assertIsInstance(obj, CurrencyExchangeRate)

    def test_base_currency_is_sek(self):
        """ Base currency should be SEK. Change test if this is no longer the case. """
        base_currency = CurrencyExchangeRate.base_currency()
        self.assertEqual(base_currency, "SEK")

    def test_get_exchange_rate_item(self):
        obj = CurrencyExchangeRate.get_exchange_rate_item("eur")
        self.assertIsInstance(obj, CurrencyExchangeRate)

    def test_get_exchange_rate(self):
        rate = CurrencyExchangeRate.get_exchange_rate("eur")
        self.assertIsInstance(rate, Decimal)

    def test_convert_sek_to_sek(self):
        new_amount, exchange_rate = CurrencyExchangeRate.convert(1.0)
        self.assertEqual(new_amount, 1.0)
        self.assertEqual(exchange_rate, 1)

    def test_convert_eur_to_usd(self):
        """ Try converting 10 EUR to USD """
        amount = Decimal(10)
        eur_rate = CurrencyExchangeRate.get_exchange_rate("eur")
        usd_rate = CurrencyExchangeRate.get_exchange_rate("usd")
        expected_amount = (amount * Decimal(eur_rate)) / Decimal(usd_rate)
        new_amount, exchange_rate = CurrencyExchangeRate.convert(10.0, from_currency="eur", to_currency="usd")
        self.assertEqual(new_amount, expected_amount)

    def test_to_base_currency(self):
        """ Test the class method to_base_currency() by converting EUR to SEK """
        amount = Decimal(10)
        eur_rate = CurrencyExchangeRate.get_exchange_rate("eur")
        expected_amount = Decimal(eur_rate) * amount
        new_amount, exchange_rate = CurrencyExchangeRate.to_base_currency(amount, "eur")
        self.assertEqual(expected_amount, new_amount)

    def test_from_base_currency(self):
        """ Test the class method from_base_currency() by converting SEK to EUR """
        amount = Decimal(10)
        eur_rate = CurrencyExchangeRate.get_exchange_rate("eur")
        expected_amount = amount / Decimal(eur_rate)
        new_amount, exchange_rate = CurrencyExchangeRate.from_base_currency(amount, "eur")
        self.assertEqual(expected_amount, new_amount)

    def test_format(self):
        """ Test for corrent formatting of amount """
        amount = Decimal(12345.678)
        usd_format = CurrencyExchangeRate.format(amount, "USD")
        sek_format = CurrencyExchangeRate.format(amount, "SEK")
        self.assertEqual(usd_format, "12,345.68")
        self.assertEqual(sek_format, "12 345")
