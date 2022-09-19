from config import ConfigAPP
from getData import saveData

conf = ConfigAPP()
objData = saveData(conf.ticks, conf.timeframe, start=conf.start,end=conf.end, indicators=conf.indicators)

# descarga y almacena toda la data historica incluso del dia en su respectiva colleción
# Pair - timeframe
objData.loadDB()

#Para iniciar el websocket, hace un repaso por la lista de pares y recoge las ultimas velas de la hora
# para asegurarse de estar actualizado.
# compara con la bd, guardando las filas que faltan. y procede a instanciar la conexion ws
ws = objData.startWebSocket()

ws.run_forever()
