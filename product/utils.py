from collections import defaultdict, namedtuple

from six import iteritems

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils.encoding import smart_text
from django_prices.templatetags import prices_i18n

from .models import Product, Stock
from .product_status import ProductAvailabilityStatus, VariantAvailabilityStatus
# from ..cart.utils import get_cart_from_request, get_or_create_cart_from_request
# from ..core.utils import to_local_currency
# from .forms import ProductForm

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


def products_visible_to_user(user):
    """
    If user is admin, returns all products, else - only available
    :param user: User instance
    :return: Products queryset
    """
    if user.is_authenticated and user.is_active and user.is_staff:
        return Product.objects.all()
    else:
        return Product.objects.get_available_products()


def products_with_details(user):
    """
    Returns product with prefetch related
    :param user: User instance
    :return: Products queryset
    """
    products = products_visible_to_user(user)
    products = products.prefetch_related(
        'category', 'images', 'variants__stock',
        'variants__variant_images__image', 'attributes__values',
        'product_type__variant_attributes__values',
        'product_type__product_attributes__values')
    return products


def products_for_homepage():
    """
    Returns products to display on home page (featured)
    :return: Products queryset
    """
    user = AnonymousUser()
    products = products_with_details(user)
    products = products.filter(is_featured=True)
    return products


def get_product_images(product):
    """
    Returns list of product images that will be placed in product gallery
    """
    return list(product.images.all())


def products_for_api(user):
    products = products_visible_to_user(user)
    return products.prefetch_related(
        'images',
        'categories',
        'variants',
        'variants__stock')


# def handle_cart_form(request, product, create_cart=False):
#     if create_cart:
#         cart = get_or_create_cart_from_request(request)
#     else:
#         cart = get_cart_from_request(request)
#     form = ProductForm(
#         cart=cart, product=product, data=request.POST or None,
#         discounts=request.discounts)
#     return form, cart


def products_for_cart(user):
    """
    Returns products, which can be added to cart
    :param user: user
    :return: Product queryset
    """
    products = products_visible_to_user(user)
    products = products.prefetch_related('variants__variant_images__image')
    return products


def product_json_ld(product, availability=None, attributes=None):
    # type: (saleor.product.models.Product, saleor.product.utils.ProductAvailability, dict) -> dict  # noqa
    """Generates JSON-LD data for product"""
    data = {'@context': 'http://schema.org/',
            '@type': 'Product',
            'name': smart_text(product),
            'image': smart_text(product.get_first_image()),
            'description': product.description,
            'offers': {'@type': 'Offer',
                       'itemCondition': 'http://schema.org/NewCondition'}}

    if availability is not None:
        if availability.price_range:
            data['offers']['priceCurrency'] = settings.DEFAULT_CURRENCY
            data['offers']['price'] = availability.price_range.min_price.net

        if availability.available:
            data['offers']['availability'] = 'http://schema.org/InStock'
        else:
            data['offers']['availability'] = 'http://schema.org/OutOfStock'

    if attributes is not None:
        brand = ''
        for key in attributes:
            if key.name == 'brand':
                brand = attributes[key].name
                break
            elif key.name == 'publisher':
                brand = attributes[key].name

        if brand:
            data['brand'] = {'@type': 'Thing', 'name': brand}
    return data


def get_product_attributes_data(product):
    """
    Returns product attributes as dict
    :param product:
    :return:
    """
    attributes = product.product_type.product_attributes.all()
    attributes_map = {attribute.pk: attribute for attribute in attributes}
    values_map = get_attributes_display_map(product, attributes)
    return {attributes_map.get(attr_pk): value_obj
            for (attr_pk, value_obj) in values_map.items()}


def get_attributes_display_map(obj, attributes):
    display_map = {}
    for attribute in attributes:
        value = obj.attributes.get(smart_text(attribute.pk))
        if value:
            choices = {smart_text(a.pk): a for a in attribute.values.all()}
            choice_obj = choices.get(value)
            if choice_obj:
                display_map[attribute.pk] = choice_obj
            else:
                display_map[attribute.pk] = value
    return display_map


def price_as_dict(price):
    if not price:
        return None
    return {'currency': price.currency,
            'gross': price.gross,
            'grossLocalized': prices_i18n.gross(price),
            'net': price.net,
            'netLocalized': prices_i18n.net(price)}


def price_range_as_dict(price_range):
    if not price_range:
        return None
    return {'maxPrice': price_as_dict(price_range.max_price),
            'minPrice': price_as_dict(price_range.min_price)}


def get_variant_url_from_product(product, attributes):
    return '%s?%s' % (product.get_absolute_url(), urlencode(attributes))


def get_variant_url(variant):
    attributes = {}
    values = {}
    for attribute in variant.product.product_type.variant_attributes.all():
        attributes[str(attribute.pk)] = attribute
        for value in attribute.values.all():
            values[str(value.pk)] = value

    return get_variant_url_from_product(variant.product, attributes)


def get_product_availability_status(product):

    is_available = product.is_available()
    has_stock_records = Stock.objects.filter(variant__product=product)
    are_all_variants_in_stock = all(
        variant.is_in_stock() for variant in product.variants.all())
    is_in_stock = any(
        variant.is_in_stock() for variant in product.variants.all())
    requires_variants = product.product_type.has_variants

    if not product.is_published:
        return ProductAvailabilityStatus.NOT_PUBLISHED
    elif requires_variants and not product.variants.exists():
        # We check the requires_variants flag here in order to not show this
        # status with product classes that don't require variants, as in that
        # case variants are hidden from the UI and user doesn't manage them.
        return ProductAvailabilityStatus.VARIANTS_MISSING
    elif not has_stock_records:
        return ProductAvailabilityStatus.NOT_CARRIED
    elif not is_in_stock:
        return ProductAvailabilityStatus.OUT_OF_STOCK
    elif not are_all_variants_in_stock:
        return ProductAvailabilityStatus.LOW_STOCK
    elif not is_available and product.available_on is not None:
        return ProductAvailabilityStatus.NOT_YET_AVAILABLE
    else:
        return ProductAvailabilityStatus.READY_FOR_PURCHASE


def get_variant_availability_status(variant):
    has_stock_records = variant.stock.exists()
    if not has_stock_records:
        return VariantAvailabilityStatus.NOT_CARRIED
    elif not variant.is_in_stock():
        return VariantAvailabilityStatus.OUT_OF_STOCK
    else:
        return VariantAvailabilityStatus.AVAILABLE