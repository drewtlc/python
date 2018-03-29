# -*- coding: utf-8 -*-

# TODO:
# +1. Вывод списков точек данных в файл с разделителями для отладки
# 2. Вывод результатов расчета процентилей в файл с разделителями
# +3. Анализ гипотезы о нормальном законе распределения для списков точек данных
# 4. Построение графиков

import functools
from functools import reduce
from base_module import DataPoint, ExcelData, GroupedDataPoints, GroupedPoints

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
        groupName = "циклические"
        sportName = "Плавание"
        valueAndCount = dict()
        rowAndValue = dict()
        for dataPoint in dataPoints:
            curValue = rowAndValue.get(dataPoint.row,"")
            additionalCurValue = ""
            if curValue != "":
                dataPoint.attributes[self.customAttrName] = curValue
            else:
                values = list()
                additionalValues = list()
                for attrName in attrNames:
                    value = dataPoint.attributes.get(attrName, '')
                    if value != "":
                        parts = list(value.split(" - "))
                        if len(parts) == 2:
                            value = parts[1]
                        else:
                            value = parts[0]
                        values += [value]
                        additionalValue = ""
                        if value == groupName:
                            for additionalAttrName in attrDict.get(attrName, []):
                                if dataPoint.attributes.get(attrName, '') == sportName:
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
                            curCount = count
                if curValue == groupName and additionalCurValue == sportName:
                    curValue = ""
                dataPoint.attributes[self.customAttrName] = curValue
                rowAndValue[dataPoint.row] = curValue
                if curValue != "":
                    curCount = valueAndCount.get(curValue, 0)
                    valueAndCount[curValue] = (curCount + 1)
        #print(valueAndCount)
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

def main():
    # Читаем из файла
    allData = ExcelData.readDataFile('БАЗА 2018 на 20.03.2018_v03.1_v05.xlsx', '', 'База 20.03.18', ExcelData.rng(1, 2808), ExcelData.rng(1, 138))
    print("Прочитано excel ячеек: "+str(len(allData.tablePoints)))
    # Переводим ячейки в точки с атрибутами
    dataPoints = DataPoint.makeDataPoints(allData, ExcelData.rng(2, 2808), ExcelData.rng(57, 138), {1 : 'Показатель'})
    print("Обработано точек данных: "+str(len(dataPoints)))
    #attrAge = CustomAttribute("Возраст (год)", [], "", lambda dp: round(dp.attributes.get("Возраст",'')) if dp.isFloat else 0)
    #attrAge.addCustomAttribute(dataPoints);
    attrVid = CustomAttribute("Группа видов спорта 1 (периф. зрение)", [], "", lambda dp: "" if dp.attributes.get("Группа видов спорта 1",'')=="10 - циклические" and (dp.attributes.get("Рекомендванный вид спорта 1",'')=="Плавание" or dp.attributes.get("Рекомендванный вид спорта 11",'')=="Плавание" or dp.attributes.get("Рекомендванный вид спорта 111",'')=="Плавание" ) else dp.attributes.get("Группа видов спорта 1",''))
    attrVid.addCustomAttribute(dataPoints);
    attrGroup = CustomAttribute("Группа видов спорта")
    attrGroup.splitInGroups(dataPoints);

    percentiles = [5, 25, 50, 75, 95]

    # Адаптационный потенциал
    groupedData_ПолВозрастПоказатель = GroupedDataPoints.groupByList(dataPoints, ["Показатель", "Пол", "Возраст"])
    #print(groupedData_ПолВозрастПоказатель)
    perc_ПолВозрастПоказатель = GroupedPoints.percentiles(groupedData_ПолВозрастПоказатель, percentiles)
    #print(perc_ПолВозрастПоказатель)
    perc_ПолВозрастПоказатель.saveToFile("perc_ПолВозрастПоказатель.csv", perc_ПолВозрастПоказатель.attrGroup)

    # Группируем по атрибутам "Пол", "Возраст (год)", "Группа видов спорта 1 (периф. зрение)"
    groupedData_ПолВозрастВидПоказатель = GroupedDataPoints.groupByList(dataPoints, ["Группа видов спорта", "Показатель", "Пол", "Возраст"])
    #print(groupedData_ПолВозрастВидПоказатель)
    perc_ПолВозрастВидПоказатель = GroupedPoints.percentiles(groupedData_ПолВозрастВидПоказатель, percentiles)
    #print(perc_ПолВозрастВидПоказатель)
    perc_ПолВозрастВидПоказатель.saveToFile("perc_ПолВозрастВидПоказатель.csv",perc_ПолВозрастВидПоказатель.attrGroup)

    return

main()

