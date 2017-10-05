from django.apps import AppConfig

default_app_config = 'activity.apps.AcctivityAppConfig'

class CartConfig(AppConfig):
    name = 'cart'

    def ready(self):
        import cart.signals
