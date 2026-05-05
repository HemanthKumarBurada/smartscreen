from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/smartscreen_db"
    SECRET_KEY: str = "change-this-secret"
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = "SmartScreen"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    WHISPER_MODEL: str = "base"
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()
