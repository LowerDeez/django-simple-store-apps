from __future__ import unicode_literals

import datetime

from django.http import HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, redirect

from .filters import (get_now_sorted_by,
                      ProductFilter, ProductCategoryFilter)
from .models import Category, Product, AttributeChoiceValue, ProductVariant
from .utils import (
    products_with_details,
    get_product_images,
    get_product_attributes_data,
)
from django.template.response import TemplateResponse


def test_view(request):
    """
    test view
    """
    product = Product.objects.first()
    attr_choice = AttributeChoiceValue.objects.filter(slug='red').first()
    print(attr_choice)
    print(Product.objects.filter(attributes__values__contains=[attr_choice.id]))
    print(product)
    print(product.attributes)
    print(ProductVariant.objects.all())
    return TemplateResponse(request, 'dashboard/product/form.html', {
        'product': product,
        'variants': ProductVariant.objects.all(),

    })


def product_details(request, slug, product_id, form=None):
    """Product details page
    The following variables are available to the template:
    product:
        The Product instance itself.
    is_visible:
        Whether the product is visible to regular users (for cases when an
        admin is previewing a product before publishing).
    form:
        The add-to-cart form.
    price_range:
        The PriceRange for the product including all discounts.
    undiscounted_price_range:
        The PriceRange excluding all discounts.
    discount:
        Either a Price instance equal to the discount value or None if no
        discount was available.
    local_price_range:
        The same PriceRange from price_range represented in user's local
        currency. The value will be None if exchange rate is not available or
        the local currency is the same as site's default currency.
    """
    products = products_with_details(user=request.user)
    product = get_object_or_404(products, id=product_id)
    if product.get_slug() != slug:
        return HttpResponsePermanentRedirect(product.get_absolute_url())
    today = datetime.date.today()
    is_visible = (
        product.available_on is None or product.available_on <= today)
    template_name = 'product/details_%s.html' % (
        type(product).__name__.lower(),)
    templates = [template_name, 'product/details.html']
    product_images = get_product_images(product)

    product_attributes = get_product_attributes_data(product)
    show_variant_picker = all([v.attributes for v in product.variants.all()])
    return TemplateResponse(
        request, templates,
        {'is_visible': is_visible,
         'product': product,
         'product_attributes': product_attributes,
         'product_images': product_images,
         'show_variant_picker': show_variant_picker
         })


# def product_add_to_cart(request, slug, product_id):
#     # types: (int, str, dict) -> None
#
#     if not request.method == 'POST':
#         return redirect(reverse(
#             'product:details',
#             kwargs={'product_id': product_id, 'slug': slug}))
#
#     products = products_for_cart(user=request.user)
#     product = get_object_or_404(products, pk=product_id)
#     form, cart = handle_cart_form(request, product, create_cart=True)
#     if form.is_valid():
#         form.save()
#         if request.is_ajax():
#             response = JsonResponse({'next': reverse('cart:index')}, status=200)
#         else:
#             response = redirect('cart:index')
#     else:
#         if request.is_ajax():
#             response = JsonResponse({'error': form.errors}, status=400)
#         else:
#             response = product_details(request, slug, product_id, form)
#     return response


from django.core.paginator import InvalidPage, Paginator
from django.http import Http404


def get_paginator_items(items, paginate_by, page_number):
    if not page_number:
        page_number = 1
    paginator = Paginator(items, paginate_by)
    try:
        page_number = int(page_number)
    except ValueError:
        raise Http404('Page can not be converted to an int.')

    try:
        items = paginator.page(page_number)
    except InvalidPage as err:
        raise Http404('Invalid page (%(page_number)s): %(message)s' % {
            'page_number': page_number, 'message': str(err)})
    return items


def category_index(request, path, category_id):
    category = get_object_or_404(Category, id=category_id)
    print(category)
    actual_path = category.get_full_path()
    if actual_path != path:
        return redirect('product:category', permanent=True, path=actual_path,
                        category_id=category_id)
    # Check for subcategories
    categories = category.get_descendants(include_self=True)
    print(categories)
    products = products_with_details(user=request.user).filter(
        category__in=categories).order_by('name')
    print(products)
    product_filter = ProductCategoryFilter(
        request.GET, queryset=products, category=category)

    ctx = {'filter': product_filter}

    return TemplateResponse(request, 'category/index.html', ctx)