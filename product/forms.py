from django import forms
from django.forms.models import ModelChoiceIterator
from django.utils.encoding import smart_text
from django.utils.translation import pgettext_lazy
from .models import Product, AttributeChoiceValue, ProductVariant


class CachingModelChoiceIterator(ModelChoiceIterator):
    def __iter__(self):
        if self.field.empty_label is not None:
            yield ('', self.field.empty_label)
        for obj in self.queryset:
            yield self.choice(obj)


class CachingModelChoiceField(forms.ModelChoiceField):
    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices
        return CachingModelChoiceIterator(self)
    choices = property(_get_choices, forms.ChoiceField._set_choices)

class _AttributeBaseForm(object):
    attribute_fields = set()  # set to stote attribute field names (using for get_fieldset in ModelAdmin)

    def __init__(self, *args, **kwargs):
        """
        You have to set self.available_attrs 
        """
        super().__init__(*args, **kwargs)
        self.prepare_fields_for_attributes()
        
    def prepare_fields_for_attributes(self):
        # add dynamic fields to form for each attribute
        if getattr(self, 'available_attrs', None):
            for attribute in self.available_attrs:
                field_defaults = {
                    'label': attribute.name,
                    'required': False,
                    'initial': self.instance.get_attribute(attribute.pk)}
                if attribute.has_values():
                    field = CachingModelChoiceField(
                        queryset=attribute.values.all(), **field_defaults)
                else:
                    field = forms.CharField(**field_defaults)
                self.fields[attribute.get_formfield_name()] = field
                # add every attribute field name to the set to use it in ModelAdmin get_fieldset method
                # to override fieldset
                self.attribute_fields.add(attribute.get_formfield_name()) 

    def iter_attribute_fields(self):
        # iterate accross attribute fields to display them in template (if you need)
        if getattr(self, 'available_attrs', None):
            for attr in self.available_attrs:
                yield self[attr.get_formfield_name()]

    def save(self, commit=True):
        # get cleaned data for each attribute field, and create dict key-value pair
        # for attributes dict to pass it to product HStore attribute field
        attributes = {}
        if getattr(self, 'available_attrs', None):
            for attr in self.available_attrs:
                value = self.cleaned_data.pop(attr.get_formfield_name())
                if isinstance(value, AttributeChoiceValue):
                    attributes[smart_text(attr.pk)] = smart_text(value.pk)
                    # attributes[smart_text(attr.slug)] = smart_text(value.slug)
                else:
                    attributes[smart_text(attr.pk)] = value
        self.instance.attributes = attributes
        instance = super().save(commit=commit)
        # clear set with attributes fields names
        self.attribute_fields.clear()
        return instance


class ProductForm(_AttributeBaseForm, forms.ModelForm):
    attribute_fields = set()  # set to stote attribute field names (using for get_fieldset in ModelAdmin)

    class Meta:
        model = Product
        exclude = ['attributes']
        labels = {
            'is_published': pgettext_lazy('product form', 'Published'), 
            'is_featured': pgettext_lazy('product form', 'Feature this product on homepage')
        }

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

        # if product already has product class, get from it attributes for product    
        if self.instance.product_class_id:
            product_class = self.instance.product_class
            self.available_attrs = product_class.product_attributes.all().prefetch_related('values')
            # prepare form fields for product_class attributes
            _AttributeBaseForm.__init__(self, *args, **kwargs)


class VariantAttributeForm(_AttributeBaseForm, forms.ModelForm):
    attribute_fields = set()
    
    class Meta:
        model = ProductVariant
        exclude = ['attributes']

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)

        if self.instance.product_id:
            product_class = self.instance.product.product_class
            self.available_attrs = product_class.variant_attributes.all().prefetch_related('values')
            _AttributeBaseForm.__init__(self, *args, **kwargs)

    