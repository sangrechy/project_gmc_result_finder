import os
import socket

_original_getaddrinfo = socket.getaddrinfo
_is_patched = False

KNOWN_API_HOSTS = {
    "cms2api.tnmgrmu.ac.in": "14.139.177.26",
    "cms2results.tnmgrmuexam.ac.in": "14.139.177.26"
}

def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if isinstance(host, str):
        if host in KNOWN_API_HOSTS:
            return _original_getaddrinfo(KNOWN_API_HOSTS[host], port, socket.AF_INET, type, proto, flags)
        if family == 0 or family == socket.AF_UNSPEC:
            try:
                return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
            except socket.gaierror:
                pass
    return _original_getaddrinfo(host, port, family, type, proto, flags)

def patch_socket():
    global _is_patched
    if not _is_patched:
        socket.getaddrinfo = ipv4_getaddrinfo
        _is_patched = True

def unpatch_socket():
    global _is_patched
    if _is_patched:
        socket.getaddrinfo = _original_getaddrinfo
        _is_patched = False
