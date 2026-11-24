from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/gimnasio"
    zona_horaria: str = "America/Lima"
    dias_por_vencer: int = 5
    cors_origins: str = "http://localhost:5173"


settings = Settings()
