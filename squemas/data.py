

def dataEntity(item, columns) -> dict:
    #print(item)
    #print(columns)
    return { col : item[col] for col in columns }

def datasEntity(items, columns: list) -> list:
    
    return [ dataEntity(item, columns) for item in items]
    