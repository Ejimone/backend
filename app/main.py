from fastapi import FastAPI
from app.routers import auth as auth_router
from app.routers import users as users_router
from app.routers import projects as projects_router
from app.routers import bids as bids_router
from app.routers import contracts as contracts_router
from app.routers import submissions as submissions_router
from app.routers import payments as payments_router
from app.routers import messaging as messaging_router
from app.routers import reviews as reviews_router

app = FastAPI()

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(projects_router.router)
app.include_router(bids_router.router)
app.include_router(contracts_router.router)
app.include_router(submissions_router.router)
app.include_router(payments_router.router)
app.include_router(messaging_router.router)
app.include_router(reviews_router.router)

@app.get("/")
async def root():
    return {"message": "Welcome to College E-commerce and Freelancing App"}
