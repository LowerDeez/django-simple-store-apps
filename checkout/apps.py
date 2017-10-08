from django.apps import AppConfig


class CheckoutConfig(AppConfig):
    name = 'checkout'

    def ready(self):
        # noinspection PyUnresolvedReferences
        from . import signals