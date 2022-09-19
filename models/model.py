from pydantic import BaseModel
from typing import Optional

class ReloadModel(BaseModel):
    scaler: str
    model: str
    columns: list

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
