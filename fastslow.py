# -*- coding: utf-8 -*-

# TODO:

from functools import reduce
import numpy
import scipy.stats
from base_module import Tools, DataPoint, ExcelData, GroupedDataPoints, GroupedPoints
import matplotlib.pyplot

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
        self.numbersM = None
        self.numbersW = None
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
            tests.numbersM = numbersM.copy()
            tests.numbersW = numbersW.copy()
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
    def diagrams(calcResults, file = ""):
        colorM = "blue"
        colorW = "red"
        alpha = 0.5
        figWidth = 10
        figHeight = 8
        keys = list(calcResults.keys())
        keys.sort()
        fig = matplotlib.pyplot.figure(figsize=(figWidth, figHeight*len(keys)))
        for index in range(len(keys)):
            key = keys[index]
            calcResult = calcResults[key]
            # Plot histogram
            ax = fig.add_subplot(len(keys), 1, index+1)
            ax.hist(calcResult.numbersM, len(calcResult.diagramM.cumcount), color=matplotlib.colors.to_rgba(colorM, alpha))
            ax.hist(calcResult.numbersW, len(calcResult.diagramW.cumcount), color=matplotlib.colors.to_rgba(colorW, alpha))
            ax.plot(calcResult.describeM.mean, 10, "bo")
            ax.plot(calcResult.describeW.mean, 10, "ro")
            ax.plot(calcResult.percentilesM[len(calcResult.percentilesM)//2], 10, "b^")
            ax.plot(calcResult.percentilesW[len(calcResult.percentilesW)//2], 10, "r^")
            ax.legend(["Среденее для мужчин", "Среденее для женщин", "Медиана для мужчин", "Медиана для женщин", "Распределение для мужчин", "Распределение для женщин"])
            ax.set_title(key)
        matplotlib.pyplot.show() if (file=="") else matplotlib.pyplot.savefig(file)
        return

# Основная программа (А.П.)
def main():
    # Читаем из файла
    allData = ExcelData.readDataFile("Таблица (все данные) v03.xlsx", '', "Данные", ExcelData.rng(1, 61), ExcelData.rng(1, 24))
    print("Прочитано excel ячеек: "+str(len(allData.tablePoints)))
    # Переводим ячейки в точки с атрибутами
    dataPoints = DataPoint.makeDataPoints(allData, ExcelData.rng(2, 61), ExcelData.rng(5, 24), {1 : "Показатель"})
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
    CalcResult.diagrams(res, "APResults.png")
    return

main()

