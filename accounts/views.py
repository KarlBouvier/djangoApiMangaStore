from django.contrib.auth import login, authenticate
from .serializer import RegisterSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def connexion(request):
    """
    API endpoint for user login
    Body: { username, password }
    Returns: JWT tokens and user info
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({
            'detail': 'username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({
            'detail': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    refresh_token = str(refresh)

    return Response({
        'access': access,
        'refresh': refresh_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    })

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def inscription(request):
    """
    API endpoint for user registration
    Body: { username, email, password, password2 }
    Returns: JWT tokens and user info
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)
        
        return Response({
            'access': access,
            'refresh': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deconnexion(request):
    """
    API endpoint for user logout
    Blacklists the refresh token
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({
            'detail': 'Successfully logged out'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'detail': 'Invalid token or token already blacklisted'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    API endpoint to get current authenticated user info
    Returns: User details
    """
    user = request.user
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
    })
