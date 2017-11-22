from django.db.models import CASCADE
from django.db.models.fields.related import ForwardOneToOneDescriptor
from django.db.models import OneToOneField

from .forms import MoneyAmountFormField

class MoneyAmountDescriptor(ForwardOneToOneDescriptor):
    """
    Modified descriptor which, in case the remote MoneyAmount field does not
    exist on attempted access, will create a new one with default values.
    """
    def __get__(self, instance, cls=None):
        """
        instance = the Model object that has the MoneyAmountField (e.g. a Lead object)
        self.field = commerce.fields.MoneyAmountField object
        self.field.name = name of the MoneyAmountField field (e.g. 'original_price')
        self.field.remote_field.model = MoneyAmount object
        """
        try:
            return super(MoneyAmountDescriptor, self).__get__(instance, cls)
        except self.RelatedObjectDoesNotExist:
            # Create new MoneyField:
            rel_obj = self.field.remote_field.model()
            # Object has to be saved BEFORE the relation is made:
            rel_obj.save()
            # Make the relation to it:
            super(MoneyAmountDescriptor, self).__set__(instance, rel_obj)
            return super(MoneyAmountDescriptor, self).__get__(instance, cls)

    def __set__(self, instance, value):
        from .models import MoneyAmount
        # If value is not a MoneyAmount object, assume it's a decimal amount
        # and create a new MoneyAmount object
        # Also delete the old related MoneyAmount object, if there is one
        if not isinstance(value, MoneyAmount):
            if value is not None:
                value = MoneyAmount(amount=value)
                value.save()
            try:
                old_obj = getattr(instance, self.field.name)
                old_obj.delete()
            except:
                pass
        super(MoneyAmountDescriptor, self).__set__(instance, value)


class MoneyAmountField(OneToOneField):
    """
    Modified OneToOneField for MoneyAmount relations. Will automatically create
    a new MoneyAmount object if there is none.

    Intended usage:
    price = commerce.fields.MoneyAmoundField()
    """
    forward_related_accessor_class = MoneyAmountDescriptor

    def __init__(self, to=None, on_delete=CASCADE, to_field=None, **kwargs):
        if not hasattr(kwargs, 'related_name'):
            kwargs['related_name'] = "+"
        super(MoneyAmountField, self).__init__('commerce.MoneyAmount', on_delete, to_field, **kwargs)

    def formfield(self, **kwargs):
        defaults = { 'form_class': MoneyAmountFormField }
        defaults.update(kwargs)
        return super(MoneyAmountField, self).formfield(**defaults)
