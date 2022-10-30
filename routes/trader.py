from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from middlewares.verify_token_route import VerifyTokenRoute
from models.model import *
from models.bot import NewBot, UpdateBot, ActionBot, TradesBot, MetricsBot, TaskTicket
import pandas as pd
from config.dbmongo import DbBridge
import aiofiles
from worker.task import runTrader
from celery import Celery



trader_routes = APIRouter(route_class=VerifyTokenRoute)

conn = DbBridge(host="localhost", port=27017, auth=False)

@trader_routes.post("/upload")
async def upload_file(file: UploadFile=File(...)):
    try:
        async with aiofiles.open(f"./ml/{file.filename}", 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            out_file.close()
        return JSONResponse(content={"message":"Success Upload", "filename":file.filename},status_code=200)
    except Exception as e:
        return JSONResponse(content={"message":"Upload Error", "error":e},status_code=401)

@trader_routes.post("/new/bot")
async def new_bot(bot: NewBot):
    try:
        # if not exist register it in database
        new_bot = conn.saveBot(bot)
        conn.saveBot(bot)
        return JSONResponse(content={"message":"Success", "uuid": new_bot.uuid},status_code=200)
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/update/bot")
async def update_bot(bot: UpdateBot):
    try:
        if(conn.existBot(bot.uuid)):
            conn.updateBot(bot)
            edited_bot = conn.getBot(bot.uuid)
            return JSONResponse(content={"message":"Success", "bot": edited_bot},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/run/bot", response_model=TaskTicket)
async def run_bot(bot: ActionBot):
    try:
        if(conn.existBot(bot.uuid)):
            bot_item = conn.getBot(bot.uuid)
            #start bot
            task_id = runTrader.delay(bot_item)

            return JSONResponse(content={"message":"Success", "task_id": task_id},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/stop/bot")
async def stop_bot(bot: ActionBot):
    try:
        if(conn.existBot(bot.uuid)):
            #stop bot
            Celery.app.control.revoke(bot.task_id, terminate=True)
            return JSONResponse(content={"message":"Success", "status": "stopped"},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

        
@trader_routes.post("/status/bot")
async def status_bot(bot: ActionBot):
    try:
        if(conn.existBot(bot.uuid)):
            #stop bot
            result = conn.getBotStatus(bot.uuid)
            return JSONResponse(content={"message":"Success", "status": result},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/trades/bot")
async def trades_bot(bot: TradesBot):
    try:
        if(conn.existBot(bot.uuid)):
            trades = conn.getTradesBot(bot)
            return JSONResponse(content={"message":"Success", "trades": trades},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

@trader_routes.post("/metrics/bot")
async def metrics_bot(item: MetricsBot):
    try:
        if(conn.existBot(item.uuid)):
            bot = conn.getBot(item.uuid)

            # generate metrics

            metrics = ""

            return JSONResponse(content={"message":"Success", "metrics": metrics},status_code=200)
        else:
            return JSONResponse(content={"message":"Error", "error": "Not Found"},status_code=200)    
    except Exception as e:
        return JSONResponse(content={"message":"Error", "error":e},status_code=401)

