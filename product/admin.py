from django.contrib import admin
from django.shortcuts import redirect
from django.urls import resolve
from .models import *
from .admin_forms import ProductAdminForm, VariantAttributeAdminForm


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


# class ProductVariantAdminInline(admin.TabularInline):
#     extra = 0
#     model = ProductVariant
#     fields = ('sku', 'name', 'price_override')


class ProductImageAdminInline(admin.TabularInline):
    model = ProductImage


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = [f.name for f in Product._meta.fields]
    inlines = [ProductImageAdminInline]

    def get_form(self, request, obj=None, **kwargs):
        # Proper kwargs are form, fields, exclude, formfield_callback
        if not obj:  # obj is None, so this is an object add page, and we display only product class
            kwargs['fields'] = ['product_class', ]
            self.inlines = []
        else: # if obj - this a object change page, and we display all fields without product class and attributes (HStore field), but with rendered attributse fields
            kwargs['fields'] = '__all__'
            self.exclude = ['attributes']
            self.inlines = [ProductImageAdminInline]
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        # override get_fieldset to include all fields for product attributes
        fieldsets = super().get_fieldsets(request, obj)
        form = self.get_form(request, obj=obj)
        if obj:
            for f in form.attribute_fields:
                fieldsets[0][1]['fields'] += [f] 
        form.attribute_fields.clear()
        return fieldsets

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

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """enable ordering drop-down alphabetically"""
        if db_field.name == 'image':
            resolved = resolve(request.path_info)
            if resolved.args:
                parent_object = self.parent_model.objects.filter(pk=resolved.args[0]).first()
                if parent_object:
                    kwargs['queryset'] = parent_object.product.images.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    inlines = [StockAdminInline, VariantImageAdminInline]
    list_display = ['product',  'name', 'sku', 'show_attributes']
    form = VariantAttributeAdminForm

    def show_attributes(self, obj):
        attrs = ''
        for value, key in obj.attributes.items():
            attrs += '{}: {}\n'.format(
                ProductAttribute.objects.filter(pk=value).first(),
                AttributeChoiceValue.objects.select_related('attribute').filter(pk=key).first()
            )
        return attrs

    def get_form(self, request, obj=None, **kwargs):
        # Proper kwargs are form, fields, exclude, formfield_callback
        if not obj:  # obj is None, so this is an add page
            kwargs['fields'] = ['product', ]
            self.inlines = []
        else:
            self.exclude = ['attributes']
            # self.readonly_fields = ['product']
            self.inlines = [StockAdminInline, VariantImageAdminInline]
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        # override get_fieldset to include all fields for product attributes
        fieldsets = super().get_fieldsets(request, obj)
        form = self.form
        if obj:
            for f in form.attribute_fields:
                fieldsets[0][1]['fields'] += [f] 
        form.attribute_fields.clear()
        return fieldsets    

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if not change:
            product_id = request.GET.get('id')
            if product_id:
                self.product = Product.objects.filter(id=product_id, product_class__has_variants=True)\
                    .select_related('product_class')\
                    .prefetch_related('categories')
            else:
                self.product = Product.objects.filter(product_class__has_variants=True) \
                    .select_related('product_class') \
                    .prefetch_related('categories')
            context['adminform'].form.fields['product'].queryset = self.product
        return super().render_change_form(request, context, add, change, form_url, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'product':
            kwargs['initial'] = request.GET.get('id')
        return super().formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def save_model(self, request, obj, form, change):
        print(ProductVariant.objects.filter(attributes=obj.attributes))
        if not obj.id:
            # obj.product = self.product.first()
            obj.save()
            obj.sku = obj.id
        return super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('/admin/product/productvariant/{}/change/?id={}'.format(obj.id, request.GET.get('id')))

    # def has_add_permission(self, request):
    #     return False

@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ('name', )


class AttributeChoiceValueAdminInline(admin.TabularInline):
    fields = ['id', 'name', 'slug', 'color']
    prepopulated_fields = {"slug": ("name",)}
    model = AttributeChoiceValue


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    prepopulated_fields = {"slug": ("name",)}
    inlines = [AttributeChoiceValueAdminInline]