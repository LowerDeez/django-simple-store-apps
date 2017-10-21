from .models import Cart


def get_cart(request, create=False):
    """
    Return current Cart in session or create new Cart object if doesn't exists.
    :return: Cart object
    """
    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated() and request.session.get('user_cart'):
        kwargs = {
            'session_key': request.session['user_cart'],
            'user': request.user
        }
    else:
        kwargs = {'session_key': request.session.session_key}

    try:
        return Cart.objects.get(**kwargs)
    except Cart.DoesNotExist:
        if create:
            return Cart.objects.create(**kwargs)
        else:
            return None


### UTILS FOR VARIANT FIELD
from satchless.item import InsufficientStock
from uuid import UUID
from django.utils.translation import pgettext_lazy
from django.contrib import messages


def contains_unavailable_variants(cart):
    try:
        for line in cart.items.all():
            line.variant.check_quantity(line.quantity)
    except InsufficientStock:
        return True
    return False


def remove_unavailable_variants(cart):
    for line in cart.items.all():
        try:
            cart.add(line.variant, quantity=line.quantity, replace=True)
        except InsufficientStock as e:
            quantity = e.item.get_stock_quantity()
            cart.add(line.variant, quantity=quantity, replace=True)


def check_product_availability_and_warn(request, cart):
    if contains_unavailable_variants(cart):
        msg = pgettext_lazy(
            'Cart warning message',
            'Sorry. We don\'t have that many items in stock. '
            'Quantity was set to maximum available for now.')
        messages.warning(request, msg)
        remove_unavailable_variants(cart)


def get_or_create_user_cart(user, cart_queryset=Cart.objects.all()):
    """Returns open cart for given user or creates one.
    :type cart_queryset: saleor.cart.models.CartQueryset
    :type user: User
    :rtype: Cart
    """
    return cart_queryset.open().get_or_create(user=user)[0]


def get_user_cart(user, cart_queryset=Cart.objects.all()):
    """Returns open cart for given user or None if not found.
    :type cart_queryset: saleor.cart.models.CartQueryset
    :type user: User
    :rtype: Cart | None
    """
    return cart_queryset.open().filter(user=user).first()


def token_is_valid(token):
    if token is None:
        return False
    if isinstance(token, UUID):
        return True
    try:
        UUID(token)
    except ValueError:
        return False
    return True








