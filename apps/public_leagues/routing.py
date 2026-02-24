from django.urls import re_path
from .consumers import PublicLeagueConsumer

websocket_urlpatterns = [
    re_path(r'ws/public-leagues/(?P<league_id>\w+)/$', PublicLeagueConsumer.as_asgi()),
]
