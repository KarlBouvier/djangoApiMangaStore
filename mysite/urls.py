"""
URL configuration for mysite project.

All endpoints are now REST API endpoints for Next.js frontend.
"""
from django.contrib import admin
from django.urls import path, include
from accounts import views as account_view
from connect import views as connect_view
from produit import views as produit_view
from mysite import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/csrf/', produit_view.get_csrf_token, name='csrf_token'),
    
    # Authentication API endpoints
    path('api/auth/login/', account_view.connexion, name="login"),
    path('api/auth/register/', account_view.inscription, name="register"),
    path('api/auth/logout/', account_view.deconnexion, name="logout"),
    path('api/auth/me/', account_view.current_user, name='current_user'),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),
    
    # Manga & Collection API endpoints
    path('api/manga/', connect_view.get_mangas, name="get_mangas"),
    path('api/manga/<int:manga_id>/', connect_view.manga_detail_view, name='manga_detail'),
    path('api/collection/', connect_view.collection_view, name="collection"),
    path('api/recherche/', connect_view.recherche_view, name="recherche"),
    
    # Shopping Cart API endpoints
    path('api/panier/', produit_view.panier_view, name='panier'),
    path('api/panier/ajouter/<int:tome_id>/', produit_view.ajouter_au_panier_view, name='ajouter_au_panier'),
    path('api/panier/retirer/<int:tome_id>/', produit_view.retirer_du_panier_view, name='retirer_du_panier'),
    path('api/panier/modifier/<int:tome_id>/', produit_view.modifier_quantite_view, name='modifier_quantite'),
    path('api/panier/vider/', produit_view.vider_panier_view, name='vider_panier'),
    
    # Order API endpoints
    path('api/commandes/create/', produit_view.commander_view, name='commander'),
    path('api/commandes/', produit_view.historique_commandes_view, name='historique_commandes'),
    path('api/commandes/<int:commande_id>/', produit_view.detail_commande_view, name='detail_commande'),
    
    # Payment API endpoints
    path('api/payments/create-intent/', produit_view.create_payment_intent, name='create_payment_intent'),
    path('api/payments/<str:payment_id>/status/', produit_view.get_payment_status, name='get_payment_status'),
    path('api/webhooks/stripe/', produit_view.stripe_webhook, name='stripe_webhook'),
    
    # Celery Test API endpoints
    path('api/celery/test/', produit_view.start_test_task, name='start_test_task'),
    path('api/celery/status/<str:task_id>/', produit_view.get_task_status, name='get_task_status'),
    path('api/celery/email/', produit_view.start_email_task, name='start_email_task'),
    path('api/celery/process-order/', produit_view.start_order_processing_task, name='start_order_processing_task'),
]

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]