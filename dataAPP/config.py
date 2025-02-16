
class ConfigAPP():
    def __init__(self):
        self.ticks = [
                    "ETHUSDT",
                    "SOLUSDT",
                    "AVAXUSDT",
                    "ADAUSDT",
                    "ALGOUSDT",
                    "DOTUSDT",
                    "LINKUSDT",
                    "UNIUSDT",
                    "MANAUSDT",
                    "THETAUSDT",
                    "BTCUSDT",
                    "VETUSDT"
                ]
        self.timeframe = "30m"

        self.start = "01-01-2020"

        self.end = "30-12-2024"
        self.indicators = ['rsi', 'adx', 'macd', 'macd_hist', 'macd_signal', 'ema50', 'ema9', 'ema21', 'ema100', 'ema200', 'change', 'cambio', 'obv','mfi','cci','mom','atr','bbands']
