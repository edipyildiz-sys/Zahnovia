"""
Zahnovia Email Servisi
Kayıt doğrulama ve şifre sıfırlama emailleri için
"""
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings


class EmailService:
    """Base email service"""

    @staticmethod
    def send_email(subject, message, recipient_list, html_message=None):
        """Send email with optional HTML content"""
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Email gönderme hatası: {str(e)}")
            return False


class RegistrationEmailService(EmailService):
    """Kayıt işlemleri için email servisi"""

    @staticmethod
    def send_verification_email(user, profile, verification_url):
        """Email doğrulama linki gönder"""
        subject = "Bestätigen Sie Ihre E-Mail-Adresse - Zahnovia"

        message = f"""
Sehr geehrte/r {user.first_name} {user.last_name},

vielen Dank für Ihre Registrierung bei Zahnovia.

Bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie auf den folgenden Link klicken:

{verification_url}

Dieser Link ist 24 Stunden gültig.

Falls Sie sich nicht bei Zahnovia registriert haben, ignorieren Sie diese E-Mail bitte.

Mit freundlichen Grüßen,
Ihr Zahnovia Team
        """

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #17a2b8, #138496); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .btn {{ display: inline-block; background: #17a2b8; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
        .btn:hover {{ background: #138496; }}
        .footer {{ margin-top: 20px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Willkommen bei Zahnovia!</h1>
        </div>
        <div class="content">
            <p>Sehr geehrte/r {user.first_name} {user.last_name},</p>
            <p>vielen Dank für Ihre Registrierung bei Zahnovia.</p>
            <p>Bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie auf den folgenden Button klicken:</p>
            <p style="text-align: center;">
                <a href="{verification_url}" class="btn">E-Mail bestätigen</a>
            </p>
            <p><small>Oder kopieren Sie diesen Link in Ihren Browser:<br>{verification_url}</small></p>
            <p><strong>Dieser Link ist 24 Stunden gültig.</strong></p>
            <p>Falls Sie sich nicht bei Zahnovia registriert haben, ignorieren Sie diese E-Mail bitte.</p>
            <p>Mit freundlichen Grüßen,<br>Ihr Zahnovia Team</p>
        </div>
        <div class="footer">
            <p>Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht darauf.</p>
        </div>
    </div>
</body>
</html>
        """

        return EmailService.send_email(
            subject=subject,
            message=message,
            recipient_list=[user.email],
            html_message=html_message
        )

    @staticmethod
    def send_admin_notification(user, profile):
        """Admin'e yeni kayıt bildirimi gönder"""
        admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', None)
        if not admin_email:
            return False

        subject = f"Neue Registrierung - {user.username}"
        message = f"""
Neue Benutzerregistrierung bei Zahnovia:

Benutzername: {user.username}
E-Mail: {user.email}
Name: {user.first_name} {user.last_name}
Registrierungsdatum: {user.date_joined.strftime('%d.%m.%Y %H:%M')}
        """

        return EmailService.send_email(
            subject=subject,
            message=message,
            recipient_list=[admin_email]
        )


class PasswordResetEmailService(EmailService):
    """Şifre sıfırlama için email servisi"""

    @staticmethod
    def send_password_reset_email(user, reset_url):
        """Şifre sıfırlama linki gönder"""
        subject = "Passwort zurücksetzen - Zahnovia"

        message = f"""
Sehr geehrte/r {user.first_name} {user.last_name},

Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt.

Klicken Sie auf den folgenden Link, um ein neues Passwort festzulegen:

{reset_url}

Dieser Link ist 24 Stunden gültig.

Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail bitte.
Ihr Passwort wird nicht geändert.

Mit freundlichen Grüßen,
Ihr Zahnovia Team
        """

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #17a2b8, #138496); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .btn {{ display: inline-block; background: #17a2b8; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
        .btn:hover {{ background: #138496; }}
        .footer {{ margin-top: 20px; text-align: center; color: #666; font-size: 12px; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 6px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Passwort zurücksetzen</h1>
        </div>
        <div class="content">
            <p>Sehr geehrte/r {user.first_name} {user.last_name},</p>
            <p>Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt.</p>
            <p>Klicken Sie auf den folgenden Button, um ein neues Passwort festzulegen:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="btn">Neues Passwort festlegen</a>
            </p>
            <p><small>Oder kopieren Sie diesen Link in Ihren Browser:<br>{reset_url}</small></p>
            <p><strong>Dieser Link ist 24 Stunden gültig.</strong></p>
            <div class="warning">
                <strong>Hinweis:</strong> Falls Sie diese Anfrage nicht gestellt haben,
                ignorieren Sie diese E-Mail bitte. Ihr Passwort wird nicht geändert.
            </div>
            <p>Mit freundlichen Grüßen,<br>Ihr Zahnovia Team</p>
        </div>
        <div class="footer">
            <p>Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht darauf.</p>
        </div>
    </div>
</body>
</html>
        """

        return EmailService.send_email(
            subject=subject,
            message=message,
            recipient_list=[user.email],
            html_message=html_message
        )
