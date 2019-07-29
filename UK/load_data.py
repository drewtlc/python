import pymssql as ms
import pandas as pd
import functools
from functools import reduce
import re
import struct
import xml.etree.ElementTree as et
import datetime

# Общий класс для работы с БД (соединение, чтение таблиц, фильтрация)
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
        sql = "select * from " + tableName + ("" if conditions == "" else " where " + conditions)
        # if conditions != "":
        #     sql = sql + " where " + conditions
        return self.readSql(conn, sql)

    # Наложение фильтра по вхождению строк в значение колонки. Истина, если есть вхождение хотя бы одной строки.
    def filterByStrOr(self, df, colname, strings):
        return df[df[colname].notna() & reduce(lambda x,y: x|y, map(lambda s: df[colname].astype(str).str.contains(s, flags = re.IGNORECASE), strings))]

    # Наложение фильтра по вхождению строк в значение колонки. Истина, если есть вхождение всех строк.
    def filterByStrAnd(self, df, colname, strings):
        return df[df[colname].notna() & reduce(lambda x,y: x&y, map(lambda s: df[colname].astype(str).str.contains(s, flags = re.IGNORECASE), strings))]

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
        for _, row in df.iterrows():
            key = reduce(lambda s,k: (s if (s=="") else s+"_") + str(row[k]), keyColumns, "")
            data[key]=row[arrayColumn]
            maxlen = max(maxlen, len(row[arrayColumn]))
        for key, val in data.items():
            while len(val)<maxlen:
                val.append(0)
        return pd.DataFrame.from_dict(data)
    
    # Разбор даты
    def parseDate(self, value):
        sValue = str(value)
        dmy = sValue.split(" ")[0]
        dmyArr = dmy.split("-")
        return datetime.date(int(dmyArr[0]), int(dmyArr[1]), int(dmyArr[2]))

    # Запись в файл
    def writeToFile(self, fileName, df, dfSheetName="dataframe", dfRows=None, pt=None, ptSheetName="pTable", ptRows=None):
        print("Запись в файл " + fileName)
        with pd.ExcelWriter(fileName) as writer:
            print("  " + dfSheetName + ("" if dfRows is None else " (" + str(dfRows) + " строк)") + "...")
            dfWrite = df if dfRows is None else df.head(dfRows)
            dfWrite.to_excel(writer, sheet_name=dfSheetName, index=False)
            if pt is not None:
                print("  " + ptSheetName + ("" if ptRows is None else " (" + str(ptRows) + " строк)") + "...")
                ptWrite = pt if ptRows is None else df.head(ptRows)
                ptWrite.to_excel(writer, sheet_name=ptSheetName)
        print("Записьм в файл завершена")

# Класс для логики, которая имеет специфику обработки базы UK
class UKLoadData(LoadData):
    # Построение DataFrame по разбору XML-поля
    #   idField     - имя поля-ключа из td
    #   xmlField    - имя поля с XML-данными
    #   arrayTag    - имя тэга, который содержит множество тэгов-строк, из которых извлекаются данные
    #   attributes  - список атрибутов тэга-строки, для извлечения значений
    def createXmlDataFrame(self, td, idField, xmlField, arrayTag, attributes):
        data = list()
        labels = [idField] + attributes
        for _, tdRow in td.iterrows():
            root = et.fromstring("<root>" + tdRow[xmlField] + "</root>")
            arrayNode = root.find(arrayTag)
            for child in arrayNode:
                row = list()
                row.append(tdRow[idField])
                for attr in attributes:
                    row.append(child.get(attr))
                data.append(row)
        return pd.DataFrame.from_records(data, columns=labels)

    def severalColumns(self, df, dic, key):
        dfCols = df[dic[key]]
        dfCols.columns = list(map(lambda el: key + "_" + str(el), dic[key]))
        return dfCols

    def doPivotTable(self, df, pivotIndexColumns, pivotValuesColumns, filterColumn=None, filterValues=None):
        pivotDf = df[pivotIndexColumns + pivotValuesColumns]
        if filterColumn is not None:
            pivotDf = self.filterByStrOr(pivotDf, filterColumn, filterValues)
        pivotDf = pivotDf.sort_values(by=pivotIndexColumns + pivotValuesColumns)
        pTable = pd.pivot_table(pivotDf, index=pivotIndexColumns, values=pivotValuesColumns, aggfunc=[len,min,max])
        return pTable

#    def toString(self, floatArray):
#        return reduce(lambda s,f: (s if (s=="") else s+",") + str(f), floatArray, "")

def readTables():
    ld = UKLoadData()
    conn = ld.connect("192.168.36.58", "drew", "drew", "UralKalii05042019")
    # Выбираем данные таблиц
    trains = ld.readTable(conn, "dbo.Trains")
    trainMechanisms = ld.readTable(conn, "dbo.TrainMechanisms")
    trainComponents = ld.readTable(conn, "dbo.TrainComponents")
    mechModels = ld.readTable(conn, "dbo.Mech_Models")
    compComponents = ld.readTable(conn, "dbo.Comp_Components")
    points = ld.readTable(conn, "dbo.Points")
    measures = ld.readTable(conn, "dbo.Measures")
    # Все данные измерений
    data = ld.readTable(conn, "dbo.Data")
    #   Только самые новые из измерений
    #   data = ld.readSql(conn, "select d.* from dbo.Data d \
    #                             left join (select [idMeasure], max([Date]) as lastDate from dbo.Data group by [idMeasure]) ld on (d.[idMeasure]=ld.[idMeasure] and d.[Date]=ld.[lastDate]) \
    #                         where ld.[idMeasure] is not null")
    #   Обработка таблиц - нужно много ресурсов
    #   data["DynamicDataArray"] = data["DynamicData"].apply(ld.toFloatArray)
    #   data["DynamicDataArrayLen"] = data["DynamicDataArray"].apply(len).to_int()
    # Надо из таблиц TrainMechanisms, TrainComponents, Mech_Models, Comp_Components
    #   извлечь XML и разобрать на новые таблицы связей с точками измерений
    trainMechanismsBindings = ld.createXmlDataFrame(trainMechanisms, "idTrainMech", "Bindings", "Points", ["CompIndex", "TrainIndex", "AdditionalData"])
    trainComponentsBindings = ld.createXmlDataFrame(trainComponents, "idTrainComponent", "Bindings", "Points", ["CompIndex", "TrainIndex", "AdditionalData"])
    trainComponentsBindings.columns = ["idTrainComponent", "CompIndex", "idPoint", "AdditionalData"]
    trainComponentsBindings = trainComponentsBindings.astype(int)
    mechModelsPoints = ld.createXmlDataFrame(mechModels, "idModel", "Points", "Points", ["Index", "Name", "Description"])
    compComponentsPoints = ld.createXmlDataFrame(compComponents, "idComponent", "Points", "Points", ["Index", "Name", "Description", "Direction"])
    compComponentsPoints.columns = ["idComponent", "CompIndex", "Name", "Description", "Direction"]
    compComponentsPoints = compComponentsPoints.astype({"idComponent" : int, "CompIndex" : int, "Direction" : int})
    # print(trainMechanismsBindings.head(10))
    # print(trainComponentsBindings.head(10))
    # print(mechModelsPoints.head(10))
    # print(compComponentsPoints.head(10))
    # Нужные для соединения колонки
    colDict = dict()
    colDict["data"]                     = ["idMeasure", "Date", "DynamicData"]
    colDict["measures"]                 = ["idMeasure", "idPoint", "Name", "Description"]
    colDict["points"]                   = ["idPoint", "idTrain", "Name", "Description", "Direction"]
    colDict["trainComponentsBindings"]  = ["idTrainComponent", "CompIndex", "idPoint", "AdditionalData"]
    colDict["compComponentsPoints"]     = ["idComponent", "CompIndex", "Name", "Description", "Direction"]
    colDict["trainComponents"]          = ["idTrainComponent", "idTrain", "idCompComponent", "Name", "Description"]
    colDict["trains"]                   = ["idTrain", "Name", "Description"]
    # Оставляем только часть колонок и переименовываем их
    dataCols = ld.severalColumns(data, colDict, "data")
    measuresCols = ld.severalColumns(measures, colDict, "measures")
    pointsCols = ld.severalColumns(points, colDict, "points")
    trainComponentsBindingsCols = ld.severalColumns(trainComponentsBindings, colDict, "trainComponentsBindings")
    compComponentsPointsCols = ld.severalColumns(compComponentsPoints, colDict, "compComponentsPoints")
    trainComponentsCols = ld.severalColumns(trainComponents, colDict, "trainComponents")
    trainsCols = ld.severalColumns(trains, colDict, "trains")
    del data, measures, points, trainComponentsBindings, compComponentsPoints, trainComponents, trains
    # Строим соединение таблиц
    trainsAndComponents = pd.merge(trainsCols, trainComponentsCols, how="left", left_on="trains_idTrain", right_on="trainComponents_idTrain")
    trainsAndComponentsWithBindings = pd.merge(trainsAndComponents, trainComponentsBindingsCols, how="left", left_on="trainComponents_idTrainComponent", right_on="trainComponentsBindings_idTrainComponent")
    trainsAndComponentsWithBindingsAndPoints = pd.merge(trainsAndComponentsWithBindings, compComponentsPointsCols, how="left", left_on=["trainComponents_idCompComponent", "trainComponentsBindings_CompIndex"], right_on=["compComponentsPoints_idComponent", "compComponentsPoints_CompIndex"])
    dataAndMesures = pd.merge(dataCols, measuresCols, how="left", left_on="data_idMeasure", right_on="measures_idMeasure")
    dataMesuresPoints = pd.merge(dataAndMesures, pointsCols, how="left", left_on="measures_idPoint", right_on="points_idPoint")
    dataMesuresPointsComponentsPoints = pd.merge(dataMesuresPoints, trainsAndComponentsWithBindingsAndPoints, how="left", left_on=["points_idPoint", "points_Direction"], right_on=["trainComponentsBindings_idPoint", "compComponentsPoints_Direction"])
    del trainsAndComponents, trainsAndComponentsWithBindings, trainsAndComponentsWithBindingsAndPoints, dataAndMesures, dataMesuresPoints
    # Группируем, чтобы получить временные ряды
    
    # Изменяем колонки, чтобы сделать хорошую сводку
    dataMesuresPointsComponentsPoints["trainComponents_Name_Description"] = dataMesuresPointsComponentsPoints["trainComponents_Name"] + " " + dataMesuresPointsComponentsPoints["trainComponents_Description"]
    dataMesuresPointsComponentsPoints["data_Date"] = dataMesuresPointsComponentsPoints["data_Date"].apply(ld.parseDate)
    # Делаем сводку
    pivotIndexColumns = ["trains_idTrain", "trains_Name", "trains_Description", 
                         "trainComponents_idCompComponent", "trainComponents_idTrainComponent", "trainComponents_Name_Description",
                         "compComponentsPoints_Name", "compComponentsPoints_Description", 
                         "points_idPoint", "points_Name", "points_Description", "points_Direction", 
                         "measures_idMeasure", "measures_Name", "measures_Description"]
    pivotValuesColumns = ["data_Date"]
    pTable = ld.doPivotTable(dataMesuresPointsComponentsPoints, pivotIndexColumns, pivotValuesColumns, "trains_Name", ["5.5-1G11"]) # "trains_Description", ["CNH-B"]
    # Запись в файл
    dataMesuresPointsComponentsPoints = dataMesuresPointsComponentsPoints.drop(["data_DynamicData"], axis=1)
    ld.writeToFile("/home/drew/UK/pumps.xlsx", dataMesuresPointsComponentsPoints, "5.5-1G11", 2000, pTable)
    # dfRes_1 = pivotDf
    # print("Запись в файл...")
    # # dfRes_1 = dfRes_1.drop(["data_DynamicData"], axis=1)
    # with pd.ExcelWriter("/home/drew/UK/pumps.xlsx") as writer:
    #     # dfRes_1.head(2000).to_excel(writer, sheet_name="dfRes_1", index=False)
    #     # pTable.head(2000).to_excel(writer, sheet_name="pTable")
    #     # dfRes_1.head(10000).to_excel(writer, sheet_name="dfRes_1", index=False)
    #     dfRes_1.to_excel(writer, sheet_name="5.5-1G11", index=False)
    #     pTable.to_excel(writer, sheet_name="pTable")
    #     writer.save()
    # print("Готово")

    #colNames += list(map(lambda el: "data" + str(el), colDict["data"]))
    # with pd.merge(data[["idMeasure", "Date", "DynamicData"]], measures[["idMeasure", "idPoint", "Name", "Description"]], on="idMeasure", how="left") as dataMeasures:
    #     colNames += list(map(lambda el: "data"+str(el), colDict["data"]))
    #     dataMeasures.columns = ["idMeasure", "Date", "DynamicData", "idMeasure", "Point", "Name", "Description"]

    # # Фильтруем таблицы
    # pumps = ld.filterByStrOr(trains, "Description", ["CNH-B"])
    # pointsTochka = ld.filterByStrOr(points, "Name", ["Точка 1"])
    # pointsTochka = ld.filterByStrOr(pointsTochka, "Direction", ["1"])
    # measuresSPms2 = ld.filterByStrOr(measures, "Name", ["СП м/с2"])
    # # Оставляем только часть колонок
    # pumpsShort = pumps.filter(["idTrain", "Name", "Description"])
    # pointsShort = pointsTochka.filter(["idPoint", "idTrain", "Name", "Direction"]) # "Description"
    # measuresShort = measuresSPms2.filter(["idMeasure", "idPoint", "Name"]) # "Description", "Note", "IsCritical"
    # dataShort = data.filter(["idMeasure", "Date", "Value1", "Value2", "DynamicData"])
    # # Соединяем таблицы в одну
    # pumpsPoints = pd.merge(pumpsShort, pointsShort, on="idTrain", how="left")
    # pumpsPointsMeasures = pd.merge(pumpsPoints, measuresShort, on="idPoint", how="left")
    # pumpsPointsMeasuresData = pd.merge(pumpsPointsMeasures, dataShort, on="idMeasure", how="left")
    # # Только данные насоса 420-1
    # p420_1 = ld.filterByStrOr(pumpsPointsMeasuresData, "Name_x", ["420-1"])
    # # Обработка данных измерений
    # p420_1["DynamicDataArray"] = p420_1["DynamicData"].apply(ld.toFloatArray)
    # p420_1_data = ld.createArrayDataFrame(p420_1, ["idMeasure", "Name", "Date"], "DynamicDataArray")
    # p420_1["DynamicDataArrayLen"] = p420_1["DynamicDataArray"].apply(len).astype("int")

    # pd.options.display.max_colwidth = 130
    # print(p420_1.head()[["idMeasure", "Name", "Date", "DynamicDataArray"]])

    # print("Запись в файл...")
    # p420_1 = p420_1.drop(["DynamicData"], axis=1)
    # #p420_1.to_csv("~/Share/p420_1.csv", index=False)
    # #p420_1_data.to_csv("~/Share/p420_1_data.csv", index=False)
    # with pd.ExcelWriter("/home/drew/UK/pumps.xlsx") as writer:
    #     pumpsShort.to_excel(writer, sheet_name="pumpsShort", index=False)
    #     p420_1.to_excel(writer, sheet_name="p420_1", index=False)
    #     p420_1_data.to_excel(writer, sheet_name="p420_1_data", index=False)
    #     writer.save()
    # print("Готово")

readTables()