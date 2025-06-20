from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request, current_app as app

limiter = Limiter(
    app=app,
    key_func=lambda: None if request.remote_addr == '127.0.0.1' else get_remote_address(),
    default_limits=["20 per minute"],
    storage_uri="memory://",
    strategy="fixed-window"
)