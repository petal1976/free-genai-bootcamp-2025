from flask import Flask, g
from flask_cors import CORS
import sqlite3

from lib.db import Db

import routes.words
import routes.groups
import routes.study_sessions
import routes.dashboard
import routes.study_activities

def get_db(app):
    if not hasattr(g, 'db'):
        g.db = sqlite3.connect(app.config['DATABASE'], check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

def get_allowed_origins(app):
    try:
        with app.app_context():
            cursor = app.db.cursor()
            cursor.execute('SELECT url FROM study_activities')
            urls = cursor.fetchall()
            # Convert URLs to origins
            origins = set()
            for url in urls:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url['url'])
                    origin = f"{parsed.scheme}://{parsed.netloc}"
                    origins.add(origin)
                except:
                    continue
            return list(origins) if origins else ["*"]
    except:
        return ["*"]

def create_app(test_config=None):
    app = Flask(__name__)
    
    if test_config is None:
        # Normal configuration
        app.config.from_pyfile('config.py', silent=True)
        app.config['DATABASE'] = 'words.db'
        # Create production database connection
        app.db = sqlite3.connect(app.config['DATABASE'], check_same_thread=False)
        app.db.row_factory = sqlite3.Row
    else:
        # Test configuration
        app.config.update(test_config)
        if 'DATABASE' in test_config:
            app.db = sqlite3.connect(test_config['DATABASE'], check_same_thread=False)
            app.db.row_factory = sqlite3.Row
    
    # Get allowed origins from study_activities table
    allowed_origins = get_allowed_origins(app)
    allowed_origins.extend(["http://localhost:5173"])
    
    # In development, add localhost to allowed origins
    if app.debug:
        allowed_origins.extend(["http://localhost:8080", "http://127.0.0.1:8080"])
    
    # Configure CORS with combined origins
    CORS(app, resources={
        r"/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # load routes
    routes.words.load(app)
    routes.groups.load(app)
    routes.study_sessions.load(app)
    routes.dashboard.load(app)
    routes.study_activities.load(app)
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)