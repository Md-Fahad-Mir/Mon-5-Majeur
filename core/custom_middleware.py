from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from jwt import decode as jwt_decode
from django.conf import settings
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

@sync_to_async
def get_user_from_token(user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        logger.info(f"Query string: {query_string}")
        
        query_params = parse_qs(query_string)
        logger.info(f"Query params: {query_params}")
        
        token = query_params.get("token", [None])[0]
        logger.info(f"Extracted token: {token}")

        if token:
            try:
                logger.info(f"Validating token...")
                UntypedToken(token)  # validate token
                decoded = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                logger.info(f"Decoded token: {decoded}")
                
                user_id = decoded.get("user_id")
                logger.info(f"User ID from token: {user_id}")
                
                user = await get_user_from_token(user_id)
                if user:
                    scope["user"] = user
                    logger.info(f"User authenticated: {user}")
                else:
                    logger.warning(f"User {user_id} not found")
                    scope["user"] = AnonymousUser()
            except Exception as e:
                logger.error(f"Token validation failed: {e}", exc_info=True)
                scope["user"] = AnonymousUser()
        else:
            logger.info("No token provided, setting AnonymousUser")
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
