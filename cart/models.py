from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.translation import pgettext_lazy
from django.utils.timezone import now

from products.models.product import Product
from .cart_status import CartStatus, logger


class CartQueryset(models.QuerySet):

    def anonymous(self):
        return self.filter(user=None)

    def open(self):
        return self.filter(status=CartStatus.OPEN)

    def saved(self):
        return self.filter(status=CartStatus.SAVED)

    def waiting_for_payment(self):
        return self.filter(status=CartStatus.WAITING_FOR_PAYMENT)

    def checkout(self):
        return self.filter(status=CartStatus.CHECKOUT)

    def canceled(self):
        return self.filter(status=CartStatus.CANCELED)

    def for_display(self):
        return self.prefetch_related(
            'lines__variant__product__categories',
            'lines__variant__product__images',
            'lines__variant__product__product_class__product_attributes__values',  # noqa
            'lines__variant__product__product_class__variant_attributes__values',  # noqa
            'lines__variant__stock')


class Cart(models.Model):
    """
    Cart Model, which stores user, session key and cart items
    """
    # status fields:
    status = models.CharField(
        pgettext_lazy('Cart field', 'order status'),
        max_length=32, choices=CartStatus.CHOICES, default=CartStatus.OPEN)
    last_status_change = models.DateTimeField(
        pgettext_lazy('Cart field', 'last status change'),
        auto_now_add=True,
        blank=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
    session_key = models.CharField(max_length=255, null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)
    active = models.BooleanField(default=True)
    price_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    price_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # possible fields for voucher and token
    # voucher = models.ForeignKey(
    #     'discount.Voucher', null=True, related_name='+',
    #     on_delete=models.SET_NULL,
    #     verbose_name=pgettext_lazy('Cart field', 'token'))
    # token = models.UUIDField(
    #     pgettext_lazy('Cart field', 'token'),
    #     primary_key=True, default=uuid4, editable=False)

    objects = CartQueryset.as_manager()

    class Meta:
        unique_together = ('user', 'session_key')

    def __str__(self):
        return "Cart id: {id}".format(id=self.pk)

    def update_subtotal(self):
        subtotal = self.items.all().aggregate(sum=models.Sum('total_price'))
        self.price_subtotal = subtotal['sum']
        self.save()

    def get_total_quantity_of_items(self):
        qty = self.items.all().aggregate(sum=models.Sum('quantity'))
        return qty['sum']

    def change_status(self, status):
        if status not in dict(CartStatus.CHOICES):
            raise ValueError('Not expected status')
        if status != self.status:
            self.status = status
            self.last_status_change = now()
            self.save()

    def count(self):
        lines = self.items.all()
        return lines.aggregate(total_quantity=models.Sum('quantity'))

    def clear(self):
        self.delete()

    def add(self, variant, quantity=1, data=None, replace=False,
            check_quantity=True):
        """
        Creates new CartItem (for variant field)
        :param variant:
        :param quantity:
        :param data:
        :param replace:
        :param check_quantity:
        :return:
        """
        cart_line, created = self.items.get_or_create(
            variant=variant, defaults={'quantity': 0})

        if replace:
            new_quantity = quantity
        else:
            new_quantity = cart_line.quantity + quantity

        if new_quantity < 0:
            raise ValueError('%r is not a valid quantity (results in %r)' % (
                quantity, new_quantity))

        if check_quantity:
            variant.check_quantity(new_quantity)

        cart_line.quantity = new_quantity

        if not cart_line.quantity:
            cart_line.delete()
        else:
            cart_line.save(update_fields=['quantity'])
        self.update_quantity()


class CartItem(models.Model):
    """
    Cart Item which contains Cart field (Cart can have many cart items),
    product, product quantity, total price (product price * product quantity)
    """
    cart = models.ForeignKey(Cart, null=True, related_name='items', blank=True)
    product = models.ForeignKey(Product, related_name='products', on_delete=models.CASCADE)
    # variant = models.ForeignKey(
    #     'product.ProductVariant', related_name='+',
    #     verbose_name=pgettext_lazy('Cart line field', 'product'))
    date_added = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    class Meta:
        ordering = ['date_added']

    def get_absolute_url(self):
        return self.product.get_absolute_url()

    def __str__(self):
        return self.product.name