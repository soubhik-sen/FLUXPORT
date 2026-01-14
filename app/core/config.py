from pydantic import BaseModel
import os


class Settings(BaseModel):
    # Change this to your real creds/db later (or move to env vars)
    DATABASE_URL: str =  os.getenv("DATABASE_URL", "postgresql://admin:0kpy04n0HoOIjYN9TOJGKzMP3tEZiuk7@dpg-d5jv5tt6ubrc7398ucg0-a.oregon-postgres.render.com/commexwise_1jak")


settings = Settings()
