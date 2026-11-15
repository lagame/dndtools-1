"""Resolve visitor IPs only across a locally trusted reverse proxy."""

from ipaddress import ip_address
from functools import lru_cache
import socket
import time

from django.http import HttpRequest


@lru_cache(maxsize=1)
def _tunnel_peers(time_bucket):
    try:
        return {address[4][0] for address in socket.getaddrinfo(
            'tunnel_proxy', None, type=socket.SOCK_STREAM)}
    except socket.gaierror:
        return set()


def axes_client_ip(request):
    peer = request.META.get('REMOTE_ADDR', '')
    if peer not in {'127.0.0.1', '::1'} and peer not in _tunnel_peers(int(time.monotonic() // 30)):
        return None
    header = request.META.get('HTTP_CF_CONNECTING_IP', '')
    try:
        return str(ip_address(header.strip()))
    except ValueError:
        return None


def axes_lockout_parameters(request_or_attempt, credentials):
    if isinstance(request_or_attempt, HttpRequest):
        client_ip = axes_client_ip(request_or_attempt)
    else:
        client_ip = request_or_attempt.ip_address
    return ['username', 'ip_address'] if client_ip else ['username']
