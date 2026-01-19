# declarations/gmail_backend.py
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def _build_service():
    creds = Credentials(
        token=None,  # access token yok; refresh ile alınacak
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
    )
    # access token'ı yenile
    creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)

class GmailApiEmailBackend(BaseEmailBackend):
    """
    Django EmailBackend uyumlu: EmailMessage objelerini Gmail API ile yollar.
    .env'de:
      GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
      DEFAULT_FROM_EMAIL
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = _build_service()

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        print(f"DEBUG: Sending {len(email_messages)} messages")
        sent_count = 0
        for message in email_messages:
            try:
                raw = self._build_raw(message)
                self.service.users().messages().send(userId='me', body={'raw': raw}).execute()
                sent_count += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
        return sent_count

    def _build_raw(self, message):
        from email.mime.base import MIMEBase
        from email import encoders

        # from, to, subject, body (text veya html) ayarla
        from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
        to_list = list(message.to or [])
        print(f"DEBUG Gmail: from={from_email}, to={to_list}")
        cc_list = list(message.cc or [])
        bcc_list = list(message.bcc or [])

        # Attachments varsa MIMEMultipart('mixed') kullan
        has_attachments = bool(message.attachments)
        has_html = bool(getattr(message, 'alternatives', []))

        if has_attachments:
            # Ana container: mixed (body + attachments için)
            mime = MIMEMultipart('mixed')

            # Body için alt-container oluştur
            if has_html:
                body_part = MIMEMultipart('alternative')
                body_part.attach(MIMEText(message.body, 'plain', _charset='utf-8'))
                for content, mimetype in message.alternatives:
                    if mimetype == 'text/html':
                        body_part.attach(MIMEText(content, 'html', _charset='utf-8'))
                mime.attach(body_part)
            else:
                mime.attach(MIMEText(message.body, 'plain', _charset='utf-8'))

            # Attachments ekle
            for attachment in message.attachments:
                if isinstance(attachment, MIMEBase):
                    mime.attach(attachment)
                else:
                    from email.header import Header
                    filename, content, mimetype = attachment
                    main_type, sub_type = mimetype.split('/', 1)
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(content)
                    encoders.encode_base64(part)

                    # Dosya ismini UTF-8 olarak encode et
                    # Header encoding kullanarak Almanca karakterleri düzgün göster
                    try:
                        # Önce ASCII olarak dene
                        filename.encode('ascii')
                        # ASCII ise direkt kullan
                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                    except UnicodeEncodeError:
                        # ASCII değilse, RFC 2231 tuple format kullan
                        # Tuple: (charset, language, value) - value string olmalı
                        part.add_header(
                            'Content-Disposition',
                            'attachment',
                            filename=('utf-8', '', filename)  # filename string olarak
                        )

                    mime.attach(part)
                    # Windows console emoji sorunu için try-except ekle
                    try:
                        print(f"  Attachment added: {filename}")
                    except UnicodeEncodeError:
                        print(f"  [*] Attachment added: {filename}")
        else:
            # Attachments yok, eski mantık
            if has_html:
                mime = MIMEMultipart('alternative')
                mime.attach(MIMEText(message.body, 'plain', _charset='utf-8'))
                for content, mimetype in message.alternatives:
                    if mimetype == 'text/html':
                        mime.attach(MIMEText(content, 'html', _charset='utf-8'))
            else:
                mime = MIMEText(message.body, 'plain', _charset='utf-8')

        mime['From'] = from_email
        mime['To'] = ", ".join(to_list)
        if cc_list:
            mime['Cc'] = ", ".join(cc_list)
        mime['Subject'] = message.subject

        # Gmail API: base64url encode
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode('utf-8')
        return raw
