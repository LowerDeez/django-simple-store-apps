from django.contrib import admin
from django import forms
from .models import *
from django.forms.models import ModelChoiceIterator
from django.utils.encoding import smart_text


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


class ProductVariantAdminInline(admin.TabularInline):
    model = ProductVariant


class ProductImageAdminInline(admin.TabularInline):
    model = ProductImage


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        exclude = ['product_class']
        labels = {
            'is_published': pgettext_lazy('product form', 'Published'),
            'is_featured': pgettext_lazy(
                'product form', 'Feature this product on homepage')}

    def __init__(self, *args, **kwargs):
        self.product_attributes = []
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['categories'].widget.attrs['data-placeholder'] = (
            pgettext_lazy('Product form placeholder', 'Search'))
        self.instance.product_class = ProductClass.objects.all().first()
        product_class = self.instance.product_class
        self.product_attributes = product_class.product_attributes.all()
        self.product_attributes = self.product_attributes.prefetch_related(
            'values')
        self.prepare_fields_for_attributes()

    def prepare_fields_for_attributes(self):
        for attribute in self.product_attributes:
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

    def iter_attribute_fields(self):
        for attr in self.product_attributes:
            yield self[attr.get_formfield_name()]

    def save(self, commit=True):
        attributes = {}
        for attr in self.product_attributes:
            print(attr.id)
            print(attr.values.all())
            print(attr.get_formfield_name())
            # value = self.cleaned_data.pop(attr.get_formfield_name())
            # print(value)
            # if isinstance(value, AttributeChoiceValue):
            #     attributes[smart_text(attr.pk)] = smart_text(value.pk)
            # else:
            #     attributes[smart_text(attr.pk)] = value
            attributes[attr.id] = attr.values.all()
        print(attributes)
        self.instance.attributes = attributes
        instance = super(ProductForm, self).save(commit=commit)
        return instance


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = ('product_class', 'attributes', 'name', 'price', 'available_on', 'description')
    inlines = [ProductVariantAdminInline, ProductImageAdminInline]


admin.site.register(StockLocation)


class StockAdminInline(admin.TabularInline):
    model = Stock


class VariantImageAdminInline(admin.TabularInline):
    model = VariantImage


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    inlines = [StockAdminInline, VariantImageAdminInline]


@admin.register(ProductClass)
class ProductClassAdmin(admin.ModelAdmin):
    list_display = ('name', )


class AttributeChoiceValueAdminInline(admin.TabularInline):
    model = AttributeChoiceValue


@admin.register(ProductAttribute)
class ProductAttribute(admin.ModelAdmin):
     inlines = [AttributeChoiceValueAdminInline]