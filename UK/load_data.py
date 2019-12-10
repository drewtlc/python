import pymssql as ms
import pandas as pd
import functools
from functools import reduce
import re
import struct
import xml.etree.ElementTree as et
import datetime
import os

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
        with pd.ExcelWriter(path=fileName, mode=('a' if os.path.exists(fileName) else 'w')) as writer:
            print("  " + dfSheetName + ("" if dfRows is None else " (" + str(dfRows) + " строк)") + "...")
            dfWrite = df if dfRows is None else df.head(dfRows)
            dfWrite.to_excel(writer, sheet_name=dfSheetName, index=False)
            if pt is not None:
                print("  " + ptSheetName + ("" if ptRows is None else " (" + str(ptRows) + " строк)") + "...")
                ptWrite = pt if ptRows is None else df.head(ptRows)
                ptWrite.to_excel(writer, sheet_name=ptSheetName)
        print("Запись в файл завершена")

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
    # Файл для разписи результатов
    outFileName = "/home/drew/UK/pumps.xlsx"
    if os.path.exists(outFileName): os.remove(outFileName)
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
    trainComponentsBindingsPoints = ld.createXmlDataFrame(trainComponents, "idTrainComponent", "Bindings", "Points", ["CompIndex", "TrainIndex", "AdditionalData"])
    trainComponentsBindingsPoints.columns = ["idTrainComponent", "CompIndex", "idPoint", "AdditionalData"]
    trainComponentsBindingsPoints = trainComponentsBindingsPoints.astype(int)
    trainComponentsBindingsFaultFrequencies = ld.createXmlDataFrame(trainComponents, "idTrainComponent", "Bindings", "FaultFreqValues", ["CompIndex", "Value", "Value2", "Value3"])
    trainComponentsBindingsFaultFrequencies.columns = ["idTrainComponent", "CompIndex", "Value", "Value2", "Value3"]
    trainComponentsBindingsFaultFrequencies = trainComponentsBindingsFaultFrequencies.astype({"idTrainComponent" : int, "CompIndex" : int})
    mechModelsPoints = ld.createXmlDataFrame(mechModels, "idModel", "Points", "Points", ["Index", "Name", "Description"])
    compComponentsPoints = ld.createXmlDataFrame(compComponents, "idComponent", "Points", "Points", ["Index", "Name", "Description", "Direction"])
    compComponentsPoints.columns = ["idComponent", "CompIndex", "Name", "Description", "Direction"]
    compComponentsPoints = compComponentsPoints.astype({"idComponent" : int, "CompIndex" : int, "Direction" : int})
    compComponentsFaultFrequencies = ld.createXmlDataFrame(compComponents, "idComponent", "FaultFrequencies", "FaultFrequencies", ["Name", "Description", "Code", "Value", "CoefValue2", "CoefValue3"])
    compComponentsFaultFrequencies.columns = ["idComponent", "Name", "Description", "Code", "Value", "CoefValue2", "CoefValue3"]
    compComponentsFaultFrequencies = compComponentsFaultFrequencies.astype({"idComponent" : int, "Code" : int})
    # print(trainMechanismsBindings.head(10))
    # print(trainComponentsBindingsPoints.head(10))
    # print(mechModelsPoints.head(10))
    # print(compComponentsPoints.head(10))
    # Нужные для соединения колонки
    colDict = dict()
    colDict["data"]                           = ["idMeasure", "Date", "DynamicData"]
    colDict["measures"]                       = ["idMeasure", "idPoint", "Name", "Description"]
    colDict["points"]                         = ["idPoint", "idTrain", "Name", "Description", "Direction"]
    colDict["trainComponentsBindingsPoints"]  = ["idTrainComponent", "CompIndex", "idPoint", "AdditionalData"]
    colDict["trainComponentsBindingsFaultFrequencies"] = ["idTrainComponent", "CompIndex", "Value", "Value2", "Value3"]
    colDict["compComponentsPoints"]           = ["idComponent", "CompIndex", "Name", "Description", "Direction"]
    colDict["compComponentsFaultFrequencies"] = ["idComponent", "Name", "Description", "Code", "Value", "CoefValue2", "CoefValue3"]
    colDict["trainComponents"]                = ["idTrainComponent", "idTrain", "idCompComponent", "Name", "Description"]
    colDict["trains"]                         = ["idTrain", "Name", "Description"]
    # Оставляем только часть колонок и переименовываем их
    dataCols = ld.severalColumns(data, colDict, "data")
    measuresCols = ld.severalColumns(measures, colDict, "measures")
    pointsCols = ld.severalColumns(points, colDict, "points")
    trainComponentsBindingsPointsCols = ld.severalColumns(trainComponentsBindingsPoints, colDict, "trainComponentsBindingsPoints")
    trainComponentsBindingsFaultFrequenciesCols = ld.severalColumns(trainComponentsBindingsFaultFrequencies, colDict, "trainComponentsBindingsFaultFrequencies")
    print(trainComponentsBindingsFaultFrequenciesCols.head(10))
    compComponentsPointsCols = ld.severalColumns(compComponentsPoints, colDict, "compComponentsPoints")
    compComponentsFaultFrequenciesCols = ld.severalColumns(compComponentsFaultFrequencies, colDict, "compComponentsFaultFrequencies")
    print(compComponentsFaultFrequenciesCols.head(10))
    trainComponentsCols = ld.severalColumns(trainComponents, colDict, "trainComponents")
    trainsCols = ld.severalColumns(trains, colDict, "trains")
    # Промежуточный вывод таблиц, если необходимо
    ld.writeToFile(outFileName, compComponentsFaultFrequenciesCols, "compComponentsFaultFrequencies", 2000)
    ld.writeToFile(outFileName, trainComponentsBindingsFaultFrequenciesCols, "trainComponentsBindingsFaultFrequencies", 2000)
    del data, measures, points, trainComponentsBindingsPoints, trainComponentsBindingsFaultFrequencies, compComponentsPoints, compComponentsFaultFrequencies, trainComponents, trains
    # Строим соединение таблиц
    trainsAndComponents = pd.merge(trainsCols, trainComponentsCols, how="left", left_on="trains_idTrain", right_on="trainComponents_idTrain")
    trainsAndComponentsWithBindings = pd.merge(trainsAndComponents, trainComponentsBindingsPointsCols, how="left", left_on="trainComponents_idTrainComponent", right_on="trainComponentsBindingsPoints_idTrainComponent")
    trainsAndComponentsWithBindingsAndPoints = pd.merge(trainsAndComponentsWithBindings, compComponentsPointsCols, how="left", left_on=["trainComponents_idCompComponent", "trainComponentsBindingsPoints_CompIndex"], right_on=["compComponentsPoints_idComponent", "compComponentsPoints_CompIndex"])
    dataAndMesures = pd.merge(dataCols, measuresCols, how="left", left_on="data_idMeasure", right_on="measures_idMeasure")
    dataMesuresPoints = pd.merge(dataAndMesures, pointsCols, how="left", left_on="measures_idPoint", right_on="points_idPoint")
    dataMesuresPointsComponentsPoints = pd.merge(dataMesuresPoints, trainsAndComponentsWithBindingsAndPoints, how="left", left_on=["points_idPoint", "points_Direction"], right_on=["trainComponentsBindingsPoints_idPoint", "compComponentsPoints_Direction"])
    del trainsAndComponents, trainsAndComponentsWithBindings, trainsAndComponentsWithBindingsAndPoints, dataAndMesures, dataMesuresPoints
    # Поправим типы колонок
    
    # Группируем, чтобы получить временные ряды
    timeSeries = dict()
    gbDf = ld.filterByStrOr(dataMesuresPointsComponentsPoints, "trains_Name", ["5.5-1G11"])
    groupByColumns = ["trains_idTrain", "trainComponents_idTrainComponent", "points_idPoint", "points_Direction",
                      "measures_idMeasure", "measures_Name"]
    tsColumns = ["data_Date", "data_DynamicData"]
    for key, groupDf in gbDf.groupby(groupByColumns):
        timeSeries[key] = groupDf[tsColumns]
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
    ld.writeToFile(outFileName, dataMesuresPointsComponentsPoints, "5.5-1G11", None, pTable)

readTables()