import sys
from pathlib import Path

# Add project root directory to sys.path so all imports resolve seamlessly
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app

class VercelPathFixMiddleware:
    """
    Vercel internal rewrites forward requests to /api/index.
    This middleware transparently restores the original request path so Flask routes match accurately.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Check raw/forwarded URI headers provided by Vercel Edge proxy
        forwarded = (
            environ.get('HTTP_X_FORWARDED_URI') or
            environ.get('HTTP_X_FORWARDED_URL') or
            environ.get('HTTP_X_NOW_ROUTE_MATCHES') or
            environ.get('REQUEST_URI') or
            environ.get('RAW_URI')
        )
        if forwarded:
            clean_path = forwarded.split('?')[0]
            if clean_path and not clean_path.startswith('/api/index'):
                environ['PATH_INFO'] = clean_path

        # 2. Normalize /api/index root and subpaths
        path = environ.get('PATH_INFO', '')
        if path in ('/api/index', '/api/index/'):
            environ['PATH_INFO'] = '/'
        elif path.startswith('/api/index/'):
            environ['PATH_INFO'] = path[len('/api/index'):]

        return self.wsgi_app(environ, start_response)

# Attach middleware to the Flask WSGI handler while exposing 'app' as the Flask instance
app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)
