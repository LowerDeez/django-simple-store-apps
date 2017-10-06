from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^add/(?P<class_pk>[0-9]+)/$',
        views.product_create, name='product-add'),
]