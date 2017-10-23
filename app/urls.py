from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^cart/', include('cart.urls', namespace='cart')),
    url(r'^checkout/', include('checkout.urls', namespace='checkout')),
    url(r'^profiles/', include('profiles.urls', namespace='profiles')),
    url(r'^product/', include('product.urls', namespace='product')),

    url(r'^search/', include("search.urls", namespace='search')),

    url(r'^like/', include("like.urls", namespace='likes')),

    url(r'^', include('products.urls', namespace='products')),

]

if settings.DEBUG:
    # import debug_toolbar
    #
    # urlpatterns += [
    #     url(r'^__debug__/', include(debug_toolbar.urls)),
    # ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)