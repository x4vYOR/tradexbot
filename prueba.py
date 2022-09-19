
from pymongo import MongoClient

uri = "mongodb://localhost:27017/"

conn = MongoClient(uri)

mydb = conn["prueba"]

mycol = mydb["coleccion"]

Emp = [
    { "EmpID": "5", "Name": "aaaa" ,"Designation":"jhkjddkhjk"},
    { "EmpID": "6", "Name": "hjbbkh" ,"Designation":"bbbb"},
    { "EmpID": "7", "Name": "ccc" ,"Designation":"cc"}
]
mycol.insert_many(Emp)

#for x in mycol.find(): print(x)
print(conn["prueba"]["coleccion"].find()[0])

"""
import pandas as pd

dicts = [
    {
        "id": 2424,
        "name": "javier",
        "apellido": "jimenez"
    },
    {
        "id": 2421,
        "name": "jafgdfer",
        "apellido": "jifgdfez"
    },
    {
        "id": 2423,
        "name": "javgfdfg",
        "apellido": "jgdfgdfnez"
    },
    {
        "id": 2422,
        "name": "jdfgdf",
        "apellido": "jifgdfgz"
    }
]
dicts2 = [
    {
        "id": 5553,
        "name": "javgfdaaaaafg",
        "apellido": "jgdfgdfnez"
    },
    {
        "id": 5532,
        "name": "jdaaaafgdf",
        "apellido": "jifgdfgz"
    }
]
df = pd.DataFrame(dicts)

df1 = pd.DataFrame(dicts2)
#array = [2422,2421]
#df = df.drop(df[df.id.isin(array)].index)
print(df)
df = df.shift(-2)
print(df)
df.iloc[-2:] = df1

print(df)

#print(df1)
"""

