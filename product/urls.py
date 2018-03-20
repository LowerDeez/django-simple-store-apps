from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^details/(?P<slug>[a-z0-9-_]+?)-(?P<product_id>[0-9]+)/$',
        views.product_details, name='details'),
    url(r'^category/(?P<path>[a-z0-9-_/]+?)-(?P<category_id>[0-9]+)/$',
        views.category_index, name='category'),
    url(r'^test_view/$',
        views.test_view, name='product-add'),
]