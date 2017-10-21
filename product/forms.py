from __future__ import unicode_literals

import json

from django import forms
from django.utils.encoding import smart_text
from django.utils.translation import pgettext_lazy
from django_prices.templatetags.prices_i18n import gross
from .models import Product


class VariantChoiceField(forms.ModelChoiceField):
    discounts = None

    def label_from_instance(self, obj):
        variant_label = smart_text(obj)
        label = pgettext_lazy(
            'Variant choice field label',
            '%(variant_label)s - %(price)s') % {
                'variant_label': variant_label,
                'price': gross(obj.get_price(discounts=self.discounts))}
        return label


class ProductForm(forms.ModelForm):
    variant = VariantChoiceField(queryset=None)

    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, product, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.product = product
        variant_field = self.fields['variant']
        variant_field.queryset = self.product.variants
        variant_field.empty_label = None
        images_map = {variant.pk: [vi.image.image.url
                                   for vi in variant.variant_images.all()]
                      for variant in self.product.variants.all()}
        variant_field.widget.attrs['data-images'] = json.dumps(images_map)

    def get_variant(self, cleaned_data):
        return cleaned_data.get('variant')