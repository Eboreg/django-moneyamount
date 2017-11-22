from django import forms
from . import settings as cur_settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


class MoneyAmountWidget(forms.widgets.MultiWidget):
    def __init__(self, attrs=None):
        widgets = (
            forms.widgets.HiddenInput(attrs=attrs),
            forms.widgets.NumberInput(attrs=attrs),
            forms.widgets.Select(attrs=attrs, choices=cur_settings.CURRENCIES)
        )
        super(MoneyAmountWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        from .models import MoneyAmount, CurrencyExchangeRate
        try:
            moneyamount = MoneyAmount.objects.get(pk=value)
            return [ value, moneyamount.amount, moneyamount.currency ]
        except:
            return [ None, str(0), CurrencyExchangeRate.base_currency ]


class MoneyAmountFormField(forms.ModelChoiceField):
    # Most logic stolen from https://docs.djangoproject.com/en/1.11/_modules/django/forms/fields/#MultiValueField
    default_error_messages = {
        'required': _('This field is required.'),
        'invalid': _('Enter valid amount and currency.'),
        'incomplete': _('Enter a complete value.'),
    }
    widget = MoneyAmountWidget

    def __init__(self, queryset, *args, **kwargs):
        from .models import CurrencyExchangeRate
        self.fields = (
            forms.IntegerField(required=False),
            forms.DecimalField(),
            forms.ChoiceField(choices=cur_settings.CURRENCIES, initial=CurrencyExchangeRate.base_currency),
        )
        super(MoneyAmountFormField, self).__init__(queryset, *args, **kwargs)

    def validate(self, value):
        pass

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        if initial is None:
            initial = ['' for x in range(0, len(data))]
        else:
            if not isinstance(initial, list):
                initial = self.widget.widget.decompress(initial)
        for field, initial, data in zip(self.fields, initial, data):
            try:
                initial = field.to_python(initial)
            except ValidationError:
                return True
            if field.has_changed(initial, data):
                return True
        return False


    def clean(self, value):
        """
        Validates every value in the given list. A value is validated against
        the corresponding Field in self.fields.

        For example, if this MultiValueField was instantiated with
        fields=(DateField(), TimeField()), clean() would call
        DateField.clean(value[0]) and TimeField.clean(value[1]).
        """
        clean_data = []
        errors = []
        if not value or isinstance(value, (list, tuple)):
            if not value or not [v for v in value if v not in self.empty_values]:
                if self.required:
                    raise ValidationError(self.error_messages['required'], code='required')
                else:
                    return self.compress([])
        else:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        for i, field in enumerate(self.fields):
            try:
                field_value = value[i]
            except IndexError:
                field_value = None
            if field_value in self.empty_values:
                if field.required:
                    # Otherwise, add an 'incomplete' error to the list of
                    # collected errors and skip field cleaning, if a required
                    # field is empty.
                    if self.error_messages['incomplete'] not in errors:
                        errors.append(self.error_messages['incomplete'])
                    continue
            try:
                clean_data.append(field.clean(field_value))
            except ValidationError as e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter. Skip duplicates.
                errors.extend(m for m in e.error_list if m not in errors)
        if errors:
            raise ValidationError(errors)
        out = self.compress(clean_data)
        self.validate(out)
        self.run_validators(out)
        return out

    def compress(self, data_list):
        from .models import MoneyAmount
        if data_list:
            if data_list[0] in self.empty_values:
                moneyamount = MoneyAmount()
            else:
                moneyamount = MoneyAmount.objects.get(pk=data_list[0])
            moneyamount.amount = data_list[1]
            moneyamount.currency = data_list[2]
            moneyamount.save()
            return moneyamount
        return None
