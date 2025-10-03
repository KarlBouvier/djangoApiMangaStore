from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.core.mail import send_mail
from secrets import choice
from string import digits

# Register your models here.
@admin.action(description="Envoyer un email promotionnel")
def send_promotional_email(modeladmin, request, queryset):
    sent_count = 0
    for user in queryset:
        if user.email: 
            promo_code = "MANGA" + "".join(choice(digits) for _ in range(5))

            subject = "🎉 Offre spéciale pour vous !"
            plain_message = (
                "Bonjour {},\n\n"
                "Profitez de notre promotion exclusive et utilisez ce code: {}\n\n"
                "Valable pour une durée limitée.\n\n"
                "— L'équipe Boutique Manga"
            ).format(user.username or "cher utilisateur", promo_code)

            html_message = f"""
            <div style="background:#f6f7fb;padding:24px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1f2937;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 10px 30px rgba(31,41,55,0.08);">
                <tr>
                  <td style="padding:0;">
                    <div style="background:linear-gradient(135deg,#7c3aed,#06b6d4);padding:28px 24px;color:#ffffff;">
                      <h1 style="margin:0;font-size:24px;line-height:1.3;">Offre spéciale rien que pour vous ✨</h1>
                      <p style="margin:8px 0 0;opacity:.95;">Salut {user.username or 'cher utilisateur'}, voici un petit cadeau.</p>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:28px 24px 8px;">
                    <p style="margin:0 0 14px;font-size:16px;">Utilisez ce code promotionnel et profitez d'une remise exclusive sur votre prochaine commande :</p>
                    <div style="display:inline-block;background:#111827;color:#ffffff;font-weight:700;letter-spacing:2px;padding:14px 18px;border-radius:10px;font-size:22px;">{promo_code}</div>
                    <p style="margin:16px 0 0;font-size:14px;color:#6b7280;">Valable pendant une durée limitée. Un seul usage par compte.</p>
                    <div style="margin:22px 0 8px;">
                      <a href="https://example.com/" style="display:inline-block;background:#7c3aed;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:600;box-shadow:0 6px 16px rgba(124,58,237,0.35);">J'en profite maintenant</a>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 24px 24px;">
                    <hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0;"/>
                    <p style="margin:0;color:#6b7280;font-size:13px;">Besoin d'aide ? Répondez simplement à cet email, on est là pour vous aider.</p>
                  </td>
                </tr>
              </table>
              <p style="text-align:center;color:#9ca3af;font-size:12px;margin:14px 0 0;">© {2025} Boutique Manga. Tous droits réservés.</p>
            </div>
            """

            send_mail(
                subject=subject,
                message=plain_message,
                from_email="karlbouvier04@gmail.com",
                recipient_list=[user.email],
                fail_silently=False,
                html_message=html_message,
            )
            sent_count += 1

    messages.success(request, f"{sent_count} email(s) envoyé(s) avec succès.")

class CustomUserAdmin(UserAdmin):
    actions = [send_promotional_email]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
