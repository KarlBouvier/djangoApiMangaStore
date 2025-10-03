from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken
from django.http import JsonResponse

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # On vérifie seulement les routes protégées
        if request.path.startswith('/home/'):
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if not auth_header or not auth_header.startswith("Bearer "):
                return JsonResponse({"detail": "Authentication required"}, status=401)

            token = auth_header.split(" ")[1]
            try:
                AccessToken(token)
            except InvalidToken:
                return JsonResponse({"detail": "Invalid or expired token"}, status=401)

        return self.get_response(request)