import os

class Config():
    # Flask
    FLASK_HOST = os.getenv('FLASK_HOST')
    SECRET_KEY = os.getenv('SECRET_KEY')

    # Kafka
    KAFKA_FQDN = os.getenv('KAFKA_FQDN')
    KAFKA_JMX_FQDN = os.getenv('KAFKA_JMX_FQDN')

    # Postgres
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT')
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

    # Postmark
    POSTMARK_API_KEY = os.getenv('POSTMARK_API_KEY')
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO' if ENVIRONMENT == 'production' else 'DEBUG').upper()

    @staticmethod
    def validate():
        required = {
            'ENVIRONMENT': Config.ENVIRONMENT,
            'SECRET_KEY': Config.SECRET_KEY,
            'FLASK_HOST': Config.FLASK_HOST,
            'KAFKA_FQDN': Config.KAFKA_FQDN,
            'KAFKA_JMX_FQDN': Config.KAFKA_JMX_FQDN,
            'POSTMARK_API_KEY': Config.POSTMARK_API_KEY,
            'POSTGRES_HOST': Config.POSTGRES_HOST,
            'POSTGRES_PORT': Config.POSTGRES_PORT,
            'POSTGRES_DB': Config.POSTGRES_DB,
            'POSTGRES_USER': Config.POSTGRES_USER,
            'POSTGRES_PASSWORD': Config.POSTGRES_PASSWORD,
        }
        for key, val in required.items():
            if not val:
                raise ValueError(f"{key} is not set")