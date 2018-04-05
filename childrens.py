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
from base_module import RowsColsSettings, DataPoint, ExcelData, GroupedDataPoints, GroupedPoints

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
        rowAndValue = dict()
        for dataPoint in dataPoints:
            curValue = rowAndValue.get(dataPoint.row, "")
            additionalCurValue = ""
            #if curValue != "":
            #    dataPoint.attributes[self.customAttrName] = curValue
            #else:
            if curValue == "":
                values = list()
                additionalValues = list()
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
                            if value == groupName:
                                for additionalAttrName in attrDict.get(attrName, []):
                                    if dataPoint.attributes.get(additionalAttrName, "").upper() == sportName:
                                        additionalValue = sportName
                            additionalValues += [additionalValue]
                for i in range(len(values)):
                    value = values[i]
                    additionalValue = additionalValues[i]
                    if curValue == "" or (curValue == groupName and additionalCurValue == sportName):
                        curValue = value
                        additionalCurValue = additionalValue
                    else:
                        count = valueAndCount.get(value, 0)
                        curCount = valueAndCount.get(curValue, 0)
                        if count < curCount:
                            #curCount = count
                            curValue = value
                if curValue == groupName and additionalCurValue == sportName:
                    curValue = ""
                #dataPoint.attributes[self.customAttrName] = curValue
                rowAndValue[dataPoint.row] = curValue
                if curValue != "":
                    curCount = valueAndCount.get(curValue, 0)
                    valueAndCount[curValue] = (curCount + 1)
        print(valueAndCount)
        #print(reduce(lambda s, v: s+v, valueAndCount.values()))
        #print(rowAndValue)
        valueAndRow = dict()
        for key, value in rowAndValue.items():
            valueAndRow[value] = (valueAndRow.get(value, []) + [key])
        #print(valueAndRow)
        for dataPoint in dataPoints:
            dataPoint.attributes[self.customAttrName] = rowAndValue.get(dataPoint.row, "")
        return

class CustomScale:
    def __init__(self):
        self.data = dict() # {6: [1,2,3], 7:[2,3,2]}
        self.order = 1
        self.roundCount = -1
        self.result = dict()
        return

    def calc(self):
        #print(self.data.values())
        for i in range(len(list(self.data.values())[0])):
            x = list()
            y = list()
            x_int = list()
            y_int = list()
            for key in self.data.keys():
                x += [key]
                y += [self.data[key][i]]
                if self.data[key][i] != "":
                    x_int += [key]
                    y_int += [self.data[key][i]]
            if len(y_int)>1:
                x_int = [x_int[0], x_int[len(x_int) - 1]]
                y_int = [y_int[0], y_int[len(y_int) - 1]]
                f = interpolate.interp1d(x_int, y_int)
                for x_index in range(len(x)):
                    curX = x[x_index]
                    if curX >= x_int[0] and curX <= x_int[1]:
                        y[x_index] = float(f(curX))
                        if self.roundCount != -1:
                            y[x_index] = round(y[x_index], self.roundCount)
                    self.result[curX] = self.result.get(curX, []) + [y[x_index]]
        return

    def buildScales(groupedPoints, scaleRange = {3: [6,7,8,9,10,11,12]}, percentilesIndexes = [0,1,2,3,4], orderIndex = 8, roundCountIndex = 9):
        # orderIndex = None
        # for i in range(len(groupedPoints.attrGroup)):
        #     if groupedPoints.attrGroup[i] == "order":
        #         orderIndex = i
        blocks = dict()
        keys = list(groupedPoints.valueDic.keys())
        keys.sort()
        for key in keys:
            keyBlock = list()
            for i in range(len(key)):
                if i not in scaleRange.keys():
                    keyBlock += [key[i]]
            if tuple(keyBlock) not in blocks:
                scale = CustomScale()
                for scaleRangeValue in list(scaleRange.values())[0]:
                    rangeKey = tuple(keyBlock+[float(scaleRangeValue)])
                    if rangeKey in groupedPoints.valueDic:
                        valueDicData = groupedPoints.valueDic[rangeKey]
                        for percentilesIndex in percentilesIndexes:
                            scale.data[scaleRangeValue] = scale.data.get(scaleRangeValue, []) + [valueDicData[percentilesIndex]]
                        scale.order = valueDicData[orderIndex]
                        scale.roundCount = valueDicData[roundCountIndex]
                scale.calc()
                blocks[tuple(keyBlock)] = scale
            groupedPoints.valueDic[key] = list(repeat("", len(percentilesIndexes))) + groupedPoints.valueDic[key]
        for keyBlock, scale in blocks.items():
            for scaleKey, scaleResult in scale.result.items():
                key = tuple(list(keyBlock)+[float(scaleKey)])
                value = groupedPoints.valueDic[key]
                for i in range(len(scaleResult)):
                    value[i] = scaleResult[i]
                groupedPoints.valueDic[key] = value
        captions = list()
        for i in range(list(scaleRange.keys())[0]+1):
            captions += [groupedPoints.attrGroup[i]]
        captions += range(1,len(percentilesIndexes)+1)
        for i in range(list(scaleRange.keys())[0]+1, len(groupedPoints.attrGroup)):
            captions += [groupedPoints.attrGroup[i]]
        groupedPoints.attrGroup = captions
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
    rowsColsSettings = RowsColsSettings(1, 2810, 1, 139, 4, None, 57, None)
    allData = ExcelData.readDataFile('БАЗА 2018 на 20.03.2018_v03.2_v02.xlsx', '', 'База 20.03.18', rowsColsSettings)
    print("Прочитано excel ячеек: "+str(len(allData.tablePoints)))
    # Переводим ячейки в точки с атрибутами
    upDown = lambda value: -1 if value=="↓" else 1
    roundCount = lambda value: 2 if value == "0,11" or value == 0.11 else (1 if value == "0,1" or value == 0.1 else (0 if value == "целое" else -1))
    dataPoints = DataPoint.makeDataPoints(allData, rowsColsSettings, {1 : 'ВозрУбыв', 2 : 'Округл', 3 : 'Показатель'}, {1 : upDown, 2 : roundCount}, False)
    print("Обработано точек данных: "+str(len(dataPoints)))
    #attrAge = CustomAttribute("Возраст (год)", [], "", lambda dp: round(dp.attributes.get("Возраст",'')) if dp.isFloat else 0)
    #attrAge.addCustomAttribute(dataPoints)
    attrVid = CustomAttribute("Группа видов спорта 1 (периф. зрение)", [], "", lambda dp: "" if dp.attributes.get("Группа видов спорта 1",'')=="10 - циклические" and (dp.attributes.get("Рекомендванный вид спорта 1",'')=="Плавание" or dp.attributes.get("Рекомендванный вид спорта 11",'')=="Плавание" or dp.attributes.get("Рекомендванный вид спорта 111",'')=="Плавание" ) else dp.attributes.get("Группа видов спорта 1",''))
    attrVid.addCustomAttribute(dataPoints)
    attrGroup = CustomAttribute("Группа видов спорта")
    attrGroup.splitInGroups(dataPoints)

    percentiles = [5, 25, 50, 75, 95]

    # Группируем по атрибутам "Показатель", "Пол", "Возраст"
    groupedData_ПоказательПолВозраст = GroupedDataPoints.groupByList(dataPoints, ["Показатель", "Пол", "Возраст"])
    #print(groupedData_ПоказательПолВозраст)
    perc_ПоказательПолВозраст = GroupedPoints.percentiles(groupedData_ПоказательПолВозраст, percentiles, "ВозрУбыв", "Округл")
    CustomScale.buildScales(perc_ПоказательПолВозраст, {2: [6,7,8,9,10,11,12]}, [0,1,2,3,4], 8, 9)
    #print(perc_ПоказательПолВозраст)
    perc_ПоказательПолВозраст.saveToFile("perc_ПоказательПолВозраст.csv", perc_ПоказательПолВозраст.attrGroup)

    # Группируем по атрибутам "Группа видов спорта", "Показатель", "Пол", "Возраст"
    groupedData_ВидПоказательПолВозраст = GroupedDataPoints.groupByList(dataPoints, ["Группа видов спорта", "Показатель", "Пол", "Возраст"])
    #print(groupedData_ПолВозрастВидПоказатель)
    perc_ВидПоказательПолВозраст = GroupedPoints.percentiles(groupedData_ВидПоказательПолВозраст, percentiles, "ВозрУбыв", "Округл")
    CustomScale.buildScales(perc_ВидПоказательПолВозраст, {3: [6,7,8,9,10,11,12]}, [0,1,2,3,4], 8, 9)
    #print(perc_ВидПоказательПолВозраст)
    perc_ВидПоказательПолВозраст.saveToFile("perc_ВидПоказательПолВозраст.csv",perc_ВидПоказательПолВозраст.attrGroup)

    # Группируем по атрибутам "Группа видов спорта", "Показатель"
    groupedData_ВидПоказатель = GroupedDataPoints.groupByList(dataPoints, ["Группа видов спорта", "Показатель"])
    #print(groupedData_ВидПоказатель)
    perc_ВидПоказатель = GroupedPoints.percentiles(groupedData_ВидПоказатель, percentiles, "ВозрУбыв", "Округл", {6,7,8,9,10,11,12})
    #CustomScale.buildScales(perc_ВидПоказатель, {3: [6,7,8,9,10,11,12]}, [0,1,2,3,4], 8, 9)
    #print(perc_ВидПоказатель)
    perc_ВидПоказатель.saveToFile("perc_ВидПоказатель.csv",perc_ВидПоказатель.attrGroup)

    # Группируем по атрибутам "Группа видов спорта", "Показатель", "Пол"
    groupedData_ВидПоказательПол = GroupedDataPoints.groupByList(dataPoints, ["Группа видов спорта", "Показатель", "Пол"])
    #print(groupedData_ВидПоказательПол)
    perc_ВидПоказательПол = GroupedPoints.percentiles(groupedData_ВидПоказательПол, percentiles, "ВозрУбыв", "Округл", {6,7,8,9,10,11,12})
    #CustomScale.buildScales(perc_ВидПоказательПол, {3: [6,7,8,9,10,11,12]}, [0,1,2,3,4], 8, 9)
    #print(perc_ВидПоказательПол)
    perc_ВидПоказательПол.saveToFile("perc_ВидПоказательПол.csv",perc_ВидПоказательПол.attrGroup)

    return

main()

