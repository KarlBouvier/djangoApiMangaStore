from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import Commande


def _build_commande_email_content(commande: Commande):
    user = commande.utilisateur

    recap_items_html = ""
    recap_items_text = ""
    for item in commande.items.select_related('tome__manga').all():
        manga_nom = item.tome.manga.nom
        tome_numero = item.tome.numero
        quantite = item.quantite
        prix_unitaire = float(item.prix_unitaire)
        prix_total = float(item.prix_total)

        recap_items_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px; text-align: left;">{manga_nom}</td>
                <td style="padding: 10px; text-align: center;">Tome {tome_numero}</td>
                <td style="padding: 10px; text-align: center;">{quantite}</td>
                <td style="padding: 10px; text-align: right;">{prix_unitaire:.2f}€</td>
                <td style="padding: 10px; text-align: right; font-weight: bold;">{prix_total:.2f}€</td>
            </tr>
        """

        recap_items_text += (
            f"- {manga_nom} - Tome {tome_numero} (x{quantite}) : {prix_total:.2f}€\n"
        )

    subject = f"Confirmation de commande - {user.username}"

    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #28a745; text-align: center;">✅ Commande confirmée !</h2>
            <p>Bonjour <strong>{user.username}</strong>,</p>
            <p>Votre commande a été traitée avec succès. Merci pour votre achat !</p>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #333;">Détails de la commande</h3>
                <p><strong>Client :</strong> {user.username}</p>
                <p><strong>Email :</strong> {user.email}</p>
                <p><strong>Date :</strong> {timezone.now().strftime('%d/%m/%Y à %H:%M')}</p>
                <p><strong>Statut :</strong> <span style="color: #28a745; font-weight: bold;">Confirmée</span></p>
            </div>
            <div style="background: white; border: 1px solid #ddd; border-radius: 5px; margin: 20px 0; overflow: hidden;">
                <h3 style="background: #0b1020; color: white; margin: 0; padding: 15px; text-align: center;">📚 Récapitulatif de votre commande</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Manga</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Tome</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Qté</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Prix unit.</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {recap_items_html}
                    </tbody>
                    <tfoot>
                        <tr style="background: #e9ecef; font-weight: bold;">
                            <td colspan="4" style="padding: 15px; text-align: right; border-top: 2px solid #007bff;">Total général :</td>
                            <td style="padding: 15px; text-align: right; border-top: 2px solid #007bff; color: #28a745; font-size: 1.1em;">{float(commande.total_prix):.2f}€</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            <p style="text-align: center; margin-top: 30px;">
                <a href="http://127.0.0.1:8000/home/recherche/" 
                   style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    🛍️ Continuer mes achats
                </a>
            </p>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="text-align: center; color: #666; font-size: 14px;">
                Merci de votre confiance !<br>
                L'équipe Manga Collection
            </p>
        </div>
    </body>
    </html>
    """

    plain_message = f"""
    Bonjour {user.username},

    Votre commande a été traitée avec succès. Merci pour votre achat !

    Détails de la commande :
    - Client : {user.username}
    - Email : {user.email}
    - Date : {timezone.now().strftime('%d/%m/%Y à %H:%M')}
    - Statut : Confirmée

    Récapitulatif de votre commande :
    {recap_items_text}
    Total général : {float(commande.total_prix):.2f}€

    Prochaines étapes :
    - Vos tomes seront ajoutés à votre collection
    - Vous pouvez continuer à explorer notre catalogue
    - N'hésitez pas à nous contacter pour toute question

    Merci de votre confiance !
    L'équipe Manga Collection
    """

    return subject, plain_message, html_message, user.email


@receiver(post_save, sender=Commande)
def envoyer_email_confirmation_commande(sender, instance: Commande, created: bool, **kwargs):
    if not created:
        return
    if instance.statut != Commande.STATUT_PAYEE:
        return

    def _send():
        subject, plain_message, html_message, user_email = _build_commande_email_content(instance)
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email="karlbouvier04@gmail.com",
                recipient_list=[user_email],
                html_message=html_message,
                fail_silently=False,
            )
            print(f"✅ Email de confirmation envoyé à {instance.utilisateur.email}")
        except Exception as exc:
            print(f"❌ Erreur lors de l'envoi de l'email: {exc}")

    transaction.on_commit(_send)


