from fastapi import FastAPI
from dotenv import load_dotenv
from routes.auth import auth_routes
from routes.trader import trader_routes
from routes.data import data_routes
from fastapi.staticfiles import StaticFiles

app = FastAPI()


def mount_data(app):
    app.mount(
        "/backtest",
        StaticFiles(directory="train/backtest"),
        name="charts",
    )

app.include_router(auth_routes, prefix="/api")
app.include_router(trader_routes, prefix="/api")
app.include_router(data_routes, prefix="/api")

mount_data(app)

load_dotenv()