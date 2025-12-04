from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Karp DB"
    API_V1_STR: str = "/api/v1"
    MONGODB_URL: str
    DATABASE_NAME: str = "newest_karp_db"
    SECRET_KEY: str = "karp"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    GOOGLE_MAPS_KEY: str
    AWS_S3_BUCKET_NAME: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    REDIS_URL: str
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()
