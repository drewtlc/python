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
    def readTable(self, tableName, conditions="", limit=0):
        sql = "select " + ("" if limit <= 0 else " limit " + limit) + " * from " + tableName + ("" if conditions == "" else " where " + conditions)
        return self.readSql(sql)
    
    # Чтение данных из файла, а если его нет, то из таблицы
    def readTableBuffered(self, tableName, funcSQL = None, funcCSV = None):
        fileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), tableName + ".csv")
        df = pd.DataFrame()
        if os.path.exists(fileName):
            df = pd.read_csv(fileName)
            if funcCSV != None:
                df = funcCSV(df)
        else:
            df = self.readTable(tableName)
            if funcSQL != None:
                df = funcSQL(df)
            df.to_csv(fileName, index=False)
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
        if type(binData)==bytes:
            blockSize = 4            
            for i in range(0,len(binData),blockSize):
                block = binData[i:i+blockSize]
                fl = struct.unpack(">f", block[::-1])
                result.append(fl[0])
        return result

    # Перевод строки в массив чисел float. Нужно при чтении массива из текстового файла
    def toFloatList(self, listInStr):
        result=[]
        listInStr = listInStr.replace("[","")
        listInStr = listInStr.replace("]","")
        listInStr = listInStr.replace(" ","")
        if listInStr != "":
            result = list(map(lambda x: float(x), listInStr.split(",")))
        return result

    # Расчет для массива чисел float суммы абсолютных значений
    def calcSumAbs(self, list):
        result=0
        for item in list:
            result += abs(item)
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

    def dataSQLProcessing(self, dataDf):
        result = dataDf
        result["DynamicDataArray"] = result["DynamicData"].apply(self.toFloatArray)
        result["DynamicDataArrayLen"] = result["DynamicDataArray"].apply(len)
        result["DynamicDataArrayLen"] = result["DynamicDataArrayLen"].astype('int')
        result.drop(['DynamicData'], axis=1, inplace=True)
        return result

    def dataCSVProcessing(self, dataDf):
        result = dataDf
        result["DynamicDataArray"] = result["DynamicDataArray"].apply(self.toFloatList)
        return result

#    def toString(self, floatArray):
#        return reduce(lambda s,f: (s if (s=="") else s+",") + str(f), floatArray, "")

def readTables():
    ld = UKLoadData()
    # Файл для разписи результатов
    outFileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pumps.xlsx")
    if os.path.exists(outFileName): os.remove(outFileName)
    # Выбираем данные таблиц
    trains = ld.readTableBuffered("dbo.Trains")                    # агрегаты (например, насосы)
    # trainMechanisms пока не используется
    #trainMechanisms = ld.readTableBuffered("dbo.TrainMechanisms") # механизмы агрегата (например, для насосов это ЭД и сам насос)
    trainComponents = ld.readTableBuffered("dbo.TrainComponents")  # компоненты конкретного агрегата (например, Статор А э/д, Якорь А э/д, Ротор э/д, Подшипник №1, Подшипник №2)
    # mechModels пока не используется
    #mechModels = ld.readTableBuffered("dbo.Mech_Models")          # модели механизмов (например, для насоса в поле Keyphasors хранится параметр "Частота вращения насоса"; в поле StaticParameter - "Число лопаток рабочего колеса", Units="шт", ValueType="8"; в поле Points - Name="1", Description="Коренной подшипник насоса")
    compComponents = ld.readTableBuffered("dbo.Comp_Components")   # общее описание компонента (в том числе Points, FaultFrequencies) (например, "Подшипник качения")
    points = ld.readTableBuffered("dbo.Points")                    # точки, в которых проходят измерения
    measures = ld.readTableBuffered("dbo.Measures")                # измерения
    # Все данные измерений
    convertersCSV = {"" : ld.toFloatList}
    data = ld.readTableBuffered("dbo.Data", ld.dataSQLProcessing, convertersCSV)     # данные измерений
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
    colDict["data"]                           = [["idMeasure","int"], ["Date",""], ["DynamicDataArray",""], ["DynamicDataArrayLen","int"]]
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
    print(trainComponentsBindingsFaultFrequenciesCols.head(10))
    compComponentsPointsCols = ld.severalColumns(compComponentsPoints, colDict, "compComponentsPoints")
    compComponentsFaultFrequenciesCols = ld.severalColumns(compComponentsFaultFrequencies, colDict, "compComponentsFaultFrequencies")
    print(compComponentsFaultFrequenciesCols.head(10))
    trainComponentsCols = ld.severalColumns(trainComponents, colDict, "trainComponents")
    trainsCols = ld.severalColumns(trains, colDict, "trains")
    
    # Промежуточный вывод таблиц, если необходимо
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
    
    # Поправим типы колонок
    
    # Группируем, чтобы получить временные ряды
    timeSeries = dict()
    gbDf = ld.filterByStrOr(dataMesuresPointsComponentsPoints, "trains_Name", ["5.5-1G11"])
    #print(dataMesuresPointsComponentsPoints.head(10))
    #print(gbDf.head(10))
    # Группировка: агрегат, компонент, точка, направление, измерение, название измерения
    groupByColumns = ["trains_idTrain", "trainComponents_idTrainComponent", "points_idPoint", "points_Direction", "measures_idMeasure", "measures_Name"]
    tsColumns = ["data_Date", "data_DynamicDataArray", "data_DynamicDataArrayLen"]
    for key, groupDf in gbDf.groupby(groupByColumns):
        oneSeriesDf = groupDf[tsColumns]
        oneSeriesDf["sum_abs"] = oneSeriesDf["data_DynamicDataArray"].apply(ld.calcSumAbs)
        oneSeriesDf = oneSeriesDf[(oneSeriesDf["data_DynamicDataArrayLen"]>0) & (oneSeriesDf["sum_abs"]>0)]
        if len(oneSeriesDf.index) > 0:
            #oneSeriesDf["data_DynamicDataArray"] = oneSeriesDf["data_DynamicData"].apply(ld.toFloatArray)
            timeSeries[key] = oneSeriesDf
            keyInfo = ""
            for i in range(len(groupByColumns)):
                keyInfo = ("" if keyInfo == "" else keyInfo + ", ") + groupByColumns[i] + "=" + str(key[i])
            print(keyInfo)
            print(timeSeries[key].head(10))

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
    #dataMesuresPointsComponentsPoints = dataMesuresPointsComponentsPoints.drop(["data_DynamicData"], axis=1)
    #ld.writeToFile(outFileName, dataMesuresPointsComponentsPoints, "5.5-1G11", None, pTable)

readTables()