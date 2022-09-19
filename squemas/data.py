

async def dataEntity(item, columns) -> dict:
    #print(item)
    #print(columns)
    return { col : item[col] for col in columns }

async def datasEntity(items, columns: list) -> list:
    
    return [ await dataEntity(item, columns) for item in items]
    