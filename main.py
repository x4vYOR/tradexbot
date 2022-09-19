from fastapi import FastAPI
from dotenv import load_dotenv
from routes.auth import auth_routes
from routes.model import model_routes
from routes.data import data_routes

app = FastAPI()
app.include_router(auth_routes, prefix="/api")
app.include_router(model_routes, prefix="/api")
app.include_router(data_routes, prefix="/api")
load_dotenv()