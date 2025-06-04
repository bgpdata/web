import os

class BaseConfig:
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

class MainConfig(BaseConfig):
    # Flask
    FLASK_HOST = os.getenv('FLASK_HOST')
    SECRET_KEY = os.getenv('SECRET_KEY')

    # Postgres
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT')
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

    # Postmark
    POSTMARK_API_KEY = os.getenv('POSTMARK_API_KEY')

    @staticmethod
    def validate():
        required = {
            'ENVIRONMENT': MainConfig.ENVIRONMENT,
            'SECRET_KEY': MainConfig.SECRET_KEY,
            'FLASK_HOST': MainConfig.FLASK_HOST,
            'POSTMARK_API_KEY': MainConfig.POSTMARK_API_KEY,
            'POSTGRES_HOST': MainConfig.POSTGRES_HOST,
            'POSTGRES_PORT': MainConfig.POSTGRES_PORT,
            'POSTGRES_DB': MainConfig.POSTGRES_DB,
            'POSTGRES_USER': MainConfig.POSTGRES_USER,
            'POSTGRES_PASSWORD': MainConfig.POSTGRES_PASSWORD,
        }
        for key, val in required.items():
            if not val:
                raise ValueError(f"{key} is not set")


class RelayConfig(BaseConfig):
    HOST = os.getenv('HOST')
    OPENBMP_CONNECT = os.getenv('OPENBMP_CONNECT')

    @staticmethod
    def validate():
        required = {
            'HOST': RelayConfig.HOST,
            'OPENBMP_CONNECT': RelayConfig.OPENBMP_CONNECT,
        }
        for key, val in required.items():
            if not val:
                raise ValueError(f"{key} is not set")