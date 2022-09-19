
class ConfigAPP():
    def __init__(self):
        self.ticks = [
                    "DOTBTC",
                    "ETHBTC",
                    "SOLBTC"
                ]
        self.timeframe = "5m"

        self.start = "01-01-2022"

        self.end = "30-12-2022"
        self.indicators = ['rsi', 'adx', 'macd', 'ema50', 'ema9', 'ema21', 'ema100', 'ema200', 'change', 'cambio', 'obv']
