import joblib
#import json
#from pandas import json_normalize
from os import path, getcwd
import ast
from random import choice

#model = joblib.load('./model/modelo_rf_All_pairs_15m_06072022011022AM.joblib')
#scaler = joblib.load('./model/_All_pairs_15m_06072022040229PM.joblib')
class MlModel():

    def __init__(self):
        self.model = None
        self.scaler = None
        self.columns = []

    def load_model(self, dirs):
        try:
            print(dirs["scaler"])
            print(dirs["model"])
            print(f"dirs[columns]: {dirs['columns']} type: {type(dirs['columns'])}")
            self.columns = dirs["columns"]
            print(f"self.columns after: {self.columns} type: {self.columns}")
            print("current dir: ",getcwd())

            print("loading model")
            model_uri = './ml/models/'+dirs["model"]
            print("model uri: ",model_uri)
            print(f"exist model: {path.exists(model_uri)}")
            self.model = joblib.load(str(model_uri))


            print("loading scaler")            
            scaler_uri = './ml/models/scalers/'+dirs["scaler"]
            print("scaler uri: ",scaler_uri)
            print(f"exist scaler: {path.exists(scaler_uri)}")
            self.scaler = joblib.load(str(scaler_uri))
            
            return True
        except SystemExit as x:
            print("errorzote")
            print(x)
            print("errorzoteo")
            return False
        except Exception as e:
            print("errorcito")
            print(e)
            print("errorcito")
            return False
        

    def predict(self, df) -> list:
        try:
            # The first column must be pair name ie: ETHBTC
            print("aplicando scaling")
            #df1 = self.scaler.transform(df.loc[:, ~df.columns.isin(['pair','open_time','close'])])
            df1 = self.scaler.transform(df[self.columns])
            print("aplicando predict")
            df["buy"] = self.model.predict(df1)
            return df[["pair","buy","close","close_time"]].to_dict('records')
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



