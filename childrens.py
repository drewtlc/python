# -*- coding: utf-8 -*-

# TODO:
# +1. Вывод списков точек данных в файл с разделителями для отладки
# 2. Вывод результатов расчета процентилей в файл с разделителями
# +3. Анализ гипотезы о нормальном законе распределения для списков точек данных
# 4. Построение графиков

import xlrd
import numpy
import functools
from functools import reduce
import scipy.stats

class Tools:
    def string(val):
        if type(val) is list:
            return list(map(Tools.string, val))
        else:
            return str(val).replace(".",",")

class Dictionary:
    def __init__(self):
        self.field     = ""
        self.valuesDic = dict()
    def __str__(self):
        return "{поле="+str(self.field)+";значения="+str(self.valuesDic)+"}"

class TablePoint:
    def __init__(self):
        self.row   = 0
        self.col   = 0
        self.value = ""
    def __str__(self):
        return "{("+str(self.row)+";"+str(self.col)+");'"+str(self.value)+"'}"

class ExcelData:
    def __init__(self):
        self.dictionaries = list()
        self.tablePoints  = list()
    def rng(fromNumber, toNumber, addList = [], removeList = []):
        result = list(range(fromNumber, toNumber))
        result.append(toNumber)
        result.extend(addList)
        result = list(set(result) - set(removeList))
        result.sort()
        return result
    def __str__(self):
        dictionariesStr = reduce((lambda s, dicStr: s + "," + dicStr), map(str, self.dictionaries))
        tablePointsStr = reduce((lambda s, tableStr: s + "," + tableStr), map(str, self.tablePoints))
        return "{словари="+str(dictionariesStr)+";\nячейки="+str(tablePointsStr)+"}"
    def readDataFile(fileName, dicSheetName = "Коды", dataSheetName = "Рез-ты 16-17", rowRange = range(1, 2244), colRange = range(1, 117)): # 116 - Столбец DL
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
	                if prevRowKey == "": # Новый справочник
	                    dic = Dictionary()
	                    dic.field = row[keyCol]
	                    dic.valuesDic = {}
	                else:
	                    dic.valuesDic.update({row[keyCol]:row[valueCol]})
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
                tablePoint.value = '' if len(row)<colNum else row[colNum - 1]  # -1 чтобы перевести индексы excel в индексы python
                result.tablePoints.append(tablePoint)
        return result

class DataPoint:
    def __init__(self):
        self.row        = 0
        self.col        = 0
        self.value      = None
        self.isFloat    = False
        self.attributes = dict()
    def setValue(self, value):
        try:
            self.value = float(value)
            self.isFloat = True
        except ValueError:
            self.value = value
            self.isFloat = False
        return
    def toStr(self):
        return "("+str(self.row)+";"+str(self.col)+");"+("'" if not self.isFloat else "")+str(self.value)+("'" if not self.isFloat else "")
    def __str__(self):
        return "{"+self.toStr()+"}"
        #return "{"+self.toStr()+";"+str(self.attributes)+"}"
    def toStrWithAttr(point):
        return "{"+point.toStr()+";"+str(point.attributes)+"}"
    def makeDataPoints(excelData, dataRows = [], dataCols = [], colAttrNames = {1 : 'Тип исследования', 2 : 'Группа показателей', 3 : 'Возрасты теста', 4 : 'Показатель'}):
        result = []
        dataPointDic = {}     # Словарь для точек данных
        excelDataMatrix = {}  # Словарь для данных Excel
        allRowsSet = set()    # Множество всех строк в excelData
        allColsSet = set()    # Множество всех столбцов в excelData
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
        captionRow = dataRowsList[0] - 1 # Строка с заголовками
        while not (captionRow in allRowsSet) and (captionRow > 0): # Проверим, что такой номер строки есть во множестве всех номеров. ЕСли нет, то будем искать строку выше
            captionRow = captionRow - 1
        if captionRow == 0:
            return
        # Атрибуты по номеру строки
        rowAttrDic = {}       # Словарь с атрибутами. Ключ - номер строки, потом словарь из названия атрибута и его значения
        attrColsList = list(allColsSet-set(dataColsList))
        attrColsList.sort()
        for rowCol in [tuple([row,col]) for row in dataRowsList for col in attrColsList]:
            rowDic = rowAttrDic.get(rowCol[0], dict())
            caption = excelDataMatrix[tuple([captionRow, rowCol[1]])]
            value = excelDataMatrix[rowCol]
            dics = list(filter((lambda x: x.field == caption), excelData.dictionaries)) # Ищем значение заголовка с списке словарей Excel
            if len(dics) > 0:
                value = dics[0].valuesDic.get(value, value)     # Нашли словарь по значению caption. Если в нём есть ключ value, то вернем значение, если нет, то само value
            rowDic[caption if caption!="" else "[col"+str(rowCol[1])+"]"] = value
            rowAttrDic[rowCol[0]] = rowDic
        # Атрибуты по номеру столбца
        colAttrDic = {}       # Словарь с атрибутами. Ключ - номер столбца, потом словарь из названия атрибута и его значения
        #colAttrNames = {1 : 'Тип исследования', 2 : 'Группа показателей', 3 : 'Возрасты теста', 4 : 'Показатель'}
        attrRowsList = list(allRowsSet-set(dataRowsList))
        attrRowsList.sort()
        for rowCol in [tuple([row,col]) for row in attrRowsList for col in dataColsList]:
            colDic = colAttrDic.get(rowCol[1], dict())
            caption = colAttrNames.get(rowCol[0], "")
            value = excelDataMatrix[rowCol]
            colDic[caption if caption!="" else "[row"+str(rowCol[0])+"]"] = value
            colAttrDic[rowCol[1]] = colDic
        # Для объединенных ячеек Excel сохраяет только первое значение. Пропуски надо дополнить
        for attrName in colAttrNames.values():
            colNumbers = list(colAttrDic.keys())
            colNumbers.sort()
            for i in range(len(colNumbers)):
                col = colNumbers[i]
                colAttrValue = colAttrDic[col][attrName]
                if colAttrValue == "":
                    prevCol = colNumbers[i-1]
                    colAttrPrevValue = colAttrDic[prevCol][attrName]
                    colAttrDic[col][attrName] = colAttrPrevValue
        # Строим словарь точек данных. Ключ - пара из строки и столбца
        for rowCol in [tuple([row,col]) for row in dataRowsList for col in dataColsList]:
            value = excelDataMatrix[rowCol]
            dataPoint = DataPoint()
            # Заполним строку, столбец, значение
            dataPoint.row = rowCol[0]
            dataPoint.col = rowCol[1]
            dataPoint.setValue(value);
            # Заполним атрибуты по строке
            dataPoint.attributes = rowAttrDic[rowCol[0]].copy()
            # Заполним атрибуты по столбцу
            dataPoint.attributes.update(colAttrDic[rowCol[1]].copy())
            dataPointDic[rowCol] = dataPoint
        result = list(dataPointDic.values())
        return result

class CustomAttribute:
    def __init__(self, customAttrName, attrListToProcess, attrValueToSearch):
        self.customAttrName    = customAttrName
        self.attrListToProcess = attrListToProcess
        self.attrValueToSearch = attrValueToSearch
        self.mapLambda = lambda attr, dp: 1 if (dp.attributes.get(attr,'') == self.attrValueToSearch) else 0
    def addCustomAttributeOR(self, dataPoints):
        reduceLambda = lambda val, listVal: min(val + listVal, 1)
        for dataPoint in dataPoints:
            dataPoint.attributes[self.customAttrName] = reduce(reduceLambda, map(functools.partial(self.mapLambda, dp=dataPoint), self.attrListToProcess))
    def addCustomAttributeAND(self, dataPoints):
        reduceLambda = lambda val, listVal: min(val * listVal, 1)
        for dataPoint in dataPoints:
            dataPoint.attributes[self.customAttrName] = reduce(reduceLambda, map(functools.partial(self.mapLambda, dp=dataPoint), self.attrListToProcess))

class GroupedDataPoints:
    def __init__(self):
        self.attrGroup = list()     # [Пол,Возраст]
        self.valueDic  = dict()     # {ж,7}={ТД1,ТД2}, {ж,8}={ТД3,ТД4}
    #def makeFlat(self, parentAttrGroup = [], parentAttrGroupValues = [], topLevel=True):
    #    result = GroupedDataPoints()
    #    #_строки = ''
    #    parentAttrGroup += self.attrGroup   # [Пол,Возраст]
    #    # Проверим, последний это уровень группировки или нет
    #    for item in self.valueDic.items():
    #        #_списокЗначенийПолейГруппировки = _ключЗначение[0]                
    #        attrGroupValues = parentAttrGroupValues.copy()
    #        attrGroupValues += item[0]              # {ж,6}
    #        dic = item[1]                           # {[РекГр1],{[Циклич]={ТД1,ТД2}}}
    #        if type(dic) is GroupedDataPoints:
    #            result = dic.makeFlat(parentAttrGroup, attrGroupValues, False)
    #        else:
    #            result.valueDic[tuple(attrGroupValues)] = dic
    #    if (topLevel == True):
    #        result.attrGroup = parentAttrGroup
    #    return result
    def __str__(self):
        keys = list(self.valueDic.keys());
        keys.sort()
        mapLambda = lambda key: str(key) + '=' + str(len(self.valueDic[key]))
        reduceLambda = lambda s, nextS: s + ";\n" + nextS
        return "{" + str(self.attrGroup) + "\n" + reduce(reduceLambda, map(mapLambda, keys)) + "}"
    def groupByList(dataPoints, groupList): # Переписать на map-reduce
        result = GroupedDataPoints()
        result.attrGroup = groupList.copy()        
        for dataPoint in dataPoints:
            key = tuple(map((lambda attr: dataPoint.attributes.get(attr,'')), groupList))
            result.valueDic.setdefault(key, list()).append(dataPoint)
        return result
    def debug(self, fileName = ""):
        mapLambda = lambda dp: dp.attributes.keys()
        reduceLambda = lambda l, items: list(l) + list(items)
        attrKeys = reduce(reduceLambda, map(mapLambda, reduce(reduceLambda, self.valueDic.values())))
        attrKeys = list(set(attrKeys))
        attrKeys.sort()
        reduceStrLambda = lambda s, nextS, delim: str(s) + str(delim) + str(nextS)
        captions = self.attrGroup + attrKeys + ["row", "col", "value", "isFloat"]
        strList = [reduce(functools.partial(reduceStrLambda, delim=";"), captions)]
        keys = list(self.valueDic.keys());
        keys.sort()
        for key in keys:
            for dataPoint in self.valueDic[key]:
                l = list(map(lambda s: "<"+str(s)+">", list(key)))
                for attr in attrKeys:
                    l += [dataPoint.attributes.get(attr, "")]
                l += [dataPoint.row, dataPoint.col, dataPoint.value, dataPoint.isFloat]
                strList += [reduce(functools.partial(reduceStrLambda, delim=";"), l)]
        result = reduce(functools.partial(reduceStrLambda, delim="\n"), strList)
        if fileName == "":
            print(result)
        return

class GroupedPoints:
    def __init__(self):
        self.attrGroup = list()     # [Пол,Возраст]
        self.valueDic  = dict()     # {ж,7}={1,2}, {ж,8}={3,4}
    def __str__(self):
        keys = list(self.valueDic.keys());
        keys.sort()
        mapLambda = lambda i: str(keys[i]) + '=' + str(self.valueDic[keys[i]])
        reduceLambda = lambda s, nextS: s + ";\n" + nextS
        return "{" + str(self.attrGroup) + "\n" + reduce(reduceLambda, map(mapLambda, range(len(keys)))) + "}"
    def dataPointsWithValue(groupedDataPoints): # Из списка точек данных строим список числовых значений
        result = GroupedPoints()
        result.attrGroup = groupedDataPoints.attrGroup.copy()
        for item in groupedDataPoints.valueDic.items():
            result.valueDic[item[0]] = list(map(lambda dp: dp.value, list(filter(lambda dp: dp.isFloat == True, item[1]))))
        return result
    def percentiles(groupedDataPoints, percentiles):
        # Из сгруппированных точек строим сгруппированные списки числовых значений
        groupedPointsWithValue = GroupedPoints.dataPointsWithValue(groupedDataPoints)
        result = GroupedPoints()
        result.attrGroup = groupedPointsWithValue.attrGroup.copy() + percentiles.copy() + ["count"]
        for item in groupedPointsWithValue.valueDic.items():
            numbers = groupedPointsWithValue.valueDic[item[0]]
            result.valueDic[item[0]] = (list() if len(numbers)==0 else list(numpy.percentile(numpy.array(numbers), percentiles)))+[len(numbers)]
        return result
    def kstest(groupedDataPoints):
        groupedPointsWithValue = GroupedPoints.dataPointsWithValue(groupedDataPoints)
        result = GroupedPoints()
        result.attrGroup = groupedPointsWithValue.attrGroup.copy() + ["KS D", "KS p-value"]
        for item in groupedPointsWithValue.valueDic.items():
            numbers = groupedPointsWithValue.valueDic[item[0]]
            result.valueDic[item[0]] = list(scipy.stats.kstest(numbers, "norm"))
        return result
    def shapiro(groupedDataPoints):
        groupedPointsWithValue = GroupedPoints.dataPointsWithValue(groupedDataPoints)
        result = GroupedPoints()
        result.attrGroup = groupedPointsWithValue.attrGroup.copy() + ["W", "p-value", "Distrib"]
        for item in groupedPointsWithValue.valueDic.items():
            numbers = groupedPointsWithValue.valueDic[item[0]]
            tResult = list(scipy.stats.shapiro(numbers))
            result.valueDic[item[0]] = tResult + ["normal" if tResult[1]>0.05 else "not normal"]
        return result
    def describe(groupedDataPoints):
        groupedPointsWithValue = GroupedPoints.dataPointsWithValue(groupedDataPoints)
        result = GroupedPoints()
        result.attrGroup = groupedPointsWithValue.attrGroup.copy() # + ["KS D", "KS p-value"]
        for item in groupedPointsWithValue.valueDic.items():
            numbers = groupedPointsWithValue.valueDic[item[0]]
            result.valueDic[item[0]] = list(scipy.stats.describe(numbers))
        return result

# Основная программа
def main():
    # Читаем из файла
    allData = ExcelData.readDataFile('ОБЩИЙ ИТОГ 2016-17_01.12_v8.xlsx', 'Коды', 'Рез-ты 16-17', ExcelData.rng(1, 2244), ExcelData.rng(1, 117))
    print("Прочитано excel ячеек: "+str(len(allData.tablePoints)))
    # Переводим ячейки в точки с атрибутами
    dataPoints = DataPoint.makeDataPoints(allData, ExcelData.rng(5, 2244), ExcelData.rng(45, 115), {1 : 'Тип исследования', 2 : 'Группа показателей', 3 : 'Возрасты теста', 4 : 'Показатель'})
    print("Обработано точек данных: "+str(len(dataPoints)))
    # Циклические
    attr1 = CustomAttribute("Рек Циклические", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Циклические")
    attr1.addCustomAttributeOR(dataPoints);
    # Командные игровые
    attr2 = CustomAttribute("Рек Командные игровые", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Командные игровые")
    attr2.addCustomAttributeOR(dataPoints);
    # Игровые
    attr3 = CustomAttribute("Рек Игровые", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Игровые")
    attr3.addCustomAttributeOR(dataPoints);
    # Группируем по атрибутам "Пол", "Возраст (год)", "Показатель"
    #groupedDataAll = GroupedDataPoints.groupByList(dataPoints, ["Пол", "Возраст (год)", "Рек Циклические"])
    groupedDataAll = GroupedDataPoints.groupByList(dataPoints, ["Пол", "Возраст (год)", "Показатель"])
    groupedDataGr1 = GroupedDataPoints.groupByList(dataPoints, ["Пол", "Возраст (год)", "Показатель", "Рек гр 1"])
    #print(groupedDataAll)
    #print(groupedDataGr1)
    percentiles = [10, 25, 50, 75, 90]
    percDataAll = GroupedPoints.percentiles(groupedDataAll, percentiles)
    percDataGr1 = GroupedPoints.percentiles(groupedDataGr1, percentiles)
    print(percDataAll)
    print(percDataGr1)
    return

class CalcResult:
    percentiles = [25, 50, 75]
    def __init__(self):
        self.kstestM = None
        self.kstestW = None        
        self.shapiroM  = None
        self.shapiroW  = None
        self.normaltestM = None
        self.normaltestW = None
        self.describeM = None
        self.describeW = None
        self.percentilesM = None
        self.percentilesW = None
        self.ttest = None
        self.mannwhitneyu = None
        self.diagramM = None
        self.diagramW = None
    def __str__(self):
        result = ""
        result += "kstestM      = "+str(self.kstestM)+"\n"
        result += "kstestW      = "+str(self.kstestW)+"\n"
        result += "shapiroM     = "+str(self.shapiroM)+"\n"
        result += "shapiroW     = "+str(self.shapiroW)+"\n"
        result += "normaltestM  = "+str(self.normaltestM)+"\n"
        result += "normaltestW  = "+str(self.normaltestW)+"\n"
        result += "describeM    = "+str(self.describeM)+"\n"
        result += "describeW    = "+str(self.describeW)+"\n"
        result += "percentilesM = "+str(self.percentilesM)+"\n"
        result += "percentilesW = "+str(self.percentilesW)+"\n"
        result += "ttest        = "+str(self.ttest)+"\n"
        result += "mannwhitneyu = "+str(self.mannwhitneyu)
        return result
    def rowStr(self):
        result = list()
        level= 0.05
        value = list(self.kstestM).pop()
        result += [Tools.string(value)] + ["Норм." if value>level else "Не норм."]
        value = list(self.kstestW).pop()
        result += [Tools.string(value)] + ["Норм." if value>level else "Не норм."]
        value = list(self.shapiroM).pop()
        result += [Tools.string(value)] + ["Норм." if value>level else "Не норм."]
        value = list(self.shapiroW).pop()
        result += [Tools.string(value)] + ["Норм." if value>level else "Не норм."]
        value = list(self.normaltestM).pop()
        result += [Tools.string(value)] + ["Норм." if value>level else "Не норм."]
        value = list(self.normaltestW).pop()
        result += [Tools.string(value)] + ["Норм." if value>level else "Не норм."]
        value = list(self.ttest).pop()
        result += [Tools.string(value)] + ["Сред.один." if value>level else "Сред.отлич."]
        value = list(self.describeM).pop(2)
        result += [Tools.string(value)]
        value = list(self.describeW).pop(2)
        result += [Tools.string(value)]
        value = list(self.mannwhitneyu).pop() * 2
        result += [value] + ["Сред.один." if value>level else "Сред.отлич."]
        result += Tools.string(list(self.percentilesM))
        result += Tools.string(list(self.percentilesW))
        
        for i in range(len(self.diagramM.cumcount)):
            result += [Tools.string(self.diagramM.lowerlimit + i * self.diagramM.binsize)]
        for i in range(len(self.diagramM.cumcount)):
            result += [Tools.string(self.diagramM.cumcount[i] if i==0 else self.diagramM.cumcount[i]-self.diagramM.cumcount[i-1])]
        for i in range(len(self.diagramW.cumcount)):
            result += [Tools.string(self.diagramW.lowerlimit + i * self.diagramW.binsize)]
        for i in range(len(self.diagramW.cumcount)):
            result += [Tools.string(self.diagramW.cumcount[i] if i==0 else self.diagramW.cumcount[i]-self.diagramW.cumcount[i-1])]
        
        return reduce(lambda s,i: str(s)+";"+str(i), result)
    def captionsStr():
        result = list()
        result += ["K-S test value (M)", "K-S test (M)", "K-S test value (W)", "K-S test (W)"]
        result += ["Shapiro test value (M)", "Shapiro test (M)", "Shapiro test value (W)", "Shapiro test (W)"]
        result += ["Normal test value (M)", "Normal test (M)", "Normal test value (W)", "Normal test (W)"]
        result += ["Сравнение средних value T-test", "Сравнение средних T-test", "Mean value (M)", "Mean value (W)"]
        result += ["Сравнение средних value MU", "Сравнение средних MU"]+Tools.string(CalcResult.percentiles)+Tools.string(CalcResult.percentiles)
        return reduce(lambda s,i: str(s)+";"+str(i), result)        
    def calc(groupedDataPoints, keySecondPartM, keySecondPartW):
        result = dict()
        groupedPointsWithValue = GroupedPoints.dataPointsWithValue(groupedDataPoints)
        keyFirstParts = list(set(reduce(lambda l1,l2: l1+[l2], list(map(lambda key: list(key)[0], groupedPointsWithValue.valueDic.keys())), list())))
        keyFirstParts.sort()
        for keyFirstPart in keyFirstParts:
            keyM = [keyFirstPart] + keySecondPartM
            keyW = [keyFirstPart] + keySecondPartW
            numbersM = groupedPointsWithValue.valueDic[tuple(keyM)]
            numbersW = groupedPointsWithValue.valueDic[tuple(keyW)]
            tests = CalcResult()
            tests.kstestM = scipy.stats.kstest(numbersM, "norm")
            tests.kstestW = scipy.stats.kstest(numbersW, "norm")
            tests.shapiroM = scipy.stats.shapiro(numbersM)
            tests.shapiroW = scipy.stats.shapiro(numbersW)
            tests.normaltestM = scipy.stats.normaltest(numbersM)
            tests.normaltestW = scipy.stats.normaltest(numbersW)
            tests.describeM = scipy.stats.describe(numbersM)
            tests.describeW = scipy.stats.describe(numbersW)
            tests.percentilesM = numpy.percentile(numpy.array(numbersM), CalcResult.percentiles)
            tests.percentilesW = numpy.percentile(numpy.array(numbersW), CalcResult.percentiles)
            tests.ttest = scipy.stats.ttest_ind(numbersM, numbersW)
            tests.mannwhitneyu = scipy.stats.mannwhitneyu(numbersM, numbersW)
            tests.diagramM = scipy.stats.cumfreq(numbersM)
            tests.diagramW = scipy.stats.cumfreq(numbersW)
            #print(tests.diagramM)
            #print(keyFirstPart)
            #print(tests)
            #print(tests.rowStr())
            #print(keyFirstPart)
            result[keyFirstPart] = tests
        return result
    def write(calcResults, file = "APResults.csv"):
        keys = list(calcResults.keys())
        keys.sort()
        with open(file, "w") as file:
            file.write("Показатель"+";"+CalcResult.captionsStr()+"\n")
            for key in keys:
                calcResult = calcResults[key]
                #print(key)
                file.write(str(key)+";"+calcResult.rowStr()+"\n")
        return

# Основная программа (А.П.)
def main2():
    # Читаем из файла
    allData = ExcelData.readDataFile('Таблица (все данные) v03.xlsx', '', 'Данные', ExcelData.rng(1, 61), ExcelData.rng(1, 24))
    print("Прочитано excel ячеек: "+str(len(allData.tablePoints)))
    # Переводим ячейки в точки с атрибутами
    dataPoints = DataPoint.makeDataPoints(allData, ExcelData.rng(2, 61), ExcelData.rng(5, 24), {1 : 'Показатель'})
    print("Обработано точек данных: "+str(len(dataPoints)))
    # Группируем по атрибутам "Пол", "Тип покрытия"
    groupedData = GroupedDataPoints.groupByList(dataPoints, ["Показатель", "Пол", "Тип покрытия"])
    #groupedData = GroupedDataPoints.groupByList(dataPoints, ["Тип покрытия", "Показатель"])
    #groupedData.debug()
    #print(groupedData)
    #normTestResult = GroupedPoints.shapiro(groupedData)
    #groupedValues = GroupedPoints.dataPointsWithValue(groupedData)
    print(groupedData)
    res = CalcResult.calc(groupedData, ["Мужчины", "Быстрое"], ["Женщины", "Быстрое"])
    CalcResult.write(res)
    return

main2()

