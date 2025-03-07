import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import app.routing  

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trading.settings")

# Add this to ensure Django is fully initialized before use
django.setup()

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(app.routing.websocket_urlpatterns)
        ),
    }
)
