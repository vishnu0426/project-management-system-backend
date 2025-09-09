"""
Configuration settings for the Agno WorkSphere API
"""
import os


class Settings:
    """Application settings"""

    def __init__(self):
        # Load from environment variables with safe defaults
        self.app_name = os.getenv("APP_NAME", "Agno WorkSphere API")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "production")

        # Database - require DATABASE_URL in production
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL must be set")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Database Connection Pool Settings
        self.db_pool_min_size = int(os.getenv("DB_POOL_MIN_SIZE", "10"))
        self.db_pool_max_size = int(os.getenv("DB_POOL_MAX_SIZE", "20"))
        self.db_pool_max_queries = int(os.getenv("DB_POOL_MAX_QUERIES", "50000"))
        self.db_pool_max_inactive_time = int(os.getenv("DB_POOL_MAX_INACTIVE_TIME", "300"))

        # Redis Settings
        self.redis_max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
        self.cache_ttl = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default

        # Authentication - require JWT_SECRET in production
        self.jwt_secret = os.getenv("JWT_SECRET")
        if not self.jwt_secret:
            raise RuntimeError("JWT_SECRET must be set")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expires_in = int(os.getenv("JWT_EXPIRES_IN", "15"))  # minutes
        self.refresh_token_expires_in = int(os.getenv("REFRESH_TOKEN_EXPIRES_IN", "7"))  # days

        # Security
        self.bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
        self.password_min_length = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))

        # CORS - configure for dev and prod
        origins_str = os.getenv("ALLOWED_ORIGINS", "")
        if not origins_str:
            if self.environment == "production":
                raise RuntimeError("ALLOWED_ORIGINS must be set in production (comma-separated HTTPS URLs)")
            else:
                # Default dev origins
                origins_str = "http://localhost:3002,http://localhost:3000,http://localhost:3001"

        self.allowed_origins = [origin.strip() for origin in origins_str.split(',') if origin.strip()]

        # Rate Limiting
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

        # Email
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@agno-worksphere.com")
        self.from_name = os.getenv("FROM_NAME", "Agno WorkSphere")

        # File Upload
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
        file_types_str = os.getenv("ALLOWED_FILE_TYPES", "jpg,jpeg,png,gif,pdf,doc,docx,zip,rar")
        self.allowed_file_types = [file_type.strip() for file_type in file_types_str.split(',')]

        # AI Integration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.ai_enabled = os.getenv("AI_ENABLED", "True").lower() == "true"
        self.ai_prediction_enabled = os.getenv("AI_PREDICTION_ENABLED", "True").lower() == "true"
        self.ai_insights_enabled = os.getenv("AI_INSIGHTS_ENABLED", "True").lower() == "true"
        self.ai_smart_notifications = os.getenv("AI_SMART_NOTIFICATIONS", "True").lower() == "true"

        # Live Testing
        self.live_testing_mode = os.getenv("LIVE_TESTING_MODE", "False").lower() == "true"
        self.reset_db_on_start = os.getenv("RESET_DB_ON_START", "False").lower() == "true"
        self.demo_data_enabled = os.getenv("DEMO_DATA_ENABLED", "False").lower() == "true"

        # Local file storage for development
        self.upload_directory = os.getenv("UPLOAD_DIRECTORY", "uploads")

        # Monitoring and Observability
        self.enable_metrics = os.getenv("ENABLE_METRICS", "True").lower() == "true"
        self.enable_tracing = os.getenv("ENABLE_TRACING", "True").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = os.getenv("LOG_FORMAT", "json")

        # Performance Settings
        self.enable_gzip = os.getenv("ENABLE_GZIP", "True").lower() == "true"
        self.gzip_minimum_size = int(os.getenv("GZIP_MINIMUM_SIZE", "1000"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))

        # Health Check Settings
        self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
        self.health_check_timeout = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))


# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Global settings instance
settings = Settings()
