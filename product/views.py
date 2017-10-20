from django.shortcuts import render
from product.models import *
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse


def product_create(request):
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
