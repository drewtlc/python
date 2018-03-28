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
    def addCustomAttributeAND(self, dataPoints):
        reduceLambda = lambda val, listVal: min(val * listVal, 1)
        for dataPoint in dataPoints:
            dataPoint.attributes[self.customAttrName] = reduce(reduceLambda, map(functools.partial(self.mapLambda, dp=dataPoint), self.attrListToProcess))
    def addCustomAttribute(self, dataPoints):
        for dataPoint in dataPoints:
            dataPoint.attributes[self.customAttrName] = self.calcLambda(dataPoint)

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
    allData = ExcelData.readDataFile('БАЗА 2018 на 20.03.2018_v04.xlsx', '', 'База 20.03.18', ExcelData.rng(1, 2808), ExcelData.rng(1, 138))
    print("Прочитано excel ячеек: "+str(len(allData.tablePoints)))
    # Переводим ячейки в точки с атрибутами
    dataPoints = DataPoint.makeDataPoints(allData, ExcelData.rng(2, 2808), ExcelData.rng(57, 138), {})
    print("Обработано точек данных: "+str(len(dataPoints)))
    # # Циклические
    # attr1 = CustomAttribute("Рек Циклические", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Циклические")
    # attr1.addCustomAttributeOR(dataPoints);
    # # Командные игровые
    # attr2 = CustomAttribute("Рек Командные игровые", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Командные игровые")
    # attr2.addCustomAttributeOR(dataPoints);
    # # Игровые
    # attr3 = CustomAttribute("Рек Игровые", ["Рек гр 1", "Рек гр 2", "Рек гр 3", "Рек гр 4"], "Игровые")
    # attr3.addCustomAttributeOR(dataPoints);
    attrAge = CustomAttribute("Возраст (год)", [], "", lambda dp: round(dp.attributes.get("Возраст",'')) if dp.isFloat else 0)
    attrAge.addCustomAttribute(dataPoints);
    attrVid = CustomAttribute("Группа видов спорта 1 (периф. зрение)", [], "", lambda dp: "" if dp.attributes.get("Группа видов спорта 1",'')=="10 - циклические" and (dp.attributes.get("Рекомендванный вид спорта 1",'')=="Плавание" or dp.attributes.get("Рекомендванный вид спорта 11",'')=="Плавание" or dp.attributes.get("Рекомендванный вид спорта 111",'')=="Плавание" ) else dp.attributes.get("Группа видов спорта 1",''))
    attrVid.addCustomAttribute(dataPoints);

    percentiles = [5, 25, 50, 75, 95]
    # Адаптационный потенциал
    groupedData_ПолВозрастЧСС = GroupedDataPoints.groupByList(dataPoints, ["Пол", "Возраст (год)", "ЧСС в покое"])
    groupedData_ПолВозрастСАД = GroupedDataPoints.groupByList(dataPoints, ["Пол", "Возраст (год)", "систолическое давление"])
    groupedData_ПолВозрастДАД = GroupedDataPoints.groupByList(dataPoints, ["Пол", "Возраст (год)", "диастолическое давление"])
    groupedData_ПолВозрастАП  = GroupedDataPoints.groupByList(dataPoints, ["Пол", "Возраст (год)", "Адаптационный потенциал"])
    print(groupedData_ПолВозрастЧСС)
    print(groupedData_ПолВозрастСАД)
    print(groupedData_ПолВозрастДАД)
    print(groupedData_ПолВозрастАП)
    perc_ПолВозрастЧСС = GroupedPoints.percentiles(groupedData_ПолВозрастЧСС, percentiles)
    perc_ПолВозрастСАД = GroupedPoints.percentiles(groupedData_ПолВозрастСАД, percentiles)
    perc_ПолВозрастДАД = GroupedPoints.percentiles(groupedData_ПолВозрастДАД, percentiles)
    perc_ПолВозрастАП = GroupedPoints.percentiles(groupedData_ПолВозрастАП, percentiles)
    print(perc_ПолВозрастЧСС)
    print(perc_ПолВозрастСАД)
    print(perc_ПолВозрастДАД)
    print(perc_ПолВозрастАП)

    # # Группируем по атрибутам "Пол", "Возраст (год)", "Группа видов спорта 1 (периф. зрение)"
    # groupedDataPolVozrastVid = GroupedDataPoints.groupByList(dataPoints, ["Пол", "Возраст (год)", "Группа видов спорта 1 (периф. зрение)", "Показатель"])
    # print(groupedDataPolVozrastVid)
    # percDataPolVozrast = GroupedPoints.percentiles(groupedDataPolVozrast, percentiles)
    # percDataDataPolVozrastVid = GroupedPoints.percentiles(groupedDataPolVozrastVid, percentiles)
    # print(percDataPolVozrast)
    # print(percDataDataPolVozrastVid)
    return

main()

