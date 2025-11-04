from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "rt-collab"


def get_settings() -> Settings:
    return Settings()
