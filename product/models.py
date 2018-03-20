from __future__ import unicode_literals

import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.fields import HStoreField
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Max, Q
from django.db.models.signals import post_save
from django.utils.encoding import smart_text
from django.utils.text import slugify
from django.utils.translation import pgettext_lazy
from django.utils import six
from django_prices.models import Price, PriceField
from mptt.managers import TreeManager
from mptt.models import MPTTModel
from prices import PriceRange
from satchless.item import InsufficientStock, Item, ItemRange
from text_unidecode import unidecode
from versatileimagefield.fields import VersatileImageField, PPOIField

# from ..discount.models import calculate_discounted_price
# from ..search import index
# from .utils import *


class Category(MPTTModel):
    """
    Category model

    Attributes:
        name: category name
        slug: category slug, using for beautiful urls
        description: category description
        parent: parent category
    """
    name = models.CharField(
        pgettext_lazy('Category field', 'name'),
        max_length=128)
    slug = models.SlugField(
        pgettext_lazy('Category field', 'slug'),
        max_length=128)
    description = models.TextField(
        pgettext_lazy('Category field', 'description'),
        blank=True)
    parent = models.ForeignKey(
        'self',
        null=True, blank=True,
        related_name='children',
        verbose_name=pgettext_lazy('Category field', 'parent'))

    objects = models.Manager()
    tree = TreeManager()

    class Meta:
        permissions = (
            ('view_category',
             pgettext_lazy('Permission description', 'Can view categories')),
            ('edit_category',
             pgettext_lazy('Permission description', 'Can edit categories')))

    def __str__(self):
        return self.name

    def get_absolute_url(self, ancestors=None):
        return reverse('product:category',
                       kwargs={'path': self.get_full_path(ancestors),
                               'category_id': self.id})

    def get_full_path(self, ancestors=None):
        if not self.parent_id:
            return self.slug
        if not ancestors:
            ancestors = self.get_ancestors()
        nodes = [node for node in ancestors] + [self]
        return '/'.join([smart_text(node.slug) for node in nodes])


class ProductType(models.Model):
    """
    Product Class Model

    Attributes:
        name: category name
        has_variants: defines is product has variants
        product_attributes: attributes for product
        variant_attributes: attributes for product's variants
        is_shipping_required: defines is shipping for product required
    """
    name = models.CharField(max_length=128)
    has_variants = models.BooleanField(default=True)
    product_attributes = models.ManyToManyField(
        'ProductAttribute', related_name='product_types', blank=True)
    variant_attributes = models.ManyToManyField(
        'ProductAttribute', related_name='product_variant_types', blank=True)
    is_shipping_required = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        class_ = type(self)
        return '<%s.%s(pk=%r, name=%r)>' % (
            class_.__module__, class_.__name__, self.pk, self.name)


class ProductQuerySet(models.QuerySet):
    def available_products(self):
        today = datetime.date.today()
        return self.filter(
            Q(available_on__lte=today) | Q(available_on__isnull=True),
            Q(is_published=True))


class Product(models.Model, ItemRange):
    """
    Product Model

    Attributes:
        product_type: type of product, which defines product attributes
        name: product name
        description: product description
        categories: product categories
        price: product price
        available_on: date to which product is available
        is_published: is product published
        attributes: product attributes
        updated_at: date when product was updated
        is_featured: is product displays on main page

    """
    product_type = models.ForeignKey(
        ProductType, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    description = models.TextField()
    category = models.ForeignKey(
        Category, related_name='products', on_delete=models.CASCADE)
    price = PriceField(
        currency=settings.DEFAULT_CURRENCY, max_digits=12, decimal_places=2)
    available_on = models.DateField(blank=True, null=True)
    is_published = models.BooleanField(default=True)
    attributes = HStoreField(default={})
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_featured = models.BooleanField(default=False)

    objects = ProductQuerySet.as_manager()

    class Meta:
        permissions = (
            ('view_product',
             pgettext_lazy('Permission description', 'Can view products')),
            ('edit_product',
             pgettext_lazy('Permission description', 'Can edit products')))

    def __iter__(self):
        if not hasattr(self, '__variants'):
            setattr(self, '__variants', self.variants.all())
        return iter(getattr(self, '__variants'))

    def __repr__(self):
        class_ = type(self)
        return '<%s.%s(pk=%r, name=%r)>' % (
            class_.__module__, class_.__name__, self.pk, self.name)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            'product:details',
            kwargs={'slug': self.get_slug(), 'product_id': self.id})

    def get_slug(self):
        """
        Create slug from name field
        :return:
        """
        return slugify(smart_text(unidecode(self.name)))

    def is_in_stock(self):
        return any(variant.is_in_stock() for variant in self)

    def get_first_category(self):
        for category in self.categories.all():
            if not category.hidden:
                return category
        return None

    def is_available(self):
        today = datetime.date.today()
        return self.available_on is None or self.available_on <= today

    def get_first_image(self):
        first_image = self.images.first()

        if first_image:
            return first_image.image
        return None

    def get_attribute(self, pk):
        return self.attributes.get(smart_text(pk))

    def set_attribute(self, pk, value_pk):
        self.attributes[smart_text(pk)] = smart_text(value_pk)

    # def get_price_range(self, discounts=None, **kwargs):
    #     if not self.variants.exists():
    #         price = calculate_discounted_price(
    #             self, self.price, discounts, **kwargs)
    #         return PriceRange(price, price)
    #     else:
    #         return super(Product, self).get_price_range(
    #             discounts=discounts, **kwargs)

    def get_gross_price_range(self, **kwargs):
        grosses = [self.get_price_per_item(item, **kwargs) for item in self]
        if not grosses:
            return None
        grosses = sorted(grosses, key=lambda x: x.tax)
        return PriceRange(min(grosses), max(grosses))


# creating default variation for each product, not important
def product_save_receiver(sender, instance, created, **kwargs):
    product = instance
    variations = product.variants.all()
    if variations.count() == 0:
        new_var = ProductVariant()
        new_var.product = product
        new_var.name = 'Default'
        new_var.sku = '{} - {} - default'.format(product.id, product.name)
        new_var.save()
post_save.connect(product_save_receiver, sender=Product)


class ProductVariant(models.Model, Item):
    product = models.ForeignKey(Product, related_name='variants')
    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100, blank=True)
    price_override = PriceField(
        currency=settings.DEFAULT_CURRENCY, max_digits=12, decimal_places=2,
        blank=True, null=True)
    attributes = HStoreField(default={})
    images = models.ManyToManyField('ProductImage', through='VariantImage')

    def __str__(self):
        return self.name  # or self.display_variant()

    def check_quantity(self, quantity):
        available_quantity = self.get_stock_quantity()
        if quantity > available_quantity:
            raise InsufficientStock(self)

    def get_stock_quantity(self):
        if not len(self.stock.all()):
            return 0
        return max([stock.quantity_available for stock in self.stock.all()])

    # def get_price_per_item(self, discounts=None, **kwargs):
    #     price = self.price_override or self.product.price
    #     price = calculate_discounted_price(self.product, price, discounts,
    #                                        **kwargs)
    #     return price

    def get_absolute_url(self):
        slug = self.product.get_slug()
        product_id = self.product.id
        return reverse('product:details',
                       kwargs={'slug': slug, 'product_id': product_id})

    def as_data(self):
        return {
            'product_name': str(self),
            'product_id': self.product.pk,
            'variant_id': self.pk,
            'unit_price': str(self.get_price_per_item().gross)}

    def is_shipping_required(self):
        return self.product.product_class.is_shipping_required

    def is_in_stock(self):
        return any(
            [stock.quantity_available > 0 for stock in self.stock.all()])

    def get_attribute(self, pk):
        return self.attributes.get(smart_text(pk))

    def set_attribute(self, pk, value_pk):
        self.attributes[smart_text(pk)] = smart_text(value_pk)

    # def display_variant(self, attributes=None):
    #     if attributes is None:
    #         attributes = self.product.product_class.variant_attributes.all()
    #     values = get_attributes_display_map(self, attributes)
    #     if values:
    #         return ', '.join(
    #             ['%s: %s' % (smart_text(attributes.get(id=int(key))),
    #                          smart_text(value))
    #              for (key, value) in six.iteritems(values)])
    #     else:
    #         return smart_text(self.sku)

    def display_product(self):
        return '%s (%s)' % (smart_text(self.product),
                            smart_text(self))

    def get_first_image(self):
        return self.product.get_first_image()

    def select_stockrecord(self, quantity=1):
        # By default selects stock with lowest cost price. If stock cost price
        # is None we assume price equal to zero to allow sorting.
        stock = [
            stock_item for stock_item in self.stock.all()
            if stock_item.quantity_available >= quantity]
        zero_price = Price(0, currency=settings.DEFAULT_CURRENCY)
        stock = sorted(
            stock, key=(lambda s: s.cost_price or zero_price), reverse=False)
        if stock:
            return stock[0]

    def get_cost_price(self):
        stock = self.select_stockrecord()
        if stock:
            return stock.cost_price

    def get_attributes(self):
        attrs = []
        for value, key in self.attributes.items():
            try:
                attrs.extend(AttributeChoiceValue.objects.select_related('attribute').filter(pk=key).first().name)
            except AttributeError:
                continue
        return attrs


class StockLocation(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        permissions = (
            ('view_stock_location',
             pgettext_lazy('Permission description',
                           'Can view stock location')),
            ('edit_stock_location',
             pgettext_lazy('Permission description',
                           'Can edit stock location')))

    def __str__(self):
        return self.name


class Stock(models.Model):
    variant = models.ForeignKey(
        ProductVariant, related_name='stock', on_delete=models.CASCADE)
    location = models.ForeignKey(
        StockLocation, null=True, on_delete=models.CASCADE)
    quantity = models.IntegerField(
        validators=[MinValueValidator(0)], default=Decimal(1))
    quantity_allocated = models.IntegerField(
        validators=[MinValueValidator(0)], default=Decimal(0))
    cost_price = PriceField(
        currency=settings.DEFAULT_CURRENCY, max_digits=12, decimal_places=2,
        blank=True, null=True)

    class Meta:
        unique_together = ('variant', 'location')

    def __str__(self):
        return '%s - %s' % (self.variant.name, self.location)

    @property
    def quantity_available(self):
        return max(self.quantity - self.quantity_allocated, 0)


class ProductAttribute(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    
    class Meta:
        ordering = ('slug', )

    def __str__(self):
        return self.name

    def get_formfield_name(self):
        return slugify('attribute-%s' % self.slug, allow_unicode=True)

    def has_values(self):
        return self.values.exists()


class AttributeChoiceValue(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    color = models.CharField(
        max_length=7, blank=True,
        validators=[RegexValidator('^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')],)
    attribute = models.ForeignKey(
        ProductAttribute, related_name='values', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'attribute')

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name='images', on_delete=models.CASCADE)
    image = VersatileImageField(
        upload_to='products', ppoi_field='ppoi', blank=False)
    ppoi = PPOIField()
    alt = models.CharField(max_length=128, blank=True)
    order = models.PositiveIntegerField(editable=False)

    class Meta:
        ordering = ('order', )

    def get_ordering_queryset(self):
        return self.product.images.all()

    def save(self, *args, **kwargs):
        if self.order is None:
            qs = self.get_ordering_queryset()
            existing_max = qs.aggregate(Max('order'))
            existing_max = existing_max.get('order__max')
            self.order = 0 if existing_max is None else existing_max + 1
        super(ProductImage, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        qs = self.get_ordering_queryset()
        qs.filter(order__gt=self.order).update(order=F('order') - 1)
        super(ProductImage, self).delete(*args, **kwargs)

    def __str__(self):
        return '{} - {}'.format(self.product.name, self.order)


class VariantImage(models.Model):
    variant = models.ForeignKey(
        'ProductVariant', related_name='variant_images',
        on_delete=models.CASCADE)
    image = models.ForeignKey(
        ProductImage, related_name='variant_images', on_delete=models.CASCADE)


class Collection(models.Model):
    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128)
    products = models.ManyToManyField(
        Product, blank=True, related_name='collections')

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            'product:collection',
            kwargs={'pk': self.id, 'slug': self.slug})