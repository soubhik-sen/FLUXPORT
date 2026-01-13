from pydantic import BaseModel


class Settings(BaseModel):
    # Change this to your real creds/db later (or move to env vars)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fluxport"


settings = Settings()
