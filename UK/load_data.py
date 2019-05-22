import pymssql as ms
import pandas as pd
import functools
from functools import reduce
import re

class LoadData:
    def connect(self, server, username, password, database):
        conn =  ms.connect(server, username, password, database)
        return conn

    def readSql(self, conn, sql):
        dataframe = pd.read_sql(sql, conn)
        return dataframe

    def readTable(self, conn, tableName, conditions=""):
        sql = "select * from " + tableName
        if conditions != "":
            sql = sql + " where " + conditions
        return self.readSql(conn, sql)

    def filterByStrOr(self, df, colname, strings):
        return df[df[colname].notna() & reduce(lambda x,y: x|y, map(lambda str: df[colname].str.contains(str, flags = re.IGNORECASE), strings))]

    def filterByStrAnd(self, df, colname, strings):
        return df[df[colname].notna() & reduce(lambda x,y: x&y, map(lambda str: df[colname].str.contains(str, flags = re.IGNORECASE), strings))]

def readTables():
    ld = LoadData()
    conn = ld.connect("192.168.36.58", "drew", "drew", "UralKalii05042019")
    # Выбираем данные таблиц
    trains = ld.readTable(conn, "dbo.Trains")
    points = ld.readTable(conn, "dbo.Points")
    measures = ld.readTable(conn, "dbo.Measures")
    data = ld.readSql(conn, "select d.* from dbo.Data d \
                                left join (select [idMeasure], max([Date]) as lastDate from dbo.Data group by [idMeasure]) ld on (d.[idMeasure]=ld.[idMeasure] and d.[Date]=ld.[lastDate]) \
                            where ld.[idMeasure] is not null")
    # Фильтруем таблицы
    pumps = ld.filterByStrOr(trains, "Description", ["НПГ-720", "ЦГН 1250-71А"])
    pointsTochka = ld.filterByStrOr(points, "Name", ["Точка"])
    # Оставляем только часть колонок
    pumpsShort = pumps.filter(["idTrain", "Name", "Description"])
    pointsShort = pointsTochka.filter(["idPoint", "idTrain", "Name", "Description", "Direction"])
    measuresShort = measures.filter(["idMeasure", "idPoint", "Name", "Description", "Note", "IsCritical"])
    dataShort = data.filter(["idMeasure", "Date", "Value1", "Value2"])
    # Соединяем таблицы в одну
    pumpsPoints = pd.merge(pumpsShort, pointsShort, on="idTrain", how="left")
    pumpsPointsMeasures = pd.merge(pumpsPoints, measuresShort, on="idPoint", how="left")
    pumpsPointsMeasuresData = pd.merge(pumpsPointsMeasures, dataShort, on="idMeasure", how="left")
    # Только данные насоса 420-1
    p420_1 = ld.filterByStrOr(pumpsPointsMeasuresData, "Name_x", ["420-1"])

    print(p420_1.head(200))

    p420_1.to_csv("~/Share/p420_1.csv", index=False)



readTables()