from pydantic import BaseModel
import os


class Settings(BaseModel):
    # Change this to your real creds/db later (or move to env vars)
    DATABASE_URL: str =  os.getenv("DATABASE_URL", "postgresql://admin:3clQeR42BY90a2BWXi5YGLwwZO2qVvpt@dpg-d5jn5lili9vc73bikmlg-a.oregon-postgres.render.com/commexwise")


settings = Settings()
