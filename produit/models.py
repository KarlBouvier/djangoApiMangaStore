from django.db import models
from django.contrib.auth.models import User
import uuid
from django.core.exceptions import PermissionDenied
from utils.gcs import generate_signed_url
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Manga(models.Model):
    ref = models.UUIDField(editable=False, unique=True)
    nom = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    nombre_tome = models.IntegerField()
    categories = models.ManyToManyField('Category', related_name='mangas', blank=True)

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user is not None and not user.is_staff:
            raise PermissionDenied("Seuls les utilisateurs du staff peuvent ajouter ou modifier un manga.")

        is_new = self.pk is None
        if not self.ref:
            self.ref = uuid.uuid4()

        super().save(*args, **kwargs)

        current_count = self.tomes.count()

        if is_new:
            for i in range(1, self.nombre_tome + 1):
                Tome.objects.create(manga=self, numero=i)
        else:
            if self.nombre_tome > current_count:
                for i in range(current_count + 1, self.nombre_tome + 1):
                    Tome.objects.create(manga=self, numero=i)
            elif self.nombre_tome < current_count:
                self.tomes.filter(numero__gt=self.nombre_tome).delete()

    def __str__(self):
        return self.nom

class Tome(models.Model):
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name='tomes')
    numero = models.IntegerField()
    possesseurs = models.ManyToManyField(User, related_name='tomes_possedes', blank=True)
    cover = models.ImageField(upload_to='karlBouvier/', null=True, blank=True)

    def get_signed_cover_url(self, expiration_minutes=1):
        if self.cover:
            return generate_signed_url(f'{self.cover.name}', expiration_minutes=expiration_minutes)
        return None

    def __str__(self):
        return f"Tome {self.numero} de {self.manga.nom}"
    
class Panier(models.Model):
    """
    Modèle pour gérer le panier d'achat des utilisateurs
    """
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='panier')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Panier de {self.utilisateur.username}"
    
    @property
    def total_tomes(self):
        """Retourne le nombre total de tomes dans le panier"""
        return sum(item.quantite for item in self.items.all())
    
    @property
    def total_prix(self):
        """Retourne le prix total du panier"""
        return sum(item.prix_total for item in self.items.all())
    
    def ajouter_tome(self, tome, quantite=1):
        """Ajoute un tome au panier ou met à jour la quantité"""
        item, created = PanierItem.objects.get_or_create(
            panier=self,
            tome=tome,
            defaults={'quantite': quantite}
        )
        if not created:
            item.quantite += quantite
            item.save()

        item.save()
        return item
    
    def retirer_tome(self, tome):
        """Retire un tome du panier"""
        try:
            item = self.items.get(tome=tome)
            item.delete()
            return True
        except PanierItem.DoesNotExist:
            return False
    
    def vider(self):
        """Vide complètement le panier"""
        self.items.all().delete()

class PanierItem(models.Model):
    """
    Modèle pour les éléments individuels dans le panier
    """
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name='items')
    tome = models.ForeignKey(Tome, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['panier', 'tome']
    
    @property
    def prix_total(self):
        """Retourne le prix total pour cet item (tome * quantité)"""
        return self.tome.manga.prix * self.quantite
    
    def __str__(self):
        return f"{self.quantite}x {self.tome} dans le panier de {self.panier.utilisateur.username}"


class Commande(models.Model):
    """
    Modèle représentant une commande passée par un utilisateur
    """
    STATUT_EN_ATTENTE = 'pending'
    STATUT_PAYEE = 'paid'
    STATUT_EXPEDIEE = 'shipped'
    STATUT_ANNULEE = 'cancelled'

    STATUT_CHOICES = [
        (STATUT_EN_ATTENTE, 'En attente'),
        (STATUT_PAYEE, 'Payée'),
        (STATUT_EXPEDIEE, 'Expédiée'),
        (STATUT_ANNULEE, 'Annulée'),
    ]

    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commandes')
    reference = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_EN_ATTENTE)
    total_tomes = models.PositiveIntegerField(default=0)
    total_prix = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Commande {self.reference} de {self.utilisateur.username} ({self.get_statut_display()})"

    def recalculer_totaux(self):
        total_tomes = 0
        total_prix = 0
        for item in self.items.select_related('tome__manga').all():
            total_tomes += item.quantite
            total_prix += item.prix_total
        self.total_tomes = total_tomes
        self.total_prix = total_prix
        self.save(update_fields=['total_tomes', 'total_prix'])


class CommandeItem(models.Model):
    """
    Lignes d'une commande (snapshot au moment de l'achat)
    """
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='items')
    tome = models.ForeignKey(Tome, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def prix_total(self):
        return self.prix_unitaire * self.quantite

    def __str__(self):
        return f"{self.quantite}x {self.tome} (Commande {self.commande.reference})"


class Payment(models.Model):
    """
    Modèle pour gérer les paiements Stripe
    """
    STATUT_EN_ATTENTE = 'pending'
    STATUT_REUSSI = 'succeeded'
    STATUT_ECHEC = 'failed'
    STATUT_ANNULE = 'canceled'
    STATUT_REQUIRES_ACTION = 'requires_action'

    STATUT_CHOICES = [
        (STATUT_EN_ATTENTE, 'En attente'),
        (STATUT_REUSSI, 'Réussi'),
        (STATUT_ECHEC, 'Échec'),
        (STATUT_ANNULE, 'Annulé'),
        (STATUT_REQUIRES_ACTION, 'Action requise'),
    ]

    commande = models.OneToOneField(Commande, on_delete=models.CASCADE, related_name='payment')
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_client_secret = models.CharField(max_length=255)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_EN_ATTENTE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    devise = models.CharField(max_length=3, default='eur')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    stripe_metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Paiement {self.stripe_payment_intent_id} - {self.get_statut_display()}"


class StripeWebhookEvent(models.Model):
    """
    Modèle pour stocker les événements webhook Stripe
    """
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    data = models.JSONField()
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Webhook {self.stripe_event_id} - {self.event_type}"