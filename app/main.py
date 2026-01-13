from fastapi import FastAPI

from app.api.routers.users import router as users_router

app = FastAPI(title="FLUXPORT API")

app.include_router(users_router)


@app.get("/health")
def health():
    return {"status": "up"}
