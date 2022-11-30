
class ConfigAPP():
    def __init__(self):
        self.ticks = [
                    "BNBBTC",
                    "ETHBTC",
                    "SOLBTC",
                    "AVAXBTC",
                    "ADABTC",
                    "DOTBTC",
                    "LINKBTC",
                    "MATICBTC",
                    "UNIBTC",
                    "ALGOBTC",
                    "ATOMBTC"
                ]
        self.timeframe = "15m"

        self.start = "01-01-2017"

        self.end = "30-12-2022"
        self.indicators = ['rsi', 'adx', 'macd', 'macd_hist', 'macd_signal', 'ema50', 'ema9', 'ema21', 'ema100', 'ema200', 'change', 'cambio', 'obv','mfi','cci','mom','atr','bbands']
