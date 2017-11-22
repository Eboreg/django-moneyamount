from django import template

register = template.Library()

@register.filter
def as_currency(amount, currency):
    """
    amount = MoneyAmount
    currency = string
    """
    return amount.convert_to(currency)
