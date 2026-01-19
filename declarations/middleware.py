"""
Zahnovia Middleware
Profil tamamlama kontrolü için
"""
from django.shortcuts import redirect
from django.urls import reverse


class ProfileCompletionMiddleware:
    """
    Kullanıcının profil bilgilerini tamamlamasını zorunlu kılan middleware.
    Email doğrulanmış ama profil tamamlanmamış kullanıcıları profile_edit sayfasına yönlendirir.
    """

    # Bu URL'lere profil tamamlanmadan da erişilebilir
    EXEMPT_URLS = [
        '/login/',
        '/logout/',
        '/register/',
        '/verify-email/',
        '/password-reset/',
        '/profile/edit/',
        '/admin/',
        '/static/',
        '/media/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Önce muaf URL'leri kontrol et
        path = request.path
        for exempt_url in self.EXEMPT_URLS:
            if path.startswith(exempt_url):
                return self.get_response(request)

        # Kullanıcı giriş yapmış mı kontrol et
        if request.user.is_authenticated and not request.user.is_superuser:
            try:
                profile = request.user.hersteller_profile

                # Email doğrulanmış ama profil tamamlanmamış mı?
                if profile.email_verified and not profile.profile_completed:
                    return redirect('profile_edit')

            except AttributeError:
                # Profil yoksa oluştur ve yönlendir
                from .models import HerstellerProfile
                HerstellerProfile.objects.get_or_create(user=request.user)
                return redirect('profile_edit')

        return self.get_response(request)
