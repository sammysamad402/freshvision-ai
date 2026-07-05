"""
Shared rate-limiter instance.

Defined in its own module (rather than inside main.py) so route files like
app/routes/auth.py can apply @limiter.limit(...) to specific endpoints
(e.g. tighter limits on /login and /register to blunt brute-force and
mass-registration attempts) without causing circular imports with main.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import RATE_LIMIT_DEFAULT

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_DEFAULT])
