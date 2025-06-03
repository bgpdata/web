from flask import Flask, render_template, request, redirect, url_for, abort, session, current_app as app, jsonify
from utils.text import time_ago, format_text, clean_text, alphanumeric_text, clean_text, sanitize_text, date_text
from flask_compress import Compress
from config import MainConfig as Config
from flask_cors import CORS
from flask_talisman import Talisman
from asgiref.wsgi import WsgiToAsgi
from utils.scheduler import scheduler
from utils.cache import cache, caching
from utils.limiter import limiter
from utils.jobs import example_job
from utils.seo import get_sitemap
from routes.asn import asn_blueprint
from datetime import timedelta
from logging import StreamHandler
import logging
import atexit
import sass # type: ignore
import sys
import re

def compile_scss():
    scss_file = 'static/styles/main.scss'
    css_file = 'static/styles/main.css'
    with open(css_file, 'w', -1, 'utf8') as f:
        f.write(sass.compile(filename=scss_file))

def add_header(response):
    if request.path.startswith('/static/'):
        response.cache_control.max_age = 86400
        response.cache_control.no_cache = None
        response.cache_control.public = True
    return response

def before_request():
    compile_scss()

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)

    # Configure logging
    # Remove any existing handlers
    app.logger.handlers = []
    
    # Create a new handler with explicit encoding
    handler = StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s +0000] [%(process)d] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    app.logger.addHandler(handler)
    
    if app.config['ENVIRONMENT'] == 'production':
        app.logger.setLevel(logging.WARNING)
    else:
        app.logger.setLevel(logging.DEBUG)

    # Initialize cache
    cache.init_app(app, config={'CACHE_TYPE': 'simple'})

    # Set secure session cookies
    app.config['SESSION_COOKIE_SECURE'] = app.config['ENVIRONMENT'] == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=90)
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True

    # Initialize CORS
    cors_origin = [
        'https://bgp-data.net',
        'http://localhost:8080',
        re.compile(r'^https?://100\.\d+\.\d+\.\d+(?::\d+)?(?:/.*)?$') # VPN 100.x.x.x
    ]

    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origin}},
        supports_credentials=True,
    )

    # Initialize Flask-Talisman
    if app.config['ENVIRONMENT'] == 'production':
        Talisman(
            app,
            content_security_policy=None,
            force_https=True,
            force_https_permanent=True
        )
    else:
        # Disable Talisman completely in development
        pass

    # Compile SCSS once on startup
    compile_scss()

    # Compress Application
    Compress(app)

    # Load i18n
    i18n = {}

    # Configure Cache Control
    app.after_request(add_header)
        
    # Compile SCSS before each request in development mode
    if app.config['ENVIRONMENT'] == 'development':
        app.before_request(before_request)
    
    
    """
    Jinja
    """

    app.jinja_env.filters['time_ago'] = time_ago
    app.jinja_env.filters['format'] = format_text
    app.jinja_env.filters['clean'] = clean_text
    app.jinja_env.filters['sanitize'] = sanitize_text
    app.jinja_env.filters['only_alphanumeric'] = alphanumeric_text
    app.jinja_env.filters['date_text'] = date_text

    # Context processor
    @app.context_processor
    def context():
        scripts = []
        def script(script):
            scripts.append(script)
            return ''
        return dict(script=script, environment=app.config['ENVIRONMENT'], i18n=i18n, scripts=lambda: scripts)

    """
    Scheduler
    """

    # Initialize scheduler
    scheduler.init_app(app)

    scheduler.add_job(id='example_job', func=example_job, priority=0, days=30)

    # Register scheduler shutdown
    atexit.register(lambda: scheduler.shutdown(wait=False))

    # Start scheduler
    scheduler.start()

    """
    SEO
    """

    def sitemap(generator_function, **kwargs):
        try:
            sitemap_xml = generator_function(**kwargs)
            return app.response_class(
                sitemap_xml,
                mimetype='application/xml'
            )
        except Exception as e:
            app.logger.error("Failed to generate sitemap: %s", str(e), exc_info=True)
            return abort(500, description="An error occurred while generating the sitemap")

    @app.route('/robots.txt')
    @caching(timeout=86400) # 24 hours
    def robots():
        return render_template('seo/robots.txt')

    @app.route('/sitemap.xsl')
    @caching(timeout=86400) # 24 hours
    def sitemap_xsl():
        return render_template('seo/sitemap.xsl')

    @app.route('/sitemap.xml')
    @caching(timeout=86400) # 24 hours
    def sitemap_xml():
        # Redirect to Sitemap Index (301: Permanent Redirect)
        return redirect(url_for('sitemap_index_xml'), code=301)

    @app.route('/sitemap_index.xml')
    @caching(timeout=86400) # 24 hours
    def sitemap_index_xml():
        return sitemap(get_sitemap)
    
    """
    REST API
    """

    @app.route('/api/v1/example', methods=['GET'])
    @limiter.limit("100 per minute")
    @caching(timeout=900) # Cache for 15 minutes
    def api_v1_example():
        try:
            # Example
            example = "Example"

            return jsonify({
                "example": example
            })

        except Exception as e:
            app.logger.error("Failed to get example: %s", str(e), exc_info=True)
            return abort(500, description="An error occurred")


    """
    Basic
    """


    @app.route('/')
    #@caching(timeout=86400) # 24 hours
    def index():
        try:
            example = "Example5"

        except Exception as e:
            app.logger.error("Failed to load index: %s", str(e), exc_info=True)
            return abort(500, description="An error occurred")

        return render_template('pages/index.html', example=example)


    # Register Blueprints
    app.register_blueprint(asn_blueprint, url_prefix='/asn')

    return app

# Create the ASGI app
asgi_app = WsgiToAsgi(create_app())