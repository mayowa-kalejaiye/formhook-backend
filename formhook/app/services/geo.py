"""
IP Geolocation utility for FormHook submissions.
Supports ipinfo.io and can be extended for other providers.
"""
import requests
from typing import Optional, Dict

IPINFO_URL = "https://ipinfo.io/{ip}/json"

# Optionally set your ipinfo.io token here
IPINFO_TOKEN = None  # e.g., 'your_token_here'

def get_geolocation(ip: str) -> Optional[Dict]:
    """
    Returns geolocation info for an IP address using ipinfo.io.
    Returns dict with country, region, city, loc, org, etc. or None on failure.
    """
    headers = {}
    params = {}
    if IPINFO_TOKEN:
        params['token'] = IPINFO_TOKEN
    try:
        resp = requests.get(IPINFO_URL.format(ip=ip), headers=headers, params=params, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'country': data.get('country'),
                'region': data.get('region'),
                'city': data.get('city'),
                'latitude': data.get('loc').split(',')[0] if data.get('loc') else None,
                'longitude': data.get('loc').split(',')[1] if data.get('loc') else None,
                'location_source': 'ipinfo.io',
                'org': data.get('org'),
                'raw': data
            }
    except Exception:
        pass
    return None

def extract_client_ip(request) -> str:
    """
    Extracts the real client IP from FastAPI request, considering proxy headers.
    """
    x_forwarded_for = request.headers.get('x-forwarded-for')
    if x_forwarded_for:
        # X-Forwarded-For may contain multiple IPs, take the first
        ip = x_forwarded_for.split(',')[0].strip()
        if ip:
            return ip
    x_real_ip = request.headers.get('x-real-ip')
    if x_real_ip:
        return x_real_ip.strip()
    # Fallback to request.client.host
    return request.client.host if hasattr(request, 'client') and request.client else None
