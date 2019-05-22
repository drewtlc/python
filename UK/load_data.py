import pymssql as ms
import pandas as pd

class LoadData:
    def connect(self, server, username, password, database):
        conn =  ms.connect(server, username, password, database)
        return conn

    def readTable(self, tableName, conn):
        sql = "select * from " + tableName
        dataframe = pd.read_sql(sql, conn)
        return dataframe

def readTables():
    ld = LoadData()
    conn = ld.connect("192.168.36.58", "drew", "drew", "UralKalii05042019")
    trains = ld.readTable("dbo.Trains", conn)
    print(trains.head())


readTables()