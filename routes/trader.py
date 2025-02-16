from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from middlewares.verify_token_route import VerifyTokenRoute
from models.model import *
from models.bot import NewBot, UpdateBot, ActionBot, TradesBot, MetricsBot, TaskTicket, TradesPair, StatusTrain, NewTrain, StopTrain
from config.dbmongo import DbBridge
import aiofiles
from worker.task import runTrader, runTrainer, worker
from celery.contrib.abortable import AbortableAsyncResult
import ast
from os import getenv

trader_routes = APIRouter(route_class=VerifyTokenRoute)

conn = DbBridge(password=getenv("MONGO_PASSWORD"), auth = True) #DbBridge(host="localhost", port=27017, auth=False)

@trader_routes.post("/run/train")
async def run_train(new_train: NewTrain):
    new_train = jsonable_encoder(new_train)
    try:
        # save new train status {checksum, status, result}
        print("## Save train")
        if(conn.saveTrain({"config":new_train["config_params"], "checksum": new_train["checksum"], "status": "running", "result": ""})):
              #{"config", "checksum", "status", "result"}
            print("## STARTING TASK")
            # la logica es: empieza con status running, mientras se entrena si sucede algun error se pondra en estado "stopped"
            # si el entrenamiento culmino exitosamente el estado sera "success"
            task_id = runTrainer.delay(ast.literal_eval(new_train["config_params"]),new_train["checksum"])
            print("## TASK_ID: ", task_id.task_id)
            return JSONResponse(
                content={"message": "Success", "task_id": str(task_id.task_id)},
                status_code=200,
            )
        else:
            return JSONResponse(content={"message": "Error", "error": "Cant save train"}, status_code=401)    
    except Exception as e:
        conn.deleteTrain(new_train["checksum"])
        print("train deleted")
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)

@trader_routes.post("/train/status")
async def train_status(status: StatusTrain):
    try:
        status = jsonable_encoder(status)
        train = conn.getTrainStatus(status["checksum"])
        if train:
            print("holis")
            if(train["status"] != "stopped"):
                return JSONResponse(
                    content={"message": "Success", "train": train}, status_code=200
                )
            else:
                return JSONResponse(
                    content={"message": "Error", "error": "stopped"}, status_code=200
                )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Train does not exist"}, status_code=200
            )
    except Exception as e:
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)

@trader_routes.post("/stop/train")
async def stop_train(train: StopTrain):
    try:
        train = jsonable_encoder(train)
        if conn.updateStateTrain(train["checksum"],"stopped"):
            print("train stopped")
            return JSONResponse(
                content={"message": "Success", "status": "stopped"}, status_code=200
            )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Cant set stopped"},
                status_code=201,
                    )
    except Exception as e:
        print(e)
        return JSONResponse(content={"message": "Error", "error": str(e)}, status_code=401)


@trader_routes.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        async with aiofiles.open(f"./ml/models/{file.filename}", "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
            out_file.close()
        return JSONResponse(
            content={"message": "Success", "filename": file.filename}, status_code=200
        )
    except Exception as e:
        print(e)
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)


@trader_routes.post("/new/bot")
async def new_bot(bot: NewBot):
    try:
        # if not exist register it in database
        new_bot = conn.saveBot(jsonable_encoder(bot))
        print(new_bot)
        return JSONResponse(
            content={"message": "Success", "uuid": new_bot["uuid"]}, status_code=200
        )
    except Exception as e:
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)


@trader_routes.post("/update/bot")
async def update_bot(bot: UpdateBot):
    try:
        if conn.existBot(bot.uuid):
            conn.updateBot(bot)
            edited_bot = conn.getBot(bot.uuid)
            return JSONResponse(
                content={"message": "Success", "bot": edited_bot}, status_code=200
            )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Not Found"}, status_code=200
            )
    except Exception as e:
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)


@trader_routes.post("/run/bot")
async def run_bot(bot: ActionBot):
    try:
        bot = jsonable_encoder(bot)
        print("bot: ",bot)
        if conn.existBot(bot["uuid"]):
            print("## EXIST BOT")
            bot_item = conn.getBot(bot["uuid"])
            print("## GET BOT SUCCESS")
            print(bot_item)
            # start bot
            print("## STARTING TASK")
            task_id = runTrader.delay(bot_item)
            print("## TASK_ID: ", task_id.task_id)
            return JSONResponse(
                content={"message": "Success", "task_id": str(task_id.task_id)},
                status_code=200,
            )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Not Found"}, status_code=200
            )
    except Exception as e:
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)


@trader_routes.post("/stop/bot")
async def stop_bot(bot: ActionBot):
    try:
        bot = jsonable_encoder(bot)
        if conn.existBot(bot["uuid"]):
            # stop bot
            # print("task_id: ",bot["task_id"])
            # task = AbortableAsyncResult(bot["task_id"])
            # task.abort() # no funciona :(
            # print(task.task_id)
            if conn.setBotStatus({"uuid": bot["uuid"], "status": "stopped"}):
                print("revoked")
                return JSONResponse(
                    content={"message": "Success", "status": "stopped"}, status_code=200
                )
            else:
                return JSONResponse(
                    content={"message": "Error", "error": "Cant set stopped"},
                    status_code=201,
                )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Not Found"}, status_code=201
            )
    except Exception as e:
        print(e)
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)


@trader_routes.post("/status/bot")
async def status_bot(bot: ActionBot):
    try:
        bot = jsonable_encoder(bot)
        if conn.existBot(bot["uuid"]):
            # stop bot
            result = conn.getBotStatus(bot["uuid"])
            return JSONResponse(
                content={"message": "Success", "status": result}, status_code=200
            )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Not Found"}, status_code=200
            )
    except Exception as e:
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)


@trader_routes.post("/trades/bot")
async def trades_bot(bot: TradesBot):
    try:
        bot = jsonable_encoder(bot)
        if conn.existBot(bot["uuid"]):
            trades = conn.getTradesBot(bot)
            capital = conn.getCapitalBot(bot)
            return JSONResponse(
                content={"message": "Success", "trades": trades, "capital": capital}, status_code=200
            )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Not Found"}, status_code=200
            )
    except Exception as e:
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)

@trader_routes.post("/trades/pair")
async def trades_bot_pair(bot: TradesPair):
    try:
        bot = jsonable_encoder(bot)
        if conn.existBot(bot["uuid"]):
            trades = conn.getTradesBotPair(bot)
            return JSONResponse(
                content={"message": "Success", "trades": trades}, status_code=200
            )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Not Found"}, status_code=200
            )
    except Exception as e:
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)

@trader_routes.post("/metrics/bot")
async def metrics_bot(item: MetricsBot):
    try:
        item = jsonable_encoder(bot)

        if conn.existBot(item["uuid"]):
            bot = conn.getBot(item["uuid"])

            # generate metrics

            metrics = ""

            return JSONResponse(
                content={"message": "Success", "metrics": metrics}, status_code=200
            )
        else:
            return JSONResponse(
                content={"message": "Error", "error": "Not Found"}, status_code=200
            )
    except Exception as e:
        return JSONResponse(content={"message": "Error", "error": e}, status_code=401)


