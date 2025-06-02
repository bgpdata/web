from flask import Config
import os

class Config(Config):
    # Flask
    HOST = os.getenv('FLASK_HOST')
    SECRET_KEY = os.getenv('SECRET_KEY')
    ENVIRONMENT = os.getenv('ENVIRONMENT')
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI')
    # Postgres
    POSTGRESQL_HOST = os.getenv('POSTGRESQL_HOST')
    POSTGRESQL_DB = os.getenv('POSTGRESQL_DB')
    POSTGRESQL_USER = os.getenv('POSTGRESQL_USER')
    POSTGRESQL_PASSWORD = os.getenv('POSTGRESQL_PASSWORD')
    # Postmark
    POSTMARK_API_KEY = os.getenv('POSTMARK_API_KEY')

    @staticmethod
    def validate():
        if not Config.HOST:
            raise ValueError("HOST is not set")
        if not Config.SECRET_KEY:
            raise ValueError("SECRET_KEY is not set")
        if not Config.ENVIRONMENT in ["production", "development"]:
            raise ValueError("ENVIRONMENT is not valid")
        if not Config.MONGODB_URI:
            raise ValueError("MONGODB_URI is not set")
        if not Config.POSTMARK_API_KEY:
            raise ValueError("POSTMARK_API_KEY is not set")
        if not Config.POSTGRESQL_HOST:
            raise ValueError("POSTGRESQL_HOST is not set")
        if not Config.POSTGRESQL_DB:
            raise ValueError("POSTGRESQL_DB is not set")
        if not Config.POSTGRESQL_USER:
            raise ValueError("POSTGRESQL_USER is not set")
        if not Config.POSTGRESQL_PASSWORD:
            raise ValueError("POSTGRESQL_PASSWORD is not set")