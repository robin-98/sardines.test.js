import os
import json
import asyncio
import aiopg

async def connectDb(dbConfFile:str = None, user:str = None, password:str = None, host:str = "localhost", port:int = 5432, db:str = None, schema:str = "public"):
    """create a connection string and return a db instance
    """
    if dbConfFile is None and \
       (user is None or password is None or host is None or db is None or port is None):
        raise Exception('Invalid postgres connection request')

    if dbConfFile is not None and not os.path.exists(dbConfFile):
        raise Exception('Can not open database configuration file at {}'.format(dbConfFile))

    dbConf = {
        "host": host,
        "port": user,
        "database": db,
        "schema": schema,
        "user": user,
        "password": password
    }
    if dbConfFile is not None:
        with open(dbConfFile) as f:
            dbConf = json.load(f)
            if "type" not in dbConf \
            or dbConf["type"] != "postgres" \
            or "settings" not in dbConf:
                raise Exception("invalid database configuration file {}".format(dbConfFile))
            dbConf = dbConf["settings"]

    connStr = "dbname={database} user={user} password={password} host={host} port={port}".format(
        user = dbConf["user"],
        password = dbConf["password"],
        host = "localhost",
        port = dbConf["port"],
        database = dbConf["database"]
    )
    try:
        pool = await aiopg.create_pool(connStr)
        conn = await pool.acquire()
        return (conn, dbConf["schema"])
    except Exception as e:
        print('Error while connecting to postgres database [{}]'.format(connStr), e)
        raise e
