from fastapi import FastAPI
from routers import auth as auth_router
from routers import users as users_router
from routers import projects as projects_router
from routers import bids as bids_router
from routers import contracts as contracts_router
from routers import submissions as submissions_router
from routers import payments as payments_router
from routers import messaging as messaging_router
from routers import reviews as reviews_router
import uvicorn

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

def main():
    """Run the FastAPI application."""
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()

