
import requests as req
import pandas as pd
import datetime

def tuples_to_dict(data):
    res={}
    for key, value in data:
        res[key]=[]
    for key, value in data:
        res[key].append(value)
    for key, value in res.items():
        if(len(value)==1):
            res[key] = value[0]
    return res

def extract_indicators(indicators, rules):
    rules_indicator1 = [item["first_indicator"]["name"] for item in rules]
    rules_indicator2 = [item["second_indicator"]["name"] for item in rules]
    indicators = [item["indicator"]["name"] for item in indicators]
    return [item for item in list(set(rules_indicator1+rules_indicator2+indicators)) if item != "value"]

""" async def get_dataset(pairs, timeframe, ini, end, indicators):
        data = {
            "pair": "ETHBTC",
            "timeframe": "5m",
            "ini": "01/03/2022",
            "end": "15/04/2022",
            "indicators": ["open_time","open","high","rsi","macd","ema200"]
        }
        res = requests.post(host+'/api/login',json={"username": "x4vyjm", "email": "x4vyjm@gmail.com"})
        token = res.text.replace('"','')
        headers = {"Authorization":"Bearer "+token}
        type(headers)
        r = requests.post(host+'/api/data', json=data, headers=headers)
        df = pd.read_json(r.json()["data"]) """


def unixtodate(value, format='%d/%m/%Y %H:%M'):
    if(len(value)>0):
        ts = int(float(value))
        dt = datetime.datetime.fromtimestamp(ts / 1000)
        formatted_time = dt.strftime(format)
        return formatted_time
    else:
        return ""

def formatdate(value, format='%d/%m/%Y %H:%M'):
    print(f"value: {value}")
    if(len(value)>0):
        ts = int(value)
        dt = datetime.datetime.fromtimestamp(ts / 1000)
        formatted_time = dt.strftime(format)
        return formatted_time
    else:
        return ""