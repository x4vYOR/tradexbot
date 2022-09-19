import joblib
#import json
#from pandas import json_normalize


#model = joblib.load('./model/modelo_rf_All_pairs_15m_06072022011022AM.joblib')
#scaler = joblib.load('./model/_All_pairs_15m_06072022040229PM.joblib')
class MlModel():

    def __init__(self):
        self.model = None
        self.scaler = None
        self.columns = []

    async def load_model(self, dirs):
        try:
            print(type(dirs.scaler))
            print(type(dirs.model))
            print(type(dirs.columns))
            self.columns = dirs.columns
            self.scaler = joblib.load('./ml/'+dirs.scaler)
            self.model = joblib.load('./ml/'+dirs.model)
            return True
        except Exception as e:
            print(e)
            return False

    async def predict(self, df) -> list:
        try:
            # The first column must be pair name ie: ETHBTC
            df1 = self.scaler.transform(df.loc[:, ~df.columns.isin(['pair','open_time'])])
            df["buy"] = self.model.predict(df1)
            return df[["pair","buy"]].to_dict('records')
        except Exception as e:
            print(e)
            return False

    """
    def predict(_data):
        #df = read_json(_data)
        data = json.loads(_data)
        df = json_normalize(data) 
        scaler.transform(df)
        df["buy"] = False #model.predict(df)
        #parsed = json.loads(df.to_json(orient="records"))
        return df.to_dict()
    """



