from __future__ import unicode_literals

from django.apps import AppConfig

class MoneyAmountConfig(AppConfig):
    name = 'moneyamount'

    def ready(self):
        from . import signals
        super(MoneyAmountConfig, self).ready()
        