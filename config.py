import os
import secrets
import datetime
import urllib.parse as parser


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    JWT_SECRET_KEY = os.environ.get(
        'JWT_SECRET_KEY') or secrets.token_urlsafe(32)
    JWT_EXPIRATION_DELTA = datetime.timedelta(hours=24)

    DB_USER = parser.quote_plus(os.environ.get('DB_USER', 'Rajat'))
    DB_PASSWORD = parser.quote_plus(os.environ.get('DB_PASSWORD', '2844'))
    DB_CLUSTER = os.environ.get('DB_CLUSTER', 'cluster0.gpq2duh')
    MONGO_URI = f"mongodb+srv://{DB_USER}:{DB_PASSWORD}@{DB_CLUSTER}.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = DevelopmentConfig()
