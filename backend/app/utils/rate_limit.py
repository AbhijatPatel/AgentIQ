"""
Shared rate limiter instance.

A single Limiter instance must be used both for app.state.limiter
(registered in main.py) and for any @limiter.limit(...) decorators
on individual routes - otherwise they're disconnected and rate
limiting silently doesn't work.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)