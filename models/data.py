from pydantic import BaseModel
from typing import Optional

class ReqDataset(BaseModel):
    pair: str
    timeframe: str
    ini: Optional[str]
    end: Optional[str]
    indicators: list
    class Config:
        schema_extra = {
            "example": {
                "pair": "ETHBTC",
                "timeframe": "15m",
                "ini": "01-01-2022",
                "end": "01-06-2022",
                "indicators": ["open_time","open","high","low","close","volume","rsi","macd","macd_hist","macd_signal","adx","emaXXX","other"]
            }
        }

class ReqWsData(BaseModel):
    pairs: list
    timeframe: str
    class Config:
        schema_extra = {
            "example": {
                "pairs": ["ETHBTC","SOLBTC"],
                "timeframe": "15m"
            }
        }