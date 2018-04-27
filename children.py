# -*- coding: utf-8 -*-

# TODO:
# +1. Вывод списков точек данных в файл с разделителями для отладки
# 2. Вывод результатов расчета процентилей в файл с разделителями
# +3. Анализ гипотезы о нормальном законе распределения для списков точек данных
# 4. Построение графиков

import functools
from functools import reduce
from itertools import repeat
from scipy import interpolate
import numpy
import scipy.optimize
import warnings
from base_module import Tools, RowsColsSettings, DataPoint, ExcelData, GroupedDataPoints, GroupedPoints

class CustomAttribute:
    def __init__(self, customAttrName, attrListToProcess = [], attrValueToSearch = "", calcLambda = lambda dp: None):
        self.customAttrName    = customAttrName
        self.attrListToProcess = attrListToProcess
        self.attrValueToSearch = attrValueToSearch
        self.mapLambda         = lambda attr, dp: 1 if (dp.attributes.get(attr,'') == self.attrValueToSearch) else 0
        self.calcLambda        = calcLambda
    def addCustomAttributeOR(self, dataPoints):
        reduceLambda = lambda val, listVal: min(val + listVal, 1)
        for dataPoint in dataPoints:
            dataPoint.attributes[self.customAttrName] = reduce(reduceLambda, map(functools.partial(self.mapLambda, dp=dataPoint), self.attrListToProcess))
        return
    def addCustomAttributeAND(self, dataPoints):
        reduceLambda = lambda val, listVal: min(val * listVal, 1)
        for dataPoint in dataPoints:
            dataPoint.attributes[self.customAttrName] = reduce(reduceLambda, map(functools.partial(self.mapLambda, dp=dataPoint), self.attrListToProcess))
        return
    def addCustomAttribute(self, dataPoints):
        for dataPoint in dataPoints:
            dataPoint.attributes[self.customAttrName] = self.calcLambda(dataPoint)
        return
    def splitInGroups(self, dataPoints):
        attrNames = ["Группа видов спорта 1", "Группа видов спорта 2", "Группа видов спорта 3", "Группа видов спорта 4"]
        attrDict = {"Группа видов спорта 1": ["Рекомендванный вид спорта 1", "Рекомендванный вид спорта 11", "Рекомендванный вид спорта 111"], "Группа видов спорта 2": ["Рекомендванный вид спорта 2", "Рекомендванный вид спорта 22", "Рекомендванный вид спорта 222"], "Группа видов спорта 3": ["Рекомендванный вид спорта 3", "Рекомендванный вид спорта 33", "Рекомендванный вид спорта 333"], "Группа видов спорта 4": ["Рекомендванный вид спорта 4", "Рекомендванный вид спорта 44", "Рекомендванный вид спорта 444"]}
        groupName = "циклические".upper()
        sportName = "Плавание".upper()
        goodNames = set(map(lambda v: v.upper(), ['циклические','спортивные единоборства','сложно-координационные','игровые','командные игровые','скоростно-силовые']))
        valueAndCount = dict()
        rowAndValue = dict() # значение - список из 4 элементов
        for dataPoint in dataPoints:
            curList = rowAndValue.get(dataPoint.row, ["","","",""])
            curValue = curList[0]
            curValueAdditional = curList[1]
            curValueName = curList[2]
            curValueAdditionalName = curList[3]
            if curValue == "":
                values = list()
                additionalValues = list()
                namesValues = list()
                additionalNamesValues = list()
                for attrName in attrNames:
                    value = dataPoint.attributes.get(attrName, "").upper()
                    if value != "":
                        parts = list(value.split(" - "))
                        if len(parts) == 2:
                            value = parts[1]
                        else:
                            value = parts[0]
                        if value in goodNames:
                            values += [value]
                            additionalValue = ""
                            additionalNameValue = ""
                            # if value == groupName:
                            #     for additionalAttrName in attrDict.get(attrName, []):
                            #         if dataPoint.attributes.get(additionalAttrName, "").upper() == sportName:
                            #             additionalValue = sportName
                            #             additionalNamesValues += [additionalAttrName]
                            # else:
                            for additionalAttrName in attrDict.get(attrName, []):
                                if additionalValue == "" and dataPoint.attributes.get(additionalAttrName, "").upper() != "":
                                    additionalValue = dataPoint.attributes.get(additionalAttrName, "").upper()
                                    additionalNameValue = additionalAttrName
                            additionalValues += [additionalValue]
                            namesValues += [attrName]
                            additionalNamesValues += [additionalNameValue]
                for i in range(len(values)):
                    value = values[i]
                    additionalValue = additionalValues[i]
                    names = namesValues[i]
                    additionalNames = additionalNamesValues[i]
                    #print(values)
                    #print(additionalNamesValues)
                    if curValue == "" or (curValue == groupName and curValueAdditional == sportName):
                        curValue = value
                        curValueAdditional = additionalValue
                        curValueName = names
                        curValueAdditionalName = additionalNames
                    else:
                        count = valueAndCount.get(value, 0)
                        curCount = valueAndCount.get(curValue, 0)
                        if count < curCount:
                            #curCount = count
                            curValue = value
                            curValueAdditional = additionalValue
                            curValueName = names
                            curValueAdditionalName = additionalNames
                if curValue == groupName and curValueAdditional == sportName:
                    curValue = ""
                    curValueAdditional = ""
                    curValueName = ""
                    curValueAdditionalName = ""
                    #dataPoint.attributes[self.customAttrName] = curValue
                rowAndValue[dataPoint.row] = [curValue,curValueAdditional,curValueName,curValueAdditionalName]
                if curValue != "":
                    curCount = valueAndCount.get(curValue, 0)
                    valueAndCount[curValue] = (curCount + 1)
        print(valueAndCount)
        #print(reduce(lambda s, v: s+v, valueAndCount.values()))
        #print(rowAndValue)
        # valueAndRow = dict()
        # for key, value in rowAndValue.items():
        #     valueAndRow[value] = (valueAndRow.get(value, []) + [key])
        #print(valueAndRow)
        for dataPoint in dataPoints:
            curList = rowAndValue.get(dataPoint.row, ["","","",""])
            curValue = curList[0]
            curValueAdditional = curList[1]
            curValueName = curList[2]
            curValueAdditionalName = curList[3]
            dataPoint.attributes[self.customAttrName] = curValue
            dataPoint.attributes["Вид спорта"] = curValueAdditional
            dataPoint.attributes[self.customAttrName + " (колонка)"] = curValueName
            dataPoint.attributes["Вид спорта" + " (колонка)"] = curValueAdditionalName
        return


class ChildrenValue:
    def __init__(self, order = 1, roundCount = -1):
        self.scaleValues = list()
        self.percValues = list()
        self.count = 0
        self.mean = None
        self.std = None
        self.order = order
        self.roundCount = roundCount
        self.data = list()
        self.nums = list()

    def __str__(self):
        delim = ";"
        return Tools.withDelim(Tools.string(self.scaleValues), delim) + delim + \
               Tools.withDelim(Tools.string(self.percValues), delim) + delim + \
               Tools.string(self.count) + delim + \
               Tools.string(self.mean) + delim + \
               Tools.string(self.std) + delim + \
               Tools.string(self.order) + delim + \
               Tools.string(self.roundCount) + delim + \
               str(self.data) + delim + \
               str(self.nums)


class CalcLogic:
    def percentiles(groupedDataPoints, percentiles, orderAttrName = "", roundCountAttrName = "", ageFilter = set()):
        # Из сгруппированных точек строим сгруппированные списки числовых значений
        if len(ageFilter)==0:
            filterLambda = lambda dp: dp.isFloat == True
        else:
            filterLambda = lambda dp: (dp.isFloat == True) and (int(dp.attributes.get("Возраст")) in ageFilter)
        groupedPointsValues = GroupedPoints.dataPointsValues(groupedDataPoints, filterLambda)
        groupedPointsNums = GroupedPoints.dataPointsNums(groupedDataPoints, filterLambda)
        groupedPointsOrderAttrValue = GroupedPoints.dataPointsAttrValue(groupedDataPoints, orderAttrName)
        groupedPointsRoundCountAttrValue = GroupedPoints.dataPointsAttrValue(groupedDataPoints, roundCountAttrName)
        result = GroupedPoints()
        result.attrGroup = groupedPointsValues.attrGroup.copy() # + Tools.listIndexes(percentiles, 1) + percentiles.copy() + ["count", "mean", "std", "order", "roundCount", "data", "nums"]
        for key, numbers in groupedPointsValues.valueDic.items():
            order = 1
            if orderAttrName != "":
                orders = groupedPointsOrderAttrValue.valueDic.get(key)
                if len(orders) == 1:
                    order = list(orders)[0]
            roundCount = -1
            if roundCountAttrName != "":
                roundCounts = groupedPointsRoundCountAttrValue.valueDic.get(key)
                if len(roundCounts) == 1:
                    roundCount = list(roundCounts)[0]
            value = ChildrenValue(order, roundCount) # значение - экземпляр типа ChildrenValue
            if len(numbers) != 0:
                nparr = numpy.array(numbers)
                value.percValues = list(numpy.percentile(nparr, percentiles))
                if roundCount != -1:
                    value.percValues = list(map(lambda v: round(v, roundCount), value.percValues))
                if order == -1:
                    value.percValues.reverse()
                value.count = len(numbers)
                mean = numpy.mean(nparr)
                value.mean = (mean if roundCount == -1 else round(mean, roundCount + 2))
                std = numpy.std(nparr)
                value.std = (std if roundCount == -1 else round(std, roundCount + 2))
                value.data = numbers
                value.nums = groupedPointsNums.valueDic[key]
            result.valueDic[key] = value
        return result

    def saveToFile(dataPoints, fileName, delim = ";"):
        dataMatrix = dict()  # Словарь для данных
        minRow = None
        minCol = None
        attributesOrder = list()
        for dataPoint in dataPoints:
            if len(attributesOrder)==0:
                attributesOrder = list(dataPoint.attributes.keys())
            dataMatrix[tuple([dataPoint.row, dataPoint.col])] = dataPoint
            if minRow == None:
                minRow = dataPoint.row
            if minCol == None:
                minCol = dataPoint.col
            minRow = dataPoint.row if minRow > dataPoint.row else minRow
            minCol = dataPoint.col if minCol > dataPoint.col else minCol
        rowsCols = list(dataMatrix.keys())
        rowsCols.sort()
        rowsData = dict()
        attrName1 = "Группа видов спорта"
        attrName2 = "Вид спорта"
        attrName3 = attrName1 + " (колонка)"
        attrName4 = attrName2 + " (колонка)"
        for rowCol in rowsCols:
            row = rowCol[0]
            col = rowCol[1]
            dp = dataMatrix[rowCol]
            rowList = rowsData.get(row, [])
            rowList1 = rowsData.get(-3, [])
            rowList2 = rowsData.get(-2, [])
            rowList3 = rowsData.get(-1, [])
            if col == minCol:
                attr1 = dp.attributes.get(attrName1, "")
                attr2 = dp.attributes.get(attrName2, "")
                attr3 = dp.attributes.get(attrName3, "")
                attr4 = dp.attributes.get(attrName4, "")
                rowList += [attr1, attr2, attr3, attr4]
                keysList = attributesOrder.copy()
                for key in [attrName1, attrName2, attrName3, attrName4, "ВозрУбыв", "Округл", "Показатель"]:
                    keysList.remove(key)
                for key in keysList:
                    rowList += [dp.attributes.get(key)]
            if row == minRow:
                if col == minCol:
                    rowList1 = ["","","",""]
                    rowList2 = ["","","",""]
                    rowList3 = [attrName1, attrName2, attrName3, attrName4]
                    keysList = attributesOrder.copy()
                    for key in [attrName1, attrName2, attrName3, attrName4, "ВозрУбыв", "Округл", "Показатель"]:
                        keysList.remove(key)
                    for key in keysList:
                        rowList1 += [""]
                        rowList2 += [""]
                        rowList3 += [key]
                rowList1 += [dp.attributes.get("ВозрУбыв")]
                rowList2 += [dp.attributes.get("Округл")]
                rowList3 += [dp.attributes.get("Показатель")]
                rowsData[-3] = rowList1
                rowsData[-2] = rowList2
                rowsData[-1] = rowList3
            val = Tools.string(dp.value) if dp.isFloat else dp.value
            rowList.append(val)
            rowsData[row] = rowList
        with open(fileName, "w") as file:
            rows = list(rowsData.keys())
            rows.sort()
            for row in rows:
                rowList = rowsData[row]
                for i in range(len(rowList)):
                    rowList[i] = str(rowList[i]).replace("\n"," ")
                    if rowList[i]=="":
                        rowList[i] = "\"\""
                strForFile = reduce(lambda s,v: str(s)+delim+str(v), rowList)
                file.write(strForFile+"\n")
        return

class CustomScale:
    def __init__(self, order = 1, roundCount = -1):
        self.data = dict() # {6: [1,2,3], 7: [2,3,2]}
        self.counts = dict()
        self.order = order
        self.roundCount = roundCount
        self.result = dict()
        return

    def exp(t, a, b):
        return a * numpy.exp(b * t)

    def bestFit(self, ages, x, y):
        xBegin = ages[0]
        xEnd = ages[len(ages) - 1]
        #  p - апроксимационный полином некоторой степени. В текущей версии 1 степени. Коэфициенты полинома дает функция polyfit
        p = numpy.poly1d(numpy.polyfit(numpy.array(x), numpy.array(y), 1))
        # with warnings.catch_warnings():
        #     warnings.filterwarnings('error')
        #     try:
        #         p = numpy.poly1d(numpy.polyfit(numpy.array(x), numpy.array(y[i]), 1))
        #     except numpy.RankWarning:
        #         stop = True
        yBegin, yEnd = p(xBegin), p(xEnd)
        pair = None
        if self.order == 1 and yBegin <= yEnd:
            pair = [yBegin, yEnd]
        if self.order == 1 and yBegin > yEnd:
            pair = [yEnd, yBegin]
        if self.order == -1 and yBegin >= yEnd:
            pair = [yBegin, yEnd]
        if self.order == -1 and yBegin < yEnd:
            pair = [yEnd, yBegin]
        funcP = interpolate.interp1d([xBegin, xEnd], pair)
        errP = 0
        for i in Tools.listIndexes(x):
            errP += (funcP(x[i]) - y[i]) ^ 2
        # Теперь строим экспоненту
        [a, b], pcov = scipy.optimize.curve_fit(CustomScale.exp, x, y)
        yBegin, yEnd = CustomScale.exp(xBegin, a, b), CustomScale.exp(xEnd, a, b)



    def calc(self):
        #print(self.data.values())
        if len(self.data) != 0:
            ages = list(self.data.keys())
            ages.sort()
            x = list()
            cols = len(self.data.get(ages[0]))
            #y = [repeat([], cols)]
            y = list()
            for i in range(cols):
                y.append([])
            for age in ages:
                count = self.counts.get(age)
                for i in range(count):
                    x.append(age)
                for i in range(cols):
                    for j in range(count):
                        y[i].append(self.data.get(age)[i])
            f = list()
            for i in range(cols):
                 f.append(self.bestFit(ages, x, y[i]))
            for age in ages:
                vals = list()
                for i in range(cols):
                    val = float(f[i](age))
                    if self.roundCount != -1:
                        val = round(val, self.roundCount)
                    vals.append(val)
                self.result[age] = vals
        # for i in range(len(list(self.data.values())[0])):
        #     x = list()
        #     y = list()
        #     x_int = list()
        #     y_int = list()
        #     for key in self.data.keys():
        #         x += [key]
        #         y += [self.data[key][i]]
        #         if self.data[key][i] != "":
        #             x_int += [key]
        #             y_int += [self.data[key][i]]
        #     if len(y_int)>1:
        #         x_int = [x_int[0], x_int[len(x_int) - 1]]
        #         y_int = [y_int[0], y_int[len(y_int) - 1]]
        #         f = interpolate.interp1d(x_int, y_int)
        #         for x_index in range(len(x)):
        #             curX = x[x_index]
        #             if curX >= x_int[0] and curX <= x_int[1]:
        #                 y[x_index] = float(f(curX))
        #                 if self.roundCount != -1:
        #                     y[x_index] = roundCount(y[x_index], self.roundCount)
        #             self.result[curX] = self.result.get(curX, []) + [y[x_index]]
        return

    def buildScales(groupedPoints, scaleAttrName = "Возраст"):
        # Оределим место scaleAttrName в списке, который составляет ключ
        scaleAttrIndex = groupedPoints.attrGroup.index(scaleAttrName)
        # Определим возможные значения поля scaleAttrName
        scaleAttrDict = dict()
        for key in groupedPoints.valueDic.keys():
            keyList = list(key)
            scaleAttrValue = keyList[scaleAttrIndex]
            keyList.pop(scaleAttrIndex)
            keyTuple = tuple(keyList)
            scaleAttrDict[keyTuple] = scaleAttrDict.get(keyTuple, []) + [scaleAttrValue]
        scalesDict = dict()
        for scaleAttrKey, scaleAttrValues in scaleAttrDict.items():
            scale = CustomScale()
            for scaleAttrValue in scaleAttrValues:
                key = list(scaleAttrKey)
                key.insert(scaleAttrIndex, scaleAttrValue)
                childrenValue = groupedPoints.valueDic[tuple(key)]
                scale.order = childrenValue.order
                scale.roundCount = childrenValue.roundCount
                if len(childrenValue.percValues)>0:
                    scale.data[scaleAttrValue] = childrenValue.percValues
                    scale.counts[scaleAttrValue] = childrenValue.count
            scale.calc()
            for scaleAttrValue in scaleAttrValues:
                key = list(scaleAttrKey)
                key.insert(scaleAttrIndex, scaleAttrValue)
                childrenValue = groupedPoints.valueDic[tuple(key)]
                if len(childrenValue.percValues) > 0:
                    childrenValue.scaleValues = scale.result[scaleAttrValue]
        return


# Основная программа
def main1():
    # Читаем из файла
    allData = ExcelData.readDataFile('ОБЩИЙ ИТОГ 2016-17_01.12_v8.xlsx', 'Коды', 'Рез-ты 16-17', ExcelData.rng(1, 2244), ExcelData.rng(1, 117))
    print("Прочитано excel ячеек: "+str(len(allData.tablePoints)))
    # Переводим ячейки в точки с атрибутами
    dataPoints = DataPoint.makeDataPoints(allData, ExcelData.rng(5, 2244), ExcelData.rng(45, 115), {1 : 'Тип исследования', 2 : 'Группа показателей', 3 : 'Возрасты теста', 4 : 'Показатель'})
    print("Обработано точек данных: "+str(len(dataPoints)))
    # Циклические
    attr1 = CustomAttribute("Рек Циклические", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Циклические")
    attr1.addCustomAttributeOR(dataPoints)
    # Командные игровые
    attr2 = CustomAttribute("Рек Командные игровые", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Командные игровые")
    attr2.addCustomAttributeOR(dataPoints)
    # Игровые
    attr3 = CustomAttribute("Рек Игровые", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Игровые")
    attr3.addCustomAttributeOR(dataPoints)
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

def main():
    # Читаем из файла
    rowsColsSettings = RowsColsSettings(строкаНачало=1, строкаКонец=2809, столбецНачало=1, столбецКонец=139,
                                        строкаДанныхНачало=4, строкаДанныхКонец=None, столбецДанныхНачало=57,
                                        столбецДанныхКонец=None)
    allData = ExcelData.readDataFile(fileName='БАЗА 2018 на 20.03.2018_v03.4.xlsx', dicSheetName='',
                                     dataSheetName='База 20.03.18', rowsColsSettings=rowsColsSettings)
    print("Прочитано excel ячеек: "+str(len(allData.tablePoints)))
    # Переводим ячейки в точки с атрибутами
    upDown = lambda value: -1 if value=="↓" else 1
    roundCount = lambda value: 2 if value == "0,11" or value == 0.11 else (1 if value == "0,1" or value == 0.1 else (0 if value == "целое" else -1))
    dataPoints = DataPoint.makeDataPoints(allData, rowsColsSettings, ["Дата тестирования", "Дата рождения"], {1 : 'ВозрУбыв', 2 : 'Округл', 3 : 'Показатель'}, {1 : upDown, 2 : roundCount}, False)
    print("Обработано точек данных: "+str(len(dataPoints)))
    #attrAge = CustomAttribute("Возраст (год)", [], "", lambda dp: roundCount(dp.attributes.get("Возраст",'')) if dp.isFloat else 0)
    #attrAge.addCustomAttribute(dataPoints)
    attrVid = CustomAttribute("Группа видов спорта 1 (периф. зрение)", [], "", lambda dp: "" if dp.attributes.get("Группа видов спорта 1",'')=="10 - циклические" and (dp.attributes.get("Рекомендванный вид спорта 1",'')=="Плавание" or dp.attributes.get("Рекомендванный вид спорта 11",'')=="Плавание" or dp.attributes.get("Рекомендванный вид спорта 111",'')=="Плавание" ) else dp.attributes.get("Группа видов спорта 1",''))
    attrVid.addCustomAttribute(dataPoints)
    attrGroup = CustomAttribute("Группа видов спорта")
    attrGroup.splitInGroups(dataPoints)

    CalcLogic.saveToFile(dataPoints, "БАЗА 2018 на 20.03.2018_v03.4.csv")

    percentiles = [5, 10, 25, 40, 50, 60, 75, 90, 95]
    ages = {6, 7, 8, 9, 10, 11, 12}

    # Группируем по атрибутам "Показатель", "Пол", "Возраст"
    groupedData_ПоказательПолВозраст = GroupedDataPoints.groupByList(dataPoints, ["Показатель", "Пол", "Возраст"])
    #print(groupedData_ПоказательПолВозраст)
    perc_ПоказательПолВозраст = CalcLogic.percentiles(groupedData_ПоказательПолВозраст, percentiles, "ВозрУбыв", "Округл", ages)
    CustomScale.buildScales(perc_ПоказательПолВозраст, "Возраст")
    #print(perc_ПоказательПолВозраст)
    perc_ПоказательПолВозраст.saveToFile("res_ПоказательПолВозраст.csv", perc_ПоказательПолВозраст.attrGroup + Tools.listIndexes(percentiles, 1) + percentiles + ["count", "mean", "std", "order", "roundCount", "data", "nums"])

    # Группируем по атрибутам "Группа видов спорта", "Показатель", "Пол", "Возраст"
    groupedData_ВидПоказательПолВозраст = GroupedDataPoints.groupByList(dataPoints, ["Группа видов спорта", "Показатель", "Пол", "Возраст"])
    #print(groupedData_ПолВозрастВидПоказатель)
    perc_ВидПоказательПолВозраст = CalcLogic.percentiles(groupedData_ВидПоказательПолВозраст, percentiles, "ВозрУбыв", "Округл", ages)
    CustomScale.buildScales(perc_ВидПоказательПолВозраст, "Возраст")
    #print(perc_ВидПоказательПолВозраст)
    perc_ВидПоказательПолВозраст.saveToFile("res_ВидПоказательПолВозраст.csv",perc_ВидПоказательПолВозраст.attrGroup+ Tools.listIndexes(percentiles, 1) + percentiles + ["count", "mean", "std", "order", "roundCount", "data", "nums"])

    # Группируем по атрибутам "Группа видов спорта", "Показатель"
    groupedData_ВидПоказатель = GroupedDataPoints.groupByList(dataPoints, ["Группа видов спорта", "Показатель"])
    #print(groupedData_ВидПоказатель)
    perc_ВидПоказатель = CalcLogic.percentiles(groupedData_ВидПоказатель, percentiles, "ВозрУбыв", "Округл", ages)
    #CustomScale.buildScales(perc_ВидПоказатель, "Возраст")
    #print(perc_ВидПоказатель)
    perc_ВидПоказатель.saveToFile("res_ВидПоказатель.csv",perc_ВидПоказатель.attrGroup+ Tools.listIndexes(percentiles, 1) + percentiles + ["count", "mean", "std", "order", "roundCount", "data", "nums"])

    # Группируем по атрибутам "Группа видов спорта", "Показатель", "Пол"
    groupedData_ВидПоказательПол = GroupedDataPoints.groupByList(dataPoints, ["Группа видов спорта", "Показатель", "Пол"])
    #print(groupedData_ВидПоказательПол)
    perc_ВидПоказательПол = CalcLogic.percentiles(groupedData_ВидПоказательПол, percentiles, "ВозрУбыв", "Округл", ages)
    #CustomScale.buildScales(perc_ВидПоказательПол, "Возраст")
    #print(perc_ВидПоказательПол)
    perc_ВидПоказательПол.saveToFile("res_ВидПоказательПол.csv",perc_ВидПоказательПол.attrGroup+ Tools.listIndexes(percentiles, 1) + percentiles + ["count", "mean", "std", "order", "roundCount", "data", "nums"])

    return

main()

