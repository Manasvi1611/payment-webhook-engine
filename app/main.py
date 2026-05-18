from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import init_db
from app.routers import deliveries, events, subscribers


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Payment Webhook Delivery Engine",
    description="A production-style webhook delivery system for payment events.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(events.router)
app.include_router(subscribers.router)
app.include_router(deliveries.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}
