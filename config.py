import os
import secrets
import datetime
import urllib.parse as parser

class Config:
    """Base configuration class."""
    # It's a best practice to load secrets from environment variables
    # For now, we will keep them here for simplicity.
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or secrets.token_urlsafe(32)
    JWT_EXPIRATION_DELTA = datetime.timedelta(hours=24)

    # Database Configuration
    DB_USER = parser.quote_plus(os.environ.get('DB_USER', 'Rajat'))
    DB_PASSWORD = parser.quote_plus(os.environ.get('DB_PASSWORD', '2844'))
    DB_CLUSTER = os.environ.get('DB_CLUSTER', 'cluster0.gpq2duh')
    MONGO_URI = f"mongodb+srv://{DB_USER}:{DB_PASSWORD}@{DB_CLUSTER}.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

# You can switch between configs based on an environment variable
config = DevelopmentConfig()
