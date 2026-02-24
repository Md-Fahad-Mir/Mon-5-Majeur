from django.urls import re_path
from .consumers import LeagueConsumer

websocket_urlpatterns = [
    re_path(r'ws/private-leagues/(?P<league_id>\w+)/$', LeagueConsumer.as_asgi()),
]