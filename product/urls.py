from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^$',
        views.product_create, name='product-add'),
]