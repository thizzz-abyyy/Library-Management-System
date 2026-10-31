import sys
from pathlib import Path

# Add project root directory to sys.path so all imports resolve seamlessly
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app as flask_app

class VercelPathFixMiddleware:
    """
    Vercel internal rewrites often forward requests to /api/index or /api/index/<path>.
    This middleware transparently restores the original request path so Flask routes match accurately.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        
        # Check if Vercel set forwarded URI header
        forwarded = environ.get('HTTP_X_FORWARDED_URI') or environ.get('HTTP_X_MATCHED_PATH')
        if forwarded and not forwarded.startswith('/api/index'):
            environ['PATH_INFO'] = forwarded.split('?')[0]
        elif path == '/api/index' or path == '/api/index/':
            environ['PATH_INFO'] = '/'
        elif path.startswith('/api/index/'):
            environ['PATH_INFO'] = path[len('/api/index'):]

        return self.wsgi_app(environ, start_response)

# Expose 'app' as the WSGI callable for Vercel Serverless Function
app = VercelPathFixMiddleware(flask_app)
