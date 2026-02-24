import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.private_leagues.routing import websocket_urlpatterns as private_ws_patterns
from apps.public_leagues.routing import websocket_urlpatterns as public_ws_patterns

from .custom_middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            private_ws_patterns + public_ws_patterns
        )
    ),
})

