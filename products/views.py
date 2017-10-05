from django.views.generic import ListView, DetailView

from cart.forms import AddToCartForm
from .models.product import Product, Category


class CategoryDetailView(DetailView):
    """
    View which display all products for current category
    """
    model = Category
    slug_url_kwarg = 'category_slug'
    template_name = "category_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        products = Product.objects.filter(
            category=self.get_object()
        ).prefetch_related('image')

        context.update({
            'products': products
        })
        return context


class ProductsListView(ListView):
    """
    Main view to display all products
    """
    model = Product
    queryset = Product.objects.all().active().prefetch_related('image')
    template_name = "product_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AddToCartForm
        return context


class ProductDetailView(DetailView):
    """
    Product detail view
    """
    model = Product
    template_name = "product_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AddToCartForm
        return context