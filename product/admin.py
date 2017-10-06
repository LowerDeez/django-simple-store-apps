from django.contrib import admin
from django import forms
from .models import *
from django.forms.models import ModelChoiceIterator
from django.utils.encoding import smart_text
from django.shortcuts import redirect
from django.core.urlresolvers import resolve
from django.utils.functional import curry


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


class VariantAttributeForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = []

    def __init__(self, *args, **kwargs):
        super(VariantAttributeForm, self).__init__(*args, **kwargs)
        attrs = self.instance.product.product_class.variant_attributes.all()
        self.available_attrs = attrs.prefetch_related('values')
        for attr in self.available_attrs:
            field_defaults = {
                'label': attr.name,
                'required': True,
                'initial': self.instance.get_attribute(attr.pk)}
            if attr.has_values():
                field = CachingModelChoiceField(
                    queryset=attr.values.all(), **field_defaults)
            else:
                field = forms.CharField(**field_defaults)
            self.fields[attr.get_formfield_name()] = field

    def save(self, commit=True):
        attributes = {}
        for attr in self.available_attrs:
            value = self.cleaned_data.pop(attr.get_formfield_name())
            if isinstance(value, AttributeChoiceValue):
                attributes[smart_text(attr.pk)] = smart_text(value.pk)
            else:
                attributes[smart_text(attr.pk)] = value
        self.instance.attributes = attributes
        return super(VariantAttributeForm, self).save(commit=commit)


class ProductVariantAdminInline(admin.TabularInline):
    extra = 0
    model = ProductVariant
    # form = VariantAttributeForm
    #
    # def get_parent_object_from_request(self, request):
    #     """
    #     Returns the parent object from the request or None.
    #
    #     Note that this only works for Inlines, because the `parent_model`
    #     is not available in the regular admin.ModelAdmin as an attribute.
    #     """
    #     resolved = resolve(request.path_info)
    #     if resolved.args:
    #         return self.parent_model.objects.get(pk=resolved.args[0])
    #     return None
    #
    # def get_formset(self, request, obj=None, **kwargs):
    #     initial = []
    #     if request.method == "GET":
    #         initial.append({
    #             'product': self.get_parent_object_from_request(request),
    #         })
    #     formset = super().get_formset(request, obj, **kwargs)
    #     formset.__init__ = curry(formset.__init__, initial=initial)
    #     return formset


class ProductImageAdminInline(admin.TabularInline):
    model = ProductImage


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        exclude = ['attributes']
        labels = {
            'is_published': pgettext_lazy('product form', 'Published'),
            'is_featured': pgettext_lazy(
                'product form', 'Feature this product on homepage')}

    def __init__(self, *args, **kwargs):
        self.product_attributes = []
        super(ProductForm, self).__init__(*args, **kwargs)

        if self.instance.product_class_id:
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
            value = self.cleaned_data.pop(attr.get_formfield_name())
            if isinstance(value, AttributeChoiceValue):
                attributes[smart_text(attr.pk)] = smart_text(value.pk)
            else:
                attributes[smart_text(attr.pk)] = value
            # attributes[attr.id] = attr.values.all()
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
    list_display = [f.name for f in Product._meta.fields]
    inlines = [ProductVariantAdminInline, ProductImageAdminInline]

    def get_form(self, request, obj=None, **kwargs):
        # Proper kwargs are form, fields, exclude, formfield_callback
        if not obj:  # obj is None, so this is an add page
            kwargs['fields'] = ['product_class', ]
            self.inlines = []
        else:
            self.inlines = [ProductVariantAdminInline, ProductImageAdminInline]
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.id:
            obj.price = '0.00'
            obj.save()
        return super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('/admin/product/product/{}/change'.format(obj.id))


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