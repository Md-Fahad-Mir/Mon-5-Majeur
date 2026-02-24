
from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
schema_view = get_schema_view(
    openapi.Info(
        title="🏀 MON5MAJEUR - Made by Md Fahad Mir",
        default_version='v1',
        description="API documentation for the MON5MAJEUR project",
        
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

def redirect_to_docs(request):
    """Redirect root URL to API documentation"""
    return redirect('schema-swagger-ui')


# Sentry Debub

def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path('admin/', admin.site.urls),

    # apps urls
    path('api/', include('apps.matches.urls')),
    path('api/', include('apps.players.urls')),
    path('api/', include('apps.private_leagues.urls')),
    path('api/', include('apps.public_leagues.urls')),

    path('api/', include('apps.teams.urls')),
    path('api/', include('apps.leaderboard.urls')),
    path('api/', include('apps.admin_panel.urls')),
    path('api/', include('apps.games.urls')),
    path('api/', include('apps.users.urls')),
    path('api/', include('apps.scoring.urls')),

    # allauth
    path('accounts/', include('allauth.urls')),

    # sentry
    path('sentry-debug/', trigger_error),

    

    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # Redirect root to docs
    path('', redirect_to_docs, name='root-redirect'),

]
