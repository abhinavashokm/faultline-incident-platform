from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INCIDENT_", env_file=".env", extra="ignore")

    database_url: str


class Settings(DatabaseSettings):
    control_plane_url: AnyHttpUrl
    processing_url: AnyHttpUrl
