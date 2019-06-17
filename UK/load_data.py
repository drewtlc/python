import pymssql as ms
import pandas as pd
import functools
from functools import reduce
import re
import struct

class LoadData:
    # Подключение к MSSQL
    def connect(self, server, username, password, database):
        conn =  ms.connect(server, username, password, database)
        return conn

    # Выполнение SQL запроса к БД
    def readSql(self, conn, sql):
        dataframe = pd.read_sql(sql, conn)
        return dataframe

    # Чтение таблицы из БД (через выполнение запроса)
    def readTable(self, conn, tableName, conditions=""):
        sql = "select * from " + tableName
        if conditions != "":
            sql = sql + " where " + conditions
        return self.readSql(conn, sql)

    # Наложение фильтра по вхождению строк в значение колонки. Истина, если есть вхождение хотя бы одной строки.
    def filterByStrOr(self, df, colname, strings):
        return df[df[colname].notna() & reduce(lambda x,y: x|y, map(lambda str: df[colname].str.contains(str, flags = re.IGNORECASE), strings))]

    # Наложение фильтра по вхождению строк в значение колонки. Истина, если есть вхождение всех строк.
    def filterByStrAnd(self, df, colname, strings):
        return df[df[colname].notna() & reduce(lambda x,y: x&y, map(lambda str: df[colname].str.contains(str, flags = re.IGNORECASE), strings))]

    # Перевод бинарного поля в массив чисел float. На число выделяется 4 байта, которые меняют свой порядок на обратный перед переводом во float.
    def toFloatArray(self, binData):
        result=[]
        if type(binData)==bytes:
            blockSize = 4            
            for i in range(0,len(binData),blockSize):
                block = binData[i:i+blockSize]
                fl = struct.unpack(">f", block[::-1])
                result.append(fl[0])
        return result

    # Построение DataFrame по списку колонок keyColumns
    def createArrayDataFrame(self, df, keyColumns, arrayColumn):
        data = dict()
        maxlen = 0
        for index, row in df.iterrows():
            key = reduce(lambda s,k: (s if (s=="") else s+"_") + str(row[k]), keyColumns, "")
            data[key]=row[arrayColumn]
            maxlen = max(maxlen, len(row[arrayColumn]))
        for key, val in data.items():
            while len(val)<maxlen:
                val.append(0)
        return pd.DataFrame.from_dict(data)

#    def toString(self, floatArray):
#        return reduce(lambda s,f: (s if (s=="") else s+",") + str(f), floatArray, "")

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
    # Обработка таблиц - нужно много ресурсов
    #data["DynamicDataArray"] = data["DynamicData"].apply(ld.toFloatArray)
    #data["DynamicDataArrayLen"] = data["DynamicDataArray"].apply(len).to_int()
    # Фильтруем таблицы
    pumps = ld.filterByStrOr(trains, "Description", ["НПГ-720", "ЦГН 1250-71А"])
    pointsTochka = ld.filterByStrOr(points, "Name", ["Точка"])
    # Оставляем только часть колонок
    pumpsShort = pumps.filter(["idTrain", "Name", "Description"])
    pointsShort = pointsTochka.filter(["idPoint", "idTrain", "Name", "Direction"]) # "Description"
    measuresShort = measures.filter(["idMeasure", "idPoint", "Name"]) # "Description", "Note", "IsCritical"
    dataShort = data.filter(["idMeasure", "Date", "Value1", "Value2", "DynamicData"])
    # Соединяем таблицы в одну
    pumpsPoints = pd.merge(pumpsShort, pointsShort, on="idTrain", how="left")
    pumpsPointsMeasures = pd.merge(pumpsPoints, measuresShort, on="idPoint", how="left")
    pumpsPointsMeasuresData = pd.merge(pumpsPointsMeasures, dataShort, on="idMeasure", how="left")
    # Только данные насоса 420-1
    p420_1 = ld.filterByStrOr(pumpsPointsMeasuresData, "Name_x", ["420-1"])
    # Обработка данных измерений
    p420_1["DynamicDataArray"] = p420_1["DynamicData"].apply(ld.toFloatArray)
    p420_1_data = ld.createArrayDataFrame(p420_1, ["idMeasure", "Name", "Date"], "DynamicDataArray")
    p420_1["DynamicDataArrayLen"] = p420_1["DynamicDataArray"].apply(len).astype("int")

    pd.options.display.max_colwidth = 130
    print(p420_1.head()[["idMeasure", "Name", "Date", "DynamicDataArray"]])

    print("Запись в файл...")
    p420_1 = p420_1.drop(["DynamicData"], axis=1)
    #p420_1.to_csv("~/Share/p420_1.csv", index=False)
    #p420_1_data.to_csv("~/Share/p420_1_data.csv", index=False)
    with pd.ExcelWriter("/home/drew/Share/p420_1.xlsx") as writer:
        p420_1.to_excel(writer, sheet_name="p420_1", index=False)
        p420_1_data.to_excel(writer, sheet_name="p420_1_data", index=False)
        writer.save()
    print("Готово")

readTables()