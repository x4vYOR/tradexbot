from fastapi import FastAPI
from dotenv import load_dotenv
from routes.auth import auth_routes
from routes.trader import trader_routes
from routes.data import data_routes

app = FastAPI()


app.include_router(auth_routes, prefix="/api")
app.include_router(trader_routes, prefix="/api")
app.include_router(data_routes, prefix="/api")
load_dotenv()