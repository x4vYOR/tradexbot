from pydantic import BaseModel
from typing import Optional

class StatusTrain(BaseModel):
    checksum: str

class NewTrain(BaseModel):
    config_params: str
    checksum: str

class StopTrain(BaseModel):
    checksum: str

class NewBot(BaseModel):
    columns: list
    pairs: list
    scaler: str
    model: str
    timeframe: str
    api_key: str
    api_secret: str
    exchange: str
    initial_capital: float
    capital_pair: dict
    currency_base: str
    strategy: str
    strategy_parameters: str

class UpdateBot(BaseModel):
    uuid: str
    columns: list
    pairs: list
    scaler: str
    model: str
    timeframe: str
    api_key: Optional[str]
    api_secret: Optional[str]
    exchange: str
    initial_capital: float
    capital_pair: dict
    currency_base: str
    strategy: str
    strategy_parameters: str

class ActionBot(BaseModel):
    uuid:str
    task_id:Optional[str]

class TradesBot(BaseModel):
    uuid: str
    pairs: Optional[list]
    ini: Optional[str]
    end: Optional[str]

class TradesPair(BaseModel):
    uuid: str
    pair: Optional[str]
    ini: Optional[str]
    end: Optional[str]

class MetricsBot(BaseModel):
    uuid: str
    ini: Optional[str]
    end: Optional[str]

class TaskTicket(BaseModel):
    """ID and status for the async tasks"""
    task_id: str
    status: str
    
"""
class DataRow(BaseModel):
    rsi: float
    adx: float
    macd: float
    macd_signal: float
    macd_hist: float
    ema50: float
    ema100: float
    ema200: float
    obv: float
    volume:float
"""
