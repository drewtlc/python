import warnings
warnings.filterwarnings("ignore")

import pymssql as ms
import pandas as pd
import functools
from functools import reduce
import re
import struct
import xml.etree.ElementTree as et
import datetime
import os
import time
import ast
import numpy as np

# Общий класс для работы с БД (соединение, чтение таблиц, фильтрация)
class LoadData:
    # Метод, используемый для создания объекта (contructor)
    def __init__(self):
        self.connection = None

    # Подключение к MSSQL
    def connect(self, server, username, password, database):
        conn = ms.connect(server, username, password, database)
        return conn

    # Выполнение SQL запроса к БД
    def readSql(self, sql):
        if self.connection is None:
            self.connection = self.connect("192.168.36.90", "drew", "drew", "UralKalii05042019")
        dataframe = pd.read_sql(sql, self.connection)
        return dataframe

    # Чтение таблицы из БД (через выполнение запроса)
    def readSqlTable(self, tableName, conditions="", limit=0):
        sql = "select " + ("" if limit <= 0 else "top " + str(limit)) + " * from " + tableName + ("" if conditions == "" else " where " + conditions)
        return self.readSql(sql)

    # Чтение таблицы из CSV файла
    def readCsvTable(self, fileName, converterCSV = None):
        df = pd.read_csv(fileName)
        if converterCSV != None:
            for col, func in converterCSV.items():
                df[col] = df[col].apply(func)
        return df

    # Запись таблицы в CSV файл
    def writeCsvTable(self, df, tableName):
        fileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), tableName + ".csv")
        if os.path.exists(fileName): os.remove(fileName)
        df.to_csv(fileName, index=False)
        return

    # Чтение данных из файла, а если его нет, то из таблицы
    def readSqlTableBuffered(self, tableName, processFunc = None, converterCSV = None):
        fileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), tableName + ".csv")
        df = pd.DataFrame()
        if os.path.exists(fileName):
            df = self.readCsvTable(fileName, converterCSV)
        else:
            df = self.readSqlTable(tableName)
            #df.to_csv(fileName, index=False)
            self.writeCsvTable(df, tableName)
        if processFunc != None:
            df = processFunc(df)
        return df

    # Наложение фильтра по значению колонки
    def filterByValue(self, df, colname, value):
        return df[df[colname].notna() & df[colname]==value]

    # Наложение фильтра по вхождению строк в значение колонки. Истина, если есть вхождение хотя бы одной строки.
    def filterByStrOr(self, df, colname, strings):
        return df[df[colname].notna() & reduce(lambda x,y: x|y, map(lambda s: df[colname].astype(str).str.contains(s, flags = re.IGNORECASE), strings))]

    # Наложение фильтра по вхождению строк в значение колонки. Истина, если есть вхождение всех строк.
    def filterByStrAnd(self, df, colname, strings):
        return df[df[colname].notna() & reduce(lambda x,y: x&y, map(lambda s: df[colname].astype(str).str.contains(s, flags = re.IGNORECASE), strings))]

    # Перевод бинарного поля в массив чисел float. На число выделяется 4 байта, которые меняют свой порядок на обратный перед переводом во float.
    def toFloatArray(self, binData):
        result=[]
        if (binData != None) & (type(binData) == bytes):
            blockSize = 4            
            for i in range(0,len(binData),blockSize):
                block = binData[i:i+blockSize]
                fl = struct.unpack(">f", block[::-1])
                result.append(fl[0])
        return result

    # Перевод текстового представления данных в сами данные (бинарные данные, списки, словари и т.д.)
    def evalStr(self, strVal):
        try:
            result = ast.literal_eval(strVal)
        except:
            result = None
        return result

    # Построение DataFrame по списку колонок keyColumns
    def createArrayDataFrame(self, df, keyColumns, arrayColumn):
        data = dict()
        maxlen = 0
        for _, row in df.iterrows():
            key = reduce(lambda s, k: (s if (s == "") else s + "_") + str(row[k]), keyColumns, "")
            data[key]=row[arrayColumn]
            maxlen = max(maxlen, len(row[arrayColumn]))
        for key, val in data.items():
            while len(val) < maxlen:
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
        with pd.ExcelWriter(path=fileName, mode=("a" if os.path.exists(fileName) else "w")) as writer:
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
    #   attributes  - список атрибутов тэга-строки для извлечения значений
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
        dicVal = dic[key]
        cols = list(map(lambda val: val[0], dicVal))
        types = list(map(lambda val: val[1], dicVal))
        dfCols = df[cols]
        for i in range(len(cols)):
            if types[i] != "":
                dfCols[cols[i]] = dfCols[cols[i]].astype(types[i])
        dfCols.columns = list(map(lambda el: key + "_" + str(el), cols))
        return dfCols

    def doPivotTable(self, df, pivotIndexColumns, pivotValuesColumns, filterColumn=None, filterValues=None):
        pivotDf = df[pivotIndexColumns + pivotValuesColumns]
        if filterColumn is not None:
            pivotDf = self.filterByStrOr(pivotDf, filterColumn, filterValues)
        pivotDf = pivotDf.sort_values(by=pivotIndexColumns + pivotValuesColumns)
        pTable = pd.pivot_table(pivotDf, index=pivotIndexColumns, values=pivotValuesColumns, aggfunc=[len,min,max])
        return pTable

    # Обработка таблицы с данными: бинарные данные переводятся в список вещественных чисел (нужно много ресурсов)
    def dataProcessing(self, dataDf, binColName = "DynamicData"):
        result = dataDf
        result[binColName + "Array"] = result[binColName].apply(self.toFloatArray)
        result[binColName + "Array" + "Len"] = result[binColName + "Array"].apply(len)
        result[binColName + "Array" + "Len"] = result[binColName + "Array" + "Len"].astype('int')
        result.drop([binColName], axis=1, inplace=True)
        return result

# Функция для оценки прошедшего времени
def elapsed(start = None):
    if start == None:
        print("0 sec")
        return time.time()
    else:
        current = time.time()
        print(str(current - start) + " sec")
        return current

# TODO
# 1. Визуализация одного измерения (визуализация в ширину, по строке)
# 2. Привязка оси Х к частотам
# 3. Построение временных рядов для одного среза: агрегат, компонент, точка, направление, измерение, название измерения
# 4. Визуализация одного/нескольких временных рядов (визуализация в длину, по столбцу)
# 5. Расчет характеристик связи временных рядов
# 6. Прогнозирование одного/нескольких временных рядов
# 7. Построение временных рядов для определенной частоты с учетом того, что она "плавает"

# Основная функция чтения и обработки данных
# ld - UKLoadData()
def readTables(ld):
    timepoint = time.time()
    # Выбираем данные таблиц
    print("Загрузка данных...")
    trains = ld.readSqlTableBuffered("dbo.Trains")                    # агрегаты (например, насосы)
    # trainMechanisms пока не используется
    #trainMechanisms = ld.readSqlTableBuffered("dbo.TrainMechanisms") # механизмы агрегата (например, для насосов это ЭД и сам насос)
    trainComponents = ld.readSqlTableBuffered("dbo.TrainComponents")  # компоненты конкретного агрегата (например, Статор А э/д, Якорь А э/д, Ротор э/д, Подшипник №1, Подшипник №2)
    # mechModels пока не используется
    #mechModels = ld.readSqlTableBuffered("dbo.Mech_Models")          # модели механизмов (например, для насоса в поле Keyphasors хранится параметр "Частота вращения насоса"; в поле StaticParameter - "Число лопаток рабочего колеса", Units="шт", ValueType="8"; в поле Points - Name="1", Description="Коренной подшипник насоса")
    compComponents = ld.readSqlTableBuffered("dbo.Comp_Components")   # общее описание компонента (в том числе Points, FaultFrequencies) (например, "Подшипник качения")
    points = ld.readSqlTableBuffered("dbo.Points")                    # точки, в которых проходят измерения
    measures = ld.readSqlTableBuffered("dbo.Measures")                # измерения
    # Все данные измерений
    #data = ld.readSqlTableBuffered("dbo.Data", ld.dataSQLProcessing, {"DynamicDataArray" : ld.toFloatList})     # данные измерений
    data = ld.readSqlTableBuffered("dbo.Data", None, {"DynamicData" : ld.evalStr})     # данные измерений
    timepoint = elapsed(timepoint)
    print("Объединение данных...")

    # Только самые новые из измерений
    #data = ld.readSql("select d.* from dbo.Data d \
    #                           left join (select [idMeasure], max([Date]) as lastDate from dbo.Data group by [idMeasure]) ld on (d.[idMeasure]=ld.[idMeasure] and d.[Date]=ld.[lastDate]) \
    #                           where ld.[idMeasure] is not null")
    
    # Обработка таблиц - нужно много ресурсов
    #   data["DynamicDataArray"] = data["DynamicData"].apply(ld.toFloatArray)
    #   data["DynamicDataArrayLen"] = data["DynamicDataArray"].apply(len).to_int()

    # Надо из таблиц TrainMechanisms, TrainComponents, Mech_Models, Comp_Components
    #   извлечь XML и разобрать на новые таблицы связей с точками измерений

    # trainMechanismsBindings пока не используется
    #trainMechanismsBindings = ld.createXmlDataFrame(trainMechanisms, "idTrainMech", "Bindings", "Points", ["CompIndex", "TrainIndex", "AdditionalData"])
    
    # связь компонентов конкретного агрегата и точек измерений (CompIndex="1" TrainIndex="41084")
    trainComponentsBindingsPoints = ld.createXmlDataFrame(trainComponents, "idTrainComponent", "Bindings", "Points", ["CompIndex", "TrainIndex", "AdditionalData"])
    trainComponentsBindingsPoints.columns = ["idTrainComponent", "CompIndex", "idPoint", "AdditionalData"]
    trainComponentsBindingsPoints = trainComponentsBindingsPoints.astype(int)

    # связь компонентов конкретного агрегата и частот отказа (CompIndex="1" Value="4.935600" Value2="1.000000" Value3="1.000000")
    trainComponentsBindingsFaultFrequencies = ld.createXmlDataFrame(trainComponents, "idTrainComponent", "Bindings", "FaultFreqValues", ["CompIndex", "Value", "Value2", "Value3"])
    trainComponentsBindingsFaultFrequencies.columns = ["idTrainComponent", "CompIndex", "Value", "Value2", "Value3"]
    trainComponentsBindingsFaultFrequencies = trainComponentsBindingsFaultFrequencies.astype({"idTrainComponent" : int, "CompIndex" : int})
    
    # mechModelsPoints пока не используется
    #mechModelsPoints = ld.createXmlDataFrame(mechModels, "idModel", "Points", "Points", ["Index", "Name", "Description"])
    
    # общее описание компонента и точек его измерения (Index="1" Name="Точка" Description="Точка установки подшипника" Direction="1" PickupType="1" Units="0")
    compComponentsPoints = ld.createXmlDataFrame(compComponents, "idComponent", "Points", "Points", ["Index", "Name", "Description", "Direction"])
    compComponentsPoints.columns = ["idComponent", "CompIndex", "Name", "Description", "Direction"]
    compComponentsPoints = compComponentsPoints.astype({"idComponent" : int, "CompIndex" : int, "Direction" : int})
    
    # общее описание компонента и частот отказа (Name="Fвн" Description="Частота внутреннего кольца" Code="1" Type="1" HarmType="0" Length="1" KeyIndex="1" FreqCode="-1" ParamIndex="-1" ParamIndex2="-1" ParamIndex3="-1" Value="1.000000" CoefValue2="1.000000" CoefValue3="1.000000" Add2KeyIndex="-1" Add2FreqCode="-1" Add2ParamIndex1="-1" Add2ParamIndex2="-1" Add2ParamIndex3="-1" Add2CoefValue1="0.000000" Add2CoefValue2="1.000000" Add2CoefValue3="1.000000" Length2="1" KeyIndex2="-1" FreqCode2="-1" MainHarm="1" Visible="1")
    compComponentsFaultFrequencies = ld.createXmlDataFrame(compComponents, "idComponent", "FaultFrequencies", "FaultFrequencies", ["Name", "Description", "Code", "Value", "CoefValue2", "CoefValue3"])
    compComponentsFaultFrequencies.columns = ["idComponent", "Name", "Description", "Code", "Value", "CoefValue2", "CoefValue3"]
    compComponentsFaultFrequencies = compComponentsFaultFrequencies.astype({"idComponent" : int, "Code" : int})

    # print(trainMechanismsBindings.head(10))
    # print(trainComponentsBindingsPoints.head(10))
    # print(mechModelsPoints.head(10))
    # print(compComponentsPoints.head(10))

    # Нужные для соединения колонки
    colDict = dict() # Ключ - имя dataframe, значение - список имен колонок с их типами
    colDict["data"]                           = [["idMeasure","int"], ["Date",""], ["DynamicData",""]]
    colDict["measures"]                       = [["idMeasure","int"], ["idPoint","int"], ["Name",""], ["Description",""]]
    colDict["points"]                         = [["idPoint","int"], ["idTrain","int"], ["Name",""], ["Description",""], ["Direction","int"]]
    colDict["trainComponentsBindingsPoints"]  = [["idTrainComponent","int"], ["CompIndex","int"], ["idPoint","int"], ["AdditionalData",""]]
    colDict["trainComponentsBindingsFaultFrequencies"] = [["idTrainComponent","int"], ["CompIndex","int"], ["Value",""], ["Value2",""], ["Value3",""]]
    colDict["compComponentsPoints"]           = [["idComponent","int"], ["CompIndex","int"], ["Name",""], ["Description",""], ["Direction","int"]]
    colDict["compComponentsFaultFrequencies"] = [["idComponent","int"], ["Name",""], ["Description",""], ["Code",""], ["Value",""], ["CoefValue2",""], ["CoefValue3",""]]
    colDict["trainComponents"]                = [["idTrainComponent","int"], ["idTrain","int"], ["idCompComponent","int"], ["Name",""], ["Description",""]]
    colDict["trains"]                         = [["idTrain","int"], ["Name",""], ["Description",""]]
    
    # Оставляем только часть колонок и переименовываем их
    dataCols = ld.severalColumns(data, colDict, "data")
    measuresCols = ld.severalColumns(measures, colDict, "measures")
    pointsCols = ld.severalColumns(points, colDict, "points")
    trainComponentsBindingsPointsCols = ld.severalColumns(trainComponentsBindingsPoints, colDict, "trainComponentsBindingsPoints")
    trainComponentsBindingsFaultFrequenciesCols = ld.severalColumns(trainComponentsBindingsFaultFrequencies, colDict, "trainComponentsBindingsFaultFrequencies")
    #print(trainComponentsBindingsFaultFrequenciesCols.head(10))
    compComponentsPointsCols = ld.severalColumns(compComponentsPoints, colDict, "compComponentsPoints")
    compComponentsFaultFrequenciesCols = ld.severalColumns(compComponentsFaultFrequencies, colDict, "compComponentsFaultFrequencies")
    #print(compComponentsFaultFrequenciesCols.head(10))
    trainComponentsCols = ld.severalColumns(trainComponents, colDict, "trainComponents")
    trainsCols = ld.severalColumns(trains, colDict, "trains")
    
    
    # Промежуточный вывод таблиц, если необходимо
    # Файл для записи результатов
    #outFileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pumps.xlsx")
    #if os.path.exists(outFileName): os.remove(outFileName)
    #ld.writeToFile(outFileName, compComponentsFaultFrequenciesCols, "compComponentsFaultFrequencies", 2000)
    #ld.writeToFile(outFileName, trainComponentsBindingsFaultFrequenciesCols, "trainComponentsBindingsFaultFrequencies", 2000)
    del data, measures, points, trainComponentsBindingsPoints, trainComponentsBindingsFaultFrequencies, compComponentsPoints, compComponentsFaultFrequencies, trainComponents, trains
    
    # Строим соединение таблиц
    trainsAndComponents = pd.merge(trainsCols, trainComponentsCols, how="left", left_on="trains_idTrain", right_on="trainComponents_idTrain")
    trainsAndComponentsWithBindings = pd.merge(trainsAndComponents, trainComponentsBindingsPointsCols, how="left", left_on="trainComponents_idTrainComponent", right_on="trainComponentsBindingsPoints_idTrainComponent")
    trainsAndComponentsWithBindingsAndPoints = pd.merge(trainsAndComponentsWithBindings, compComponentsPointsCols, how="left", left_on=["trainComponents_idCompComponent", "trainComponentsBindingsPoints_CompIndex"], right_on=["compComponentsPoints_idComponent", "compComponentsPoints_CompIndex"])
    dataAndMesures = pd.merge(dataCols, measuresCols, how="left", left_on="data_idMeasure", right_on="measures_idMeasure")
    dataMesuresPoints = pd.merge(dataAndMesures, pointsCols, how="left", left_on="measures_idPoint", right_on="points_idPoint")
    dataMesuresPointsComponentsPoints = pd.merge(dataMesuresPoints, trainsAndComponentsWithBindingsAndPoints, how="left", left_on=["points_idPoint", "points_Direction"], right_on=["trainComponentsBindingsPoints_idPoint", "compComponentsPoints_Direction"])
    del trainsAndComponents, trainsAndComponentsWithBindings, trainsAndComponentsWithBindingsAndPoints, dataAndMesures, dataMesuresPoints
    
    timepoint = elapsed(timepoint)
    print("Загрузка данных завершена")

    return dataMesuresPointsComponentsPoints

def writeTimeseriesFiles(ld, dataMesuresPointsComponentsPoints):
    print("Построение временных рядов...")
    timepoint = time.time()
    # Группируем, чтобы получить временные ряды
    timeSeries = dict()
    sumThreshold = 0.001 # отбрасывам измерения, где в данных одни нули или что-то к ним близкое
    lenThreshold = 10    # отбрасываем такие точки агрегатов, по которым малеькая статистика (малое число наблюдений)
    gbDf = ld.filterByStrOr(dataMesuresPointsComponentsPoints, "trains_Name", ["5.5-1G11"]) # Только данные насоса 5.5-1G11
    # Группировка: агрегат, компонент, точка, направление, измерение, название измерения
    groupByColumns = ["trains_idTrain", "trainComponents_idTrainComponent", "points_idPoint", "points_Direction", "measures_idMeasure", "measures_Name"]
    tsColumns = ["data_Date", "data_DynamicData"]
    for key, groupDf in gbDf.groupby(groupByColumns):
        oneSeriesDf = groupDf[tsColumns]
        oneSeriesDf = ld.dataProcessing(oneSeriesDf, "data_DynamicData")
        oneSeriesDf["sum_abs"] = oneSeriesDf["data_DynamicDataArray"].apply(lambda x: np.sum(np.abs(x)))
        oneSeriesDf = oneSeriesDf[(oneSeriesDf["data_DynamicDataArrayLen"]>0) & (oneSeriesDf["sum_abs"]>=sumThreshold)]
        if len(oneSeriesDf.index) >= lenThreshold:
            #oneSeriesDf["data_DynamicDataArray"] = oneSeriesDf["data_DynamicData"].apply(ld.toFloatArray)
            timeSeries[key] = oneSeriesDf
            keyInfo = ""
            for i in range(len(groupByColumns)):
                keyInfo = ("" if keyInfo == "" else keyInfo + ", ") + groupByColumns[i] + "=" + str(key[i])
            print(len(timeSeries.keys()), len(oneSeriesDf.index), np.max(oneSeriesDf["data_DynamicDataArrayLen"]), keyInfo)
            # Запись временных рядов в файл
            fileNameColumns = ["idTrain", "idTrainComponent", "idPoint", "Direction", "idMeasure"]
            fileName = ""
            for i in range(len(fileNameColumns)):
                fileName = ("" if fileName == "" else fileName + "_") + fileNameColumns[i] + "=" + str(int(key[i]))
            ld.writeCsvTable(oneSeriesDf, fileName)
            #print(timeSeries[key].head(10))

    timepoint = elapsed(timepoint)
    print("Построение временных рядов завершено")

    return

def doPivotExcelFile(ld, dataMesuresPointsComponentsPoints):
    print("Запись сводных Excel таблиц...")
    timepoint = time.time()
    # Файл для записи результатов
    outFileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pumps.xlsx")
    if os.path.exists(outFileName): os.remove(outFileName)

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

    timepoint = elapsed(timepoint)
    print("Запись сводных Excel таблиц завершена")

    return

def readTimeseriesFiles(ld, fileNamesList):
    timeSeries = dict()
    print("Чтение временных рядов...")
    timepoint = time.time()
    for fileName in fileNamesList:        
        key = list()
        for pair in fileName.split("_"):
            key.append(int(pair.split("=")[1]))
        df = ld.readCsvTable(fileName + ".csv", {"data_DynamicDataArray" : ld.evalStr})
        timeSeries[tuple(key)] = df


    timepoint = elapsed(timepoint)
    print("Чтение временных рядов завершено")

    return timeSeries

def main():
    ld = UKLoadData()
    # Чтение исходных данных (из БД или файлов) и формирование файлов с временными рядами
    #dataMesuresPointsComponentsPoints = readTables(ld)
    #writeTimeseriesFiles(ld, dataMesuresPointsComponentsPoints)
    # Чтение файлов с временными рядами
    timeSeries = readTimeseriesFiles(ld, 
    ['idTrain=2156_idTrainComponent=726_idPoint=41084_Direction=1_idMeasure=252050',
     'idTrain=2156_idTrainComponent=726_idPoint=41084_Direction=1_idMeasure=252051',
     'idTrain=2156_idTrainComponent=726_idPoint=41084_Direction=1_idMeasure=252052'])

    # Пока сводный файл не формируем
    #doPivotExcelFile(ld, dataMesuresPointsComponentsPoints)

    return

main()
