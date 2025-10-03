from rest_framework import serializers
from .models import Manga, Tome, Category, Commande, CommandeItem, Payment

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class MangaSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Manga
        fields = ['id', 'ref', 'nom', 'prix', 'nombre_tome', 'categories']


class CommandeItemSerializer(serializers.ModelSerializer):
    tome_nom = serializers.CharField(source='tome.manga.nom', read_only=True)
    tome_numero = serializers.IntegerField(source='tome.numero', read_only=True)
    
    class Meta:
        model = CommandeItem
        fields = ['id', 'tome', 'tome_nom', 'tome_numero', 'quantite', 'prix_unitaire', 'prix_total']


class CommandeSerializer(serializers.ModelSerializer):
    items = CommandeItemSerializer(many=True, read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    
    class Meta:
        model = Commande
        fields = ['id', 'reference', 'statut', 'statut_display', 'total_tomes', 'total_prix', 
                 'date_creation', 'date_modification', 'items']


class PaymentSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    commande_reference = serializers.CharField(source='commande.reference', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'stripe_payment_intent_id', 'stripe_client_secret', 'statut', 
                 'statut_display', 'montant', 'devise', 'date_creation', 'date_modification',
                 'commande_reference']


class CreatePaymentIntentSerializer(serializers.Serializer):
    """
    Serializer pour créer un PaymentIntent Stripe
    """
    commande_id = serializers.CharField()  # Changed to CharField to handle UUID strings
    
    def validate_commande_id(self, value):
        try:
            # Try to get commande by reference (UUID) first, then by id
            try:
                commande = Commande.objects.get(reference=value)
            except Commande.DoesNotExist:
                # Fallback to integer id if UUID doesn't work
                commande = Commande.objects.get(id=int(value))
            
            if commande.utilisateur != self.context['request'].user:
                raise serializers.ValidationError("Vous ne pouvez pas payer cette commande.")
            if commande.statut != Commande.STATUT_EN_ATTENTE:
                raise serializers.ValidationError("Cette commande ne peut pas être payée.")
            return value
        except (Commande.DoesNotExist, ValueError):
            raise serializers.ValidationError("Commande introuvable.")