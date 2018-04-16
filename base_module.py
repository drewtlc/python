# -*- coding: utf-8 -*-
import datetime

import xlrd
import functools
from functools import reduce

class Tools:
    def string(val):
        if type(val) is list:
            return list(map(Tools.string, val))
        else:
            return str(val).replace(".", ",") if (val is not None) else ''
    def withDelim(val, delim = ";"):
        if type(val) is list:
            return (reduce(lambda s, i: str(s) + delim + str(i), map(Tools.string, val))) if len(val)>0 else ""
        else:
            return val

    def listIndexes(listVal, add=0):
        return list(range(add, len(listVal) + add))

class RowsColsSettings:
    def __init__(self, строкаНачало, строкаКонец, столбецНачало, столбецКонец, строкаДанныхНачало =- 1, строкаДанныхКонец =- 1, столбецДанныхНачало =- 1, столбецДанныхКонец =- 1):
        self.rowFrom = строкаНачало
        self.rowTo = строкаКонец + 1    # +1 для правильного расчета правой границы через функцию range
        self.colFrom = столбецНачало
        self.colTo = столбецКонец + 1   # +1 для правильного расчета правой границы через функцию range
        self.rowDataFrom = строкаДанныхНачало if строкаДанныхНачало != -1 and строкаДанныхНачало != None else self.rowFrom
        self.rowDataTo = строкаДанныхКонец if строкаДанныхКонец != -1 and строкаДанныхКонец != None else self.rowTo
        self.colDataFrom = столбецДанныхНачало if столбецДанныхНачало != -1 and столбецДанныхНачало != None else self.colFrom
        self.colDataTo = столбецДанныхКонец if столбецДанныхКонец != -1 and столбецДанныхКонец != None else self.colTo


class Dictionary:
    def __init__(self):
        self.field = ""
        self.valuesDic = dict()

    def __str__(self):
        return "{поле=" + str(self.field) + ";значения=" + str(self.valuesDic) + "}"


class TablePoint:
    def __init__(self):
        self.row = 0
        self.col = 0
        self.value = ""

    def __str__(self):
        return "{(" + str(self.row) + ";" + str(self.col) + ");'" + str(self.value) + "'}"


class ExcelData:
    def __init__(self):
        self.dictionaries = list()
        self.tablePoints = list()

    def rng(fromNumber, toNumber, addList=[], removeList=[]):
        result = list(range(fromNumber, toNumber))
        result.append(toNumber)
        result.extend(addList)
        result = list(set(result) - set(removeList))
        result.sort()
        return result

    def __str__(self):
        dictionariesStr = reduce((lambda s, dicStr: s + "," + dicStr), map(str, self.dictionaries))
        tablePointsStr = reduce((lambda s, tableStr: s + "," + tableStr), map(str, self.tablePoints))
        return "{словари=" + str(dictionariesStr) + ";\nячейки=" + str(tablePointsStr) + "}"

    def readDataFile(fileName, dicSheetName, dataSheetName, rowsColsSettings):  # 116 - Столбец DL
        rowRange = range(rowsColsSettings.rowFrom, rowsColsSettings.rowTo)
        colRange = range(rowsColsSettings.colFrom, rowsColsSettings.colTo)
        result = ExcelData()
        book = xlrd.open_workbook(fileName, formatting_info=False)
        # Читаем справочники
        if dicSheetName != "":
            keyCol = 0
            valueCol = 1
            dicSheet = book.sheet_by_name(dicSheetName)
            dic = Dictionary()
            prevRowKey = ""
            for rowNum in range(dicSheet.nrows):
                row = dicSheet.row_values(rowNum)
                if row[keyCol] == "":
                    if dic.valuesDic:
                        result.dictionaries.append(dic)
                else:
                    if prevRowKey == "":  # Новый справочник
                        dic = Dictionary()
                        dic.field = row[keyCol]
                        dic.valuesDic = {}
                    else:
                        dic.valuesDic.update({row[keyCol]: row[valueCol]})
                prevRowKey = row[keyCol]
            if dic.valuesDic:
                result.dictionaries.append(dic)
        # Читаем данные
        dataSheet = book.sheet_by_name(dataSheetName)
        for rowNum in rowRange:
            row = dataSheet.row_values(rowNum - 1)  # -1 чтобы перевести индексы excel в индексы python
            for colNum in colRange:
                tablePoint = TablePoint()
                tablePoint.row = rowNum
                tablePoint.col = colNum
                tablePoint.value = '' if len(row) < colNum else row[colNum - 1]  # -1 чтобы перевести индексы excel в индексы python
                result.tablePoints.append(tablePoint)
        return result


class DataPoint:
    def __init__(self):
        self.row = 0
        self.col = 0
        self.value = None
        self.isFloat = False
        self.attributes = dict()

    def setValue(self, value):
        try:
            self.value = float(str(value))
            self.isFloat = True
        except ValueError:
            self.value = value
            self.isFloat = False
        if self.isFloat == False:
            try:
                self.value = float(str(value).replace(",","."))
                self.isFloat = True
            except ValueError:
                self.value = value
                self.isFloat = False
        return

    def toStr(self):
        return "(" + str(self.row) + ";" + str(self.col) + ");" + ("'" if not self.isFloat else "") + str(
            self.value) + ("'" if not self.isFloat else "")

    def __str__(self):
        return "{" + self.toStr() + "}"
        # return "{"+self.toStr()+";"+str(self.attributes)+"}"

    def toStrWithAttr(point):
        return "{" + point.toStr() + ";" + str(point.attributes) + "}"

    def makeDataPoints(excelData, rowsColsSettings, dateCols,
                       colAttrNames={1: 'Тип исследования', 2: 'Группа показателей', 3: 'Возрасты теста',
                                     4: 'Показатель'}, colAttrLambdas={}, fillAttrBlanks = True):
        result = []
        dateColsSet = set(map(lambda s: str(s).upper(), dateCols))
        dataRows = range(rowsColsSettings.rowDataFrom, rowsColsSettings.rowDataTo)
        dataCols = range(rowsColsSettings.colDataFrom, rowsColsSettings.colDataTo)
        dataPointDic = {}  # Словарь для точек данных
        excelDataMatrix = {}  # Словарь для данных Excel
        allRowsSet = set()  # Множество всех строк в excelData
        allColsSet = set()  # Множество всех столбцов в excelData
        dataRowsList = list(set(dataRows))
        dataColsList = list(set(dataCols))
        dataRowsList.sort()
        dataColsList.sort()
        # Строим словарь для данных Excel, чтобы удобно было обращаться к ячейкам. Ключ - пара из строки и столбца
        for tablePoint in excelData.tablePoints:
            excelDataMatrix[tuple([tablePoint.row, tablePoint.col])] = tablePoint.value
            allRowsSet.add(tablePoint.row)
            allColsSet.add(tablePoint.col)
        # Строим словари атрибутов. Сначала надо определить строку с заголовкаси колонок
        captionRow = dataRowsList[0] - 1  # Строка с заголовками
        # Проверим, что такой номер строки есть во множестве всех номеров. Если нет, то будем искать строку выше
        while not (captionRow in allRowsSet) and (captionRow > 0):
            captionRow = captionRow - 1
        if captionRow == 0:
            return
        # Атрибуты по номеру строки
        rowAttrDic = {}  # Словарь с атрибутами. Ключ - номер строки, потом словарь из названия атрибута и его значения
        attrColsList = list(allColsSet - set(dataColsList))
        attrColsList.sort()
        for rowCol in [tuple([row, col]) for row in dataRowsList for col in attrColsList]:
            rowDic = rowAttrDic.get(rowCol[0], dict())
            caption = excelDataMatrix[tuple([captionRow, rowCol[1]])]
            value = excelDataMatrix[rowCol]
            if (caption.upper() in dateColsSet) and (value != ""):
                tempDate = datetime.datetime(1900, 1, 1)
                deltaDays = datetime.timedelta(days=int(value))
                #secs = (int((value % 1) * 86400) - 60)
                #deltaSeconds = datetime.timedelta(seconds=secs)
                #TheTime = (tempDate + deltaDays + deltaSeconds)
                value = (tempDate + deltaDays) # + deltaSeconds
            dics = list(filter((lambda x: x.field == caption),
                               excelData.dictionaries))  # Ищем значение заголовка с списке словарей Excel
            if len(dics) > 0:
                value = dics[0].valuesDic.get(value,
                                              value)  # Нашли словарь по значению caption. Если в нём есть ключ value, то вернем значение, если нет, то само value
            rowDic[caption if caption != "" else "[col" + str(rowCol[1]) + "]"] = value
            rowAttrDic[rowCol[0]] = rowDic
        # Атрибуты по номеру столбца
        colAttrDic = {}  # Словарь с атрибутами. Ключ - номер столбца, потом словарь из названия атрибута и его значения
        # colAttrNames = {1 : 'Тип исследования', 2 : 'Группа показателей', 3 : 'Возрасты теста', 4 : 'Показатель'}
        attrRowsList = list(allRowsSet - set(dataRowsList))
        attrRowsList.sort()
        for rowCol in [tuple([row, col]) for row in attrRowsList for col in dataColsList]:
            colDic = colAttrDic.get(rowCol[1], dict())
            caption = colAttrNames.get(rowCol[0], "")
            value = excelDataMatrix[rowCol]
            if rowCol[0] in colAttrLambdas:
                value = colAttrLambdas.get(rowCol[0])(value)
            colDic[caption if caption != "" else "[row" + str(rowCol[0]) + "]"] = value
            colAttrDic[rowCol[1]] = colDic
        # Для объединенных ячеек Excel сохраяет только первое значение. Пропуски надо дополнить
        if fillAttrBlanks == True:
            for attrName in colAttrNames.values():
                colNumbers = list(colAttrDic.keys())
                colNumbers.sort()
                for i in range(len(colNumbers)):
                    col = colNumbers[i]
                    colAttrValue = colAttrDic[col][attrName]
                    if colAttrValue == "":
                        prevCol = colNumbers[i - 1]
                        colAttrPrevValue = colAttrDic[prevCol][attrName]
                        colAttrDic[col][attrName] = colAttrPrevValue
        # Строим словарь точек данных. Ключ - пара из строки и столбца
        for rowCol in [tuple([row, col]) for row in dataRowsList for col in dataColsList]:
            value = excelDataMatrix[rowCol]
            dataPoint = DataPoint()
            # Заполним строку, столбец, значение
            dataPoint.row = rowCol[0]
            dataPoint.col = rowCol[1]
            dataPoint.setValue(value)
            # Заполним атрибуты по строке
            dataPoint.attributes = rowAttrDic[rowCol[0]].copy()
            # Заполним атрибуты по столбцу
            dataPoint.attributes.update(colAttrDic[rowCol[1]].copy())
            dataPointDic[rowCol] = dataPoint
        result = list(dataPointDic.values())
        return result


class GroupedDataPoints:
    def __init__(self):
        self.attrGroup = list()  # [Пол,Возраст]
        self.valueDic = dict()  # {ж,7}={ТД1,ТД2}, {ж,8}={ТД3,ТД4}

    def __str__(self):
        keys = list(self.valueDic.keys())
        keys.sort()
        mapLambda = lambda key: str(key) + '=' + str(len(self.valueDic[key]))
        reduceLambda = lambda s, nextS: s + ";\n" + nextS
        return "{" + str(self.attrGroup) + "\n" + reduce(reduceLambda, map(mapLambda, keys)) + "}"

    def groupByList(dataPoints, groupList):  # Переписать на map-reduce
        result = GroupedDataPoints()
        result.attrGroup = groupList.copy()
        for dataPoint in dataPoints:
            key = tuple(map((lambda attr: dataPoint.attributes.get(attr, '')), groupList))
            result.valueDic.setdefault(key, list()).append(dataPoint)
        return result

    def debug(self, fileName=""):
        mapLambda = lambda dp: dp.attributes.keys()
        reduceLambda = lambda l, items: list(l) + list(items)
        attrKeys = reduce(reduceLambda, map(mapLambda, reduce(reduceLambda, self.valueDic.values())))
        attrKeys = list(set(attrKeys))
        attrKeys.sort()
        reduceStrLambda = lambda s, nextS, delim: str(s) + str(delim) + str(nextS)
        captions = self.attrGroup + attrKeys + ["row", "col", "value", "isFloat"]
        strList = [reduce(functools.partial(reduceStrLambda, delim=";"), captions)]
        keys = list(self.valueDic.keys())
        keys.sort()
        for key in keys:
            for dataPoint in self.valueDic[key]:
                l = list(map(lambda s: "<" + str(s) + ">", list(key)))
                for attr in attrKeys:
                    l += [dataPoint.attributes.get(attr, "")]
                l += [dataPoint.row, dataPoint.col, dataPoint.value, dataPoint.isFloat]
                strList += [reduce(functools.partial(reduceStrLambda, delim=";"), l)]
        result = reduce(functools.partial(reduceStrLambda, delim="\n"), strList)
        if fileName == "":
            print(result)
        return

    def buildColDict(self, attrName):
        result = dict()
        for dataPoints in self.valueDic.values():
            for dataPoint in dataPoints:
                if attrName in dataPoint.attributes:
                    result[dataPoint.attributes.get(attrName)] = dataPoint.col
        return result


class GroupedPoints:
    def __init__(self):
        self.attrGroup = list()  # [Пол,Возраст]
        self.valueDic = dict()  # {ж,7}=ChildrenValue, {ж,8}=ChildrenValue

    def __str__(self):
        keys = list(self.valueDic.keys())
        keys.sort()
        mapLambda = lambda i: Tools.string(keys[i]) + '=' + Tools.string(self.valueDic[keys[i]])
        reduceLambda = lambda s, nextS: s + ";\n" + nextS
        return "{" + str(self.attrGroup) + "\n" + reduce(reduceLambda, map(mapLambda, range(len(keys)))) + "}"

    def saveToFile(self, fileName, captions=[], delim=";"):
        keys = list(self.valueDic.keys())
        keys.sort()
        reduceLambda = lambda s, nextS: Tools.string(s) + delim + Tools.string(nextS)
        #mapLambda = lambda i: Tools.string(reduce(reduceLambda, list(keys[i]))) + delim + Tools.string(reduce(reduceLambda, list(self.valueDic[keys[i]])))
        mapLambda = lambda i: Tools.string(reduce(reduceLambda, list(keys[i]))) + delim + Tools.string(self.valueDic[keys[i]])
        reduceStrLambda = lambda s, nextS: s + "\n" + nextS
        result = ("" if len(captions)==0 else reduce(reduceLambda, captions)) + "\n" + reduce(reduceStrLambda, map(mapLambda, range(len(keys))))
        with open(fileName, "w") as file:
            file.write(result)
        return

    def dataPointsValues(groupedDataPoints, filterLambda = None):  # Из списка точек данных строим список числовых значений
        result = GroupedPoints()
        result.attrGroup = groupedDataPoints.attrGroup.copy()
        for key, value in groupedDataPoints.valueDic.items():
            if filterLambda == None:
                filteredList = list(filter(lambda dp: dp.isFloat == True, value))
            else:
                filteredList = list(filter(filterLambda, value))
            result.valueDic[key] = list(map(lambda dp: dp.value, filteredList))
        return result

    def dataPointsNums(groupedDataPoints, filterLambda = None):  # Из списка точек данных строим список числовых значений
        result = GroupedPoints()
        result.attrGroup = groupedDataPoints.attrGroup.copy()
        for key, value in groupedDataPoints.valueDic.items():
            if filterLambda == None:
                filteredList = list(filter(lambda dp: dp.isFloat == True, value))
            else:
                filteredList = list(filter(filterLambda, value))
            result.valueDic[key] = list(map(lambda dp: int(dp.attributes.get("№№")), filteredList))
        return result

    def dataPointsAttrValue(groupedDataPoints, attrName):  # Из списка точек данных строим множество значений атрибута
        result = GroupedPoints()
        result.attrGroup = groupedDataPoints.attrGroup.copy()
        for key, value in groupedDataPoints.valueDic.items():
            attrValuesSet = set(map(lambda dp: dp.attributes.get(attrName, ""), value))
            attrValuesSet = attrValuesSet.difference(set(""))
            result.valueDic[key] = attrValuesSet
        return result

        # result = set()
        # for key, value in groupedDataPoints.valueDic.items():
        #     attrValues = list(map(lambda dp: dp.attributes.get(attrName, ''), value))
        #     # print(attrValues)
        #     attrValuesSet = set(attrValues)
        #     result = result.union(attrValuesSet)
        # result = result.difference(set(''))
        # return result

    # def kstest(groupedDataPoints):
    #     groupedPointsValues = GroupedPoints.groupedPointsValues(groupedDataPoints)
    #     result = GroupedPoints()
    #     result.attrGroup = groupedPointsValues.attrGroup.copy() + ["KS D", "KS p-value"]
    #     for key, numbers in groupedPointsValues.valueDic.items():
    #         result.valueDic[key] = list(scipy.stats.kstest(numbers, "norm"))
    #     return result

    # def shapiro(groupedDataPoints):
    #     groupedPointsValues = GroupedPoints.groupedPointsValues(groupedDataPoints)
    #     result = GroupedPoints()
    #     result.attrGroup = groupedPointsValues.attrGroup.copy() + ["W", "p-value", "Distrib"]
    #     for key, numbers in groupedPointsValues.valueDic.items():
    #         tResult = list(scipy.stats.shapiro(numbers))
    #         result.valueDic[key] = tResult + ["normal" if tResult[1] > 0.05 else "not normal"]
    #     return result

    # def describe(groupedDataPoints):
    #     groupedPointsValues = GroupedPoints.groupedPointsValues(groupedDataPoints)
    #     result = GroupedPoints()
    #     result.attrGroup = groupedPointsValues.attrGroup.copy()  # + ["KS D", "KS p-value"]
    #     for key, numbers in groupedPointsValues.valueDic.items():
    #         result.valueDic[key] = list(scipy.stats.describe(numbers))
    #     return result
