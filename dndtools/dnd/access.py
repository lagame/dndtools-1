"""Bind Django admin sessions to a verified Cloudflare Access identity."""

from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse


@lru_cache(maxsize=4)
def _jwk_client(team_domain):
    parsed = urlsplit(team_domain)
    if (parsed.scheme != 'https' or parsed.path or parsed.query or parsed.fragment
            or not parsed.hostname or not parsed.hostname.endswith('.cloudflareaccess.com')):
        raise ValueError('Invalid Access team domain configuration.')
    return jwt.PyJWKClient(team_domain + '/cdn-cgi/access/certs', cache_jwk_set=True,
                           lifespan=300, timeout=3)


def verified_email(token):
    if not token or len(token) > 12000:
        return None
    try:
        key = _jwk_client(settings.ACCESS_TEAM_DOMAIN).get_signing_key_from_jwt(token)
        payload = jwt.decode(token, key.key, algorithms=['RS256'],
                             audience=settings.ACCESS_AUD,
                             issuer=settings.ACCESS_TEAM_DOMAIN,
                             options={'require': ['exp', 'iss', 'aud', 'email']})
        email = payload.get('email', '')
        return email.casefold() if isinstance(email, str) and '@' in email else None
    except (jwt.PyJWTError, ValueError, OSError):
        return None


class AccessIdentityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.ACCESS_REQUIRED or not request.path_info.startswith('/' + settings.ADMIN_URL):
            return self.get_response(request)
        email = verified_email(request.META.get('HTTP_CF_ACCESS_JWT_ASSERTION'))
        if not email:
            return HttpResponseForbidden('Access authentication required.')
        request.access_email = email
        if request.user.is_authenticated and request.user.email.casefold() != email:
            logout(request)
            return HttpResponseForbidden('Access account does not match this session.')
        if email == settings.ADMINS[0][1].casefold():
            accounts = list(get_user_model().objects.filter(email__iexact=email).order_by('pk')[:2])
            if len(accounts) != 1:
                if request.user.is_authenticated:
                    logout(request)
                return HttpResponseForbidden('Owner Access identity is ambiguous.')
            account = accounts[0]
            if (account.username != settings.ADMINS[0][0] or not account.is_active or
                    not account.is_staff or not account.is_superuser):
                if request.user.is_authenticated:
                    logout(request)
                return HttpResponseForbidden('Owner account is not active.')
            if request.user.is_authenticated and request.user.pk != account.pk:
                logout(request)
                return HttpResponseForbidden('Access account does not match this session.')
            if not request.user.is_authenticated and request.method in ('GET', 'HEAD'):
                login(request, account, backend='django.contrib.auth.backends.ModelBackend')
        else:
            from dnd.models import CollaboratorInvite
            accounts = list(get_user_model().objects.filter(email__iexact=email).order_by('pk')[:2])
            if len(accounts) != 1:
                return HttpResponseForbidden('No editorial invitation for this Access identity.')
            account = accounts[0]
            invite = CollaboratorInvite.objects.filter(user=account).first()
            if not invite or account.is_superuser:
                return HttpResponseForbidden('No editorial invitation for this Access identity.')
            if invite.access_state == 'pending':
                if request.user.is_authenticated:
                    logout(request)
                if request.path_info != reverse('editorial_activate'):
                    return redirect('editorial_activate')
            elif (invite.access_state != 'active' or not account.is_active or
                  not account.is_staff or
                  (request.user.is_authenticated and request.user.pk != account.pk)):
                if request.user.is_authenticated:
                    logout(request)
                return HttpResponseForbidden('Editorial access is not active.')
            elif not request.user.is_authenticated and request.method in ('GET', 'HEAD'):
                login(request, account, backend='django.contrib.auth.backends.ModelBackend')
        response = self.get_response(request)
        if request.user.is_authenticated and request.user.email.casefold() != email:
            logout(request)
            return HttpResponseForbidden('Access account does not match this session.')
        return response
