from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Manga, Tome, Panier, PanierItem, Commande, CommandeItem, Payment
from django.db import transaction
from rest_framework import status
from .tasks import test_task, send_email_task, process_order_task
from celery.result import AsyncResult
import stripe
from django.conf import settings
from .serializer import CreatePaymentIntentSerializer, PaymentSerializer
import json

# Create your views here.

def get_or_create_panier(user):
    """Récupère ou crée un panier pour l'utilisateur"""
    panier, created = Panier.objects.get_or_create(utilisateur=user)
    return panier

@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request):
    return Response({'csrfToken': get_token(request)})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def panier_view(request):
    """
    API endpoint to get user's shopping cart
    Returns: JSON with cart items and totals
    """
    user = request.user
    panier = get_or_create_panier(user)
    
    items = panier.items.select_related('tome__manga').all()
    items_data = [
        {
            'id': item.id,
            'tome': {
                'id': item.tome.id,
                'numero': item.tome.numero,
                'manga': {
                    'id': item.tome.manga.id,
                    'nom': item.tome.manga.nom,
                    # 'auteur': item.tome.manga.auteur,
                    'prix': float(item.tome.manga.prix),
                },
                'cover': item.tome.cover.url if item.tome.cover else None,
            },
            'quantite': item.quantite,
            'prix_total': float(item.prix_total),
        }
        for item in items
    ]
    
    return Response({
        'items': items_data,
        'total_tomes': panier.total_tomes,
        'total_prix': float(panier.total_prix),
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ajouter_au_panier_view(request, tome_id):
    """
    API endpoint to add a tome to the shopping cart
    Body: { quantite: number }
    Returns: Updated cart info
    """
    tome = get_object_or_404(Tome, id=tome_id)
    user = request.user
    panier = get_or_create_panier(user)
    
    # Récupérer la quantité depuis les données POST
    quantite = int(request.data.get('quantite', 1))
    
    # Ajouter le tome au panier
    item = panier.ajouter_tome(tome, quantite)
    
    return Response({
        'success': True,
        'message': f'{tome} ajouté au panier',
        'quantite': item.quantite,
        'total_tomes': panier.total_tomes,
        'total_prix': float(panier.total_prix)
    })
        
    # except Exception as e:
    #     return Response(
    #         {'error': str(e)}, 
    #         status=status.HTTP_400_BAD_REQUEST
    #     )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retirer_du_panier_view(request, tome_id):
    """
    API endpoint to remove a tome from the shopping cart
    Returns: Updated cart info
    """
    try:
        tome = get_object_or_404(Tome, id=tome_id)
        user = request.user
        panier = get_or_create_panier(user)
        
        # Retirer le tome du panier
        success = panier.retirer_tome(tome)
        
        if success:
            return Response({
                'success': True,
                'message': f'{tome} retiré du panier',
                'total_tomes': panier.total_tomes,
                'total_prix': float(panier.total_prix)
            })
        else:
            return Response(
                {'error': 'Tome non trouvé dans le panier'}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def modifier_quantite_view(request, tome_id):
    """
    API endpoint to modify tome quantity in the shopping cart
    Body: { quantite: number }
    Returns: Updated cart info
    """
    try:
        tome = get_object_or_404(Tome, id=tome_id)
        user = request.user
        panier = get_or_create_panier(user)
        
        # Récupérer la nouvelle quantité
        nouvelle_quantite = int(request.data.get('quantite', 1))
        
        if nouvelle_quantite <= 0:
            # Si quantité <= 0, retirer l'item
            success = panier.retirer_tome(tome)
            if success:
                return Response({
                    'success': True,
                    'message': f'{tome} retiré du panier',
                    'total_tomes': panier.total_tomes,
                    'total_prix': float(panier.total_prix)
                })
            else:
                return Response(
                    {'error': 'Tome non trouvé dans le panier'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        elif nouvelle_quantite > 10:
            return Response(
                {'error': 'Quantité maximale de 10 autorisée'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            # Mettre à jour la quantité
            try:
                item = panier.items.get(tome=tome)
                item.quantite = nouvelle_quantite
                item.save()
                
                return Response({
                    'success': True,
                    'message': f'Quantité de {tome} mise à jour',
                    'quantite': item.quantite,
                    'prix_total': float(item.prix_total),
                    'total_tomes': panier.total_tomes,
                    'total_prix': float(panier.total_prix)
                })
            except PanierItem.DoesNotExist:
                return Response(
                    {'error': 'Tome non trouvé dans le panier'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
    except ValueError:
        return Response(
            {'error': 'Quantité invalide'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vider_panier_view(request):
    """
    API endpoint to empty the shopping cart
    Returns: Success message
    """
    try:
        user = request.user
        panier = get_or_create_panier(user)
        
        # Vider le panier
        panier.vider()
        
        return Response({
            'success': True,
            'message': 'Panier vidé',
            'total_tomes': 0,
            'total_prix': 0.0
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def commander_view(request):
    """
    API endpoint to create an order
    Creates order with pending status (waiting for payment)
    Returns: Order confirmation with reference
    """
    try:
        user = request.user
        panier = get_or_create_panier(user)
        
        # Vérifier que le panier n'est pas vide
        if panier.total_tomes == 0:
            return Response(
                {'error': 'Votre panier est vide'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            total_tomes = panier.total_tomes
            total_prix = panier.total_prix
            items_data = []
            
            # Créer la commande en base de données
            commande = Commande.objects.create(
                utilisateur=user,
                total_tomes=total_tomes,
                total_prix=total_prix,
                statut=Commande.STATUT_EN_ATTENTE  # En attente de paiement
            )
            
            # Créer les éléments de la commande
            for item in panier.items.select_related('tome__manga').all():
                # Créer l'élément de commande (snapshot)
                CommandeItem.objects.create(
                    commande=commande,
                    tome=item.tome,
                    quantite=item.quantite,
                    prix_unitaire=item.tome.manga.prix,
                )
                
                # Préparer les données pour la réponse
                items_data.append({
                    'manga_nom': item.tome.manga.nom,
                    'tome_numero': item.tome.numero,
                    'quantite': item.quantite,
                    'prix_unitaire': float(item.tome.manga.prix),
                    'prix_total': float(item.prix_total)
                })
            
            # Note: Le panier ne sera vidé qu'après paiement réussi (via webhook)
        
        return Response({
            'success': True,
            'message': f'Commande {commande.reference} effectuée avec succès !',
            'commande': {
                'reference': str(commande.reference),
                'total_tomes': total_tomes,
                'total_prix': float(total_prix),
                'items': items_data,
                'date_creation': commande.date_creation.isoformat(),
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Erreur lors de la commande: {str(e)}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historique_commandes_view(request):
    """
    API endpoint to get user's order history
    Returns: List of all user orders with items
    """
    user = request.user
    commandes = Commande.objects.filter(utilisateur=user).prefetch_related(
        'items__tome__manga'
    ).order_by('-date_creation')
    
    commandes_data = []
    for commande in commandes:
        items = []
        for item in commande.items.all():
            items.append({
                'tome': {
                    'id': item.tome.id,
                    'numero': item.tome.numero,
                    'manga': {
                        'id': item.tome.manga.id,
                        'nom': item.tome.manga.nom,
                        # 'auteur': item.tome.manga.auteur,
                    }
                },
                'quantite': item.quantite,
                'prix_unitaire': float(item.prix_unitaire),
                'prix_total': float(item.prix_total),
            })
        
        commandes_data.append({
            'id': commande.id,
            'reference': str(commande.reference),
            'date_creation': commande.date_creation.isoformat(),
            'statut': commande.statut,
            'total_tomes': commande.total_tomes,
            'total_prix': float(commande.total_prix),
            'items': items,
        })
    
    return Response({'commandes': commandes_data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detail_commande_view(request, commande_id):
    """
    API endpoint to get details of a specific order
    Returns: Order details with all items
    """
    user = request.user
    commande = get_object_or_404(Commande, id=commande_id, utilisateur=user)
    items = commande.items.select_related('tome__manga').all()
    
    items_data = []
    for item in items:
        items_data.append({
            'tome': {
                'id': item.tome.id,
                'numero': item.tome.numero,
                'manga': {
                    'id': item.tome.manga.id,
                    'nom': item.tome.manga.nom,
                    # 'auteur': item.tome.manga.auteur,
                },
                'cover': item.tome.cover.url if item.tome.cover else None,
            },
            'quantite': item.quantite,
            'prix_unitaire': float(item.prix_unitaire),
            'prix_total': float(item.prix_total),
        })
    
    return Response({
        'commande': {
            'id': commande.id,
            'reference': str(commande.reference),
            'date_creation': commande.date_creation.isoformat(),
            'statut': commande.statut,
            'total_tomes': commande.total_tomes,
            'total_prix': float(commande.total_prix),
            'items': items_data,
        }
    })


# Celery Test API Endpoints

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_test_task(request):
    """
    API endpoint to start a test Celery task
    POST /api/celery/test/
    Body: { "message": "Optional custom message" }
    """
    message = request.data.get('message', 'Hello from Celery!')
    
    # Start the task asynchronously
    task = test_task.delay(message)
    
    return Response({
        'status': 'task_started',
        'task_id': task.id,
        'message': 'Test task has been queued for processing'
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_status(request, task_id):
    """
    API endpoint to check the status of a Celery task
    GET /api/celery/status/<task_id>/
    """
    try:
        task_result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': task_result.status,
            'ready': task_result.ready(),
        }
        
        if task_result.ready():
            if task_result.successful():
                response_data['result'] = task_result.result
            else:
                response_data['error'] = str(task_result.info)
        else:
            response_data['message'] = 'Task is still processing'
            
        return Response(response_data)
        
    except Exception as e:
        return Response({
            'error': f'Failed to get task status: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_email_task(request):
    """
    API endpoint to start an email sending task
    POST /api/celery/email/
    Body: { "email": "test@example.com", "subject": "Test", "message": "Hello!" }
    """
    email = request.data.get('email')
    subject = request.data.get('subject')
    message = request.data.get('message')
    
    if not all([email, subject, message]):
        return Response({
            'error': 'Missing required fields: email, subject, message'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Start the email task asynchronously
    task = send_email_task.delay(email, subject, message)
    
    return Response({
        'status': 'email_task_started',
        'task_id': task.id,
        'message': f'Email task queued for {email}'
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_order_processing_task(request):
    """
    API endpoint to start an order processing task
    POST /api/celery/process-order/
    Body: { "order_id": 123 }
    """
    order_id = request.data.get('order_id')
    
    if not order_id:
        return Response({
            'error': 'Missing required field: order_id'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Start the order processing task asynchronously
    task = process_order_task.delay(order_id)
    
    return Response({
        'status': 'order_processing_started',
        'task_id': task.id,
        'message': f'Order {order_id} queued for processing'
    }, status=status.HTTP_202_ACCEPTED)


# Stripe Payment Views

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_intent(request):
    """
    Crée un PaymentIntent Stripe pour une commande
    """
    # Configure Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    serializer = CreatePaymentIntentSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    commande_id = serializer.validated_data['commande_id']
    
    # Try to get commande by reference (UUID) first, then by id
    try:
        commande = Commande.objects.get(reference=commande_id, utilisateur=request.user)
    except Commande.DoesNotExist:
        try:
            commande = Commande.objects.get(id=int(commande_id), utilisateur=request.user)
        except (Commande.DoesNotExist, ValueError):
            return Response({
                'error': 'Commande introuvable'
            }, status=status.HTTP_404_NOT_FOUND)
    
    # Vérifier qu'il n'y a pas déjà un paiement pour cette commande
    if hasattr(commande, 'payment'):
        return Response({
            'error': 'Un paiement existe déjà pour cette commande'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Créer le PaymentIntent avec Stripe
        intent = stripe.PaymentIntent.create(
            amount=int(commande.total_prix * 100),  # Stripe utilise les centimes
            currency=settings.STRIPE_CURRENCY,
            metadata={
                'commande_id': commande.id,
                'commande_reference': str(commande.reference),
                'user_id': request.user.id,
                'user_email': request.user.email,
            },
            automatic_payment_methods={
                'enabled': True,
            },
        )
        
        # Créer l'enregistrement Payment dans la base de données
        payment = Payment.objects.create(
            commande=commande,
            stripe_payment_intent_id=intent.id,
            stripe_client_secret=intent.client_secret,
            montant=commande.total_prix,
            devise=settings.STRIPE_CURRENCY,
            stripe_metadata=intent.metadata
        )
        
        return Response({
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id,
            'payment_id': payment.id,
            'amount': intent.amount,
            'currency': intent.currency,
        }, status=status.HTTP_201_CREATED)
        
    except stripe.error.StripeError as e:
        return Response({
            'error': f'Erreur Stripe: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Erreur serveur: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_status(request, payment_id):
    """
    Récupère le statut d'un paiement
    Accepte soit l'ID Django du Payment, soit le Stripe PaymentIntent ID
    """
    try:
        # Try to get payment by Django ID first, then by Stripe PaymentIntent ID
        try:
            payment = Payment.objects.get(id=int(payment_id), commande__utilisateur=request.user)
        except (Payment.DoesNotExist, ValueError):
            # If not found by Django ID, try by Stripe PaymentIntent ID
            payment = Payment.objects.get(stripe_payment_intent_id=payment_id, commande__utilisateur=request.user)
        
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)
    except Payment.DoesNotExist:
        return Response({
            'error': 'Paiement introuvable'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Erreur: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """
    Gère les webhooks Stripe
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        # Vérifier la signature du webhook
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return Response({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return Response({'error': 'Invalid signature'}, status=400)
    
    # Traiter l'événement
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_success(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failure(payment_intent)
    
    return Response({'status': 'success'})


def handle_payment_success(payment_intent):
    """
    Traite un paiement réussi
    """
    try:
        payment = Payment.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )
        
        with transaction.atomic():
            # Mettre à jour le statut du paiement
            payment.statut = Payment.STATUT_REUSSI
            payment.save()
            
            # Mettre à jour le statut de la commande
            commande = payment.commande
            commande.statut = Commande.STATUT_PAYEE
            commande.save()
            
            # Ajouter les tomes à la collection de l'utilisateur
            for item in commande.items.all():
                for _ in range(item.quantite):
                    item.tome.possesseurs.add(commande.utilisateur)
            
            # Vider le panier de l'utilisateur
            panier = get_or_create_panier(commande.utilisateur)
            panier.vider()
            
    except Payment.DoesNotExist:
        print(f"Payment not found for intent: {payment_intent['id']}")
    except Exception as e:
        print(f"Error handling payment success: {str(e)}")


def handle_payment_failure(payment_intent):
    """
    Traite un échec de paiement
    """
    try:
        payment = Payment.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )
        
        payment.statut = Payment.STATUT_ECHEC
        payment.save()
        
    except Payment.DoesNotExist:
        print(f"Payment not found for intent: {payment_intent['id']}")
    except Exception as e:
        print(f"Error handling payment failure: {str(e)}")