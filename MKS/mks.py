#%matplolib notebook

import warnings
warnings.simplefilter("ignore")

import matplotlib
matplotlib.use('Agg')

import os
import numpy as np
import pandas as pd
import scipy
from scipy import stats
from time import gmtime, strftime
from functools import reduce
import matplotlib.pyplot as plt
import seaborn as sns
import shutil

qualities = {0 : 'АНТРОПОМЕТРИЯ', 1 : 'ВЕСТ.УСТ-ТЬ', 2 : 'ГИБКОСТЬ', 3 : 'СКОРОСТЬ', 4 : 'СИЛА', 5 : 'СК-СИЛ', 6 : 'РАБОТОСП'}
qualitiesReadable = {1 : 'Вестибулярная устойчивость', 2 : 'Гибкость', 3 : 'Скорость', 4 : 'Сила', 5 : 'Скоростно-силовые', 6 : 'Физ. работоспособность'}
invertedOrder = {1: [2,3,4], 2: [2], 3 : [1,2], 6 : [1]}
idCol    = 'Num' 
nppCol   = '№ п/п'
sexCol   = 'Пол'
ageCol   = 'Хрон. возр.'
sportCol = 'Вид спорта'
groupCol = 'Группа подготовки'
clearSuffix   = '_clear'
percSuffix    = '_perc'
qualitySuffix = '_quality'
markSuffix = '_mark'
totalMarkName = 'total' + markSuffix
totalGroupCol = 'total_group'
fioCols = ['Фамилия', 'Имя', 'Отчество']

#PATH = 'drew@192.168.36.65:/home/drew/Moskomsport/'
PATH = '/home/drew/3_MKS_data/'

# Get time
def now():
    return strftime('%Y-%m-%d %H:%M:%S', gmtime())

# Process strings as float
def strToFloat(val):
    s = str(val)
    sig = -1 if (s!='-') & (s.startswith('-')) else 1
    s = s.replace('-','')
    s = s.replace(',','.')
    s = s.replace(' ','')
    try:
        result = sig * float(s)
    except ValueError:
        result = np.NaN
    return result

# Calc perc for one value
def calcPerc(df, groupCols, groupValues, curCol, value, inverted):
    result = 0
    if value is not None:
        dfFilter = df.copy()
        for i in range(len(groupCols)):
            dfFilter = dfFilter[dfFilter[groupCols[i]]==groupValues[i]]
        valueArray = dfFilter[curCol].values
        result = stats.percentileofscore(valueArray, value)
        if (result is None) | (result == np.NaN):
            result = 0
        else:
            if inverted==True:
                result = 100 - result
    return result

def saveDf(df, path, filename = 'df.csv'):
    df.to_csv(path_or_buf=os.path.join(path, filename))
    df.to_excel(os.path.join(path, filename+'.xlsx'))
    return

def fromXlsToPrepared(path):
    xlsPath = os.path.join(PATH, 'base2019_lite3.xlsx')

    df = pd.read_excel(xlsPath, sheet_name=None)
    dfList = [df[qualities[k]] for k in qualities.keys()]

    # first 100
    #for df in dfList:
    #   df = df.iloc[:100,:]

    dfMainFull = dfList[0]
    dfMain = dfMainFull[[idCol, nppCol] + fioCols + [sexCol, ageCol, sportCol, groupCol]]
    qIndexes = sorted(list(set(qualities.keys()).difference([0])))
    for index in qIndexes:
        df = dfList[index] # Проходим по всем листам с измеренными параметрами
        for colToRemove in [nppCol] + fioCols: # Исключаем колонки с ФИО и номером по порядку
            if colToRemove in df.columns:
                df.drop(colToRemove, axis=1, inplace=True)
        addCols = [idCol]
        for colIndex in range(1,len(df.columns)):
            colName = str(df.columns[colIndex])
            clearName = colName + '_' + str(index) + '_' + str(colIndex) + clearSuffix
            addCols.append(clearName)
            df[clearName] = df[colName].apply(strToFloat).astype(float)
        adAdd = df[addCols]
        dfMain = dfMain.join(adAdd.set_index(idCol), on=idCol)

    clearCols = [col for col in dfMain.columns if col.endswith(clearSuffix)==True]
    invertedOrderSet = set()
    for k in invertedOrder.keys():
        for l in invertedOrder[k]:
            invertedOrderSet.add((int(k),int(l)))
    for i in range(len(clearCols)):
        clearCol = clearCols[i]
        print(now(),i+1,'-',len(clearCols),':',clearCol,'...')
        percCol = clearCol.replace(clearSuffix, percSuffix)
        nameSplited = str(percCol).split('_')
        qAndI = (int(nameSplited[-3]),int(nameSplited[-2]))
        dfMain[percCol] = dfMain.apply(
            lambda row: calcPerc(dfMain, [sexCol, ageCol], [row[sexCol], row[ageCol]], clearCol, row[clearCol], qAndI in invertedOrderSet),
            axis=1
        )
    
    percCols = [col for col in dfMain.columns if col.endswith(percSuffix)==True]
    dfMain[percCols] = dfMain[percCols].fillna(0)
    percColsGroups = dict()
    for col in percCols:
        nameSplited = str(col).split('_')
        index = nameSplited[-3]
        group = percColsGroups.get(index, list())
        group.append(col)
        percColsGroups[index] = group

    markCols = list()
    for k in percColsGroups.keys():
        group = percColsGroups[k]
        qualityName = str(k) + qualitySuffix
        dfMain[qualityName] = dfMain[group].mean(axis=1)
        qualityMarkName = qualityName + markSuffix
        markCols.append(qualityMarkName)
        dfMain[qualityMarkName] = dfMain[qualityName].apply(lambda v: 0.25 if v<25 else 0.5 if v<50 else 0.75 if v<75 else 1).astype(float)

    dfMain[totalMarkName] = dfMain[markCols].sum(axis=1)
    # очень слабо - 1,5-2,25 балла, слабо - 2,5-3, нормально - 3,25-3,75, сильно - 4 и выше
    dfMain[totalGroupCol] = dfMain[totalMarkName].apply(lambda v: 'очень слабо' if v<=2.25 else 'слабо' if v<=3 else 'нормально' if v<=3.75 else 'сильно').astype(str)

    saveDf(dfMain, path, 'dfMain.csv')
    print(dfMain.head(15)) # to comment
    print(dfMain.shape)    # to comment
    return

def readPrepared(path):
    filepath = os.path.join(path, 'dfMain.csv')
    dfMain = pd.read_csv(filepath)
    #print(dfMain.head(15))
    #print(dfMain.shape)
    return dfMain

def buildBoxes(df, colList, path):
    qualityCols = [col for col in dfMain.columns if col.endswith(qualitySuffix)==True]
    qualityNamesDict = dict()
    qualityNamesList = list()
    for col in qualityCols:
        key = int(col.split('_')[0])
        qualityNamesDict[col] = qualitiesReadable[key]
        qualityNamesList.append(qualitiesReadable[key])
    colsValues = list()
    for col in colList:
        values = sorted(list(set(df[col].values)))
        colsValues.append(values)
    while len(colsValues)>1:
        firstList = colsValues[-2]
        secondList = colsValues[-1]
        combList = list()
        for first in firstList:
            for second in secondList:
                comb = list()
                if type(second) is list:
                    comb = second.copy()
                    comb.insert(0,first)
                else:
                    comb = list([first, second])
                combList.append(comb)
        colsValues.pop()
        colsValues.pop()
        colsValues.append(combList)

    colsValues = colsValues[0]
    
    dfQuantile = pd.DataFrame(columns=colList+qualityNamesList)
    
    nonEmptyDfList = list()
    for i in range(len(colsValues)):
        comb = colsValues[i]
        title = reduce(lambda x,y: str(x) + ',' + str(y), comb)
        print('Filter.',i+1,'-',len(colsValues),':',title)
        dfFiltered = df.copy()    
        for j in range(len(colList)):
            dfFiltered = dfFiltered[dfFiltered[colList[j]]==comb[j]]
        dfFiltered = dfFiltered[qualityCols]
        for col in dfFiltered.columns:
            dfFiltered[qualityNamesDict[col]] = dfFiltered[col]
            dfFiltered.drop(col,axis=1, inplace=True)
        if not dfFiltered.empty:
            nonEmptyDfList.append([comb, dfFiltered])
            qDf = pd.DataFrame(dfFiltered.quantile(q=0.5))
            qDf[str(i)] = qDf.iloc[:,0]
            qDf.drop(list(qDf.columns)[0],axis=1,inplace=True)
            qDf = qDf.T
            for j in range(len(colList)):
                qDf[colList[j]] = [comb[j]]
            dfQuantile = dfQuantile.append(qDf)

    dfQuantileSave = pd.DataFrame()
    dfQuantileSave[colList] = dfQuantile[colList]
    dfQuantileSave[qualityNamesList] = dfQuantile[qualityNamesList]
    
    folderName = reduce(lambda x,y: str(x) + '-' + str(y), colList)
    folderPath = path + folderName + '/'
    if os.path.exists(folderPath):
        shutil.rmtree(path=folderPath)
    os.makedirs(folderPath)
    saveDf(dfQuantileSave, folderPath, folderName + '.csv')
    
    for i in range(len(nonEmptyDfList)):
        comb, dfBox = nonEmptyDfList[i]
        title = reduce(lambda x,y: str(x) + ',' + str(y), comb)
        print('Draw.',i+1,'-',len(nonEmptyDfList),':',title)
        #ax = fig.add_subplot(len(nonEmptyDfList), 1, i+1)
        #sns.boxplot(data=dfBox, orient="h", ax=ax)
        #ax.set_title(title)

        plt.figure(figsize=(6,3))
        #plt.yticks(rotation=60)
        ax = sns.boxplot(data=dfBox, orient="h", **{'whis': 0, 'showcaps' : False, 'showfliers' : False})
        ax.set_title(title)
        plt.xlim(0, 100)
        plt.tight_layout()
        fileName = reduce(lambda x,y: str(x) + '-' + str(y), comb) + '.png'
        plt.savefig(os.path.join(folderPath, fileName), format='png')
            
    #fileName = reduce(lambda x,y: str(x) + '-' + str(y), colList) + '.png'
    #fig.savefig(os.path.join(path, fileName), format='png')
    #plt.show()
    
    return

fromXlsToPrepared(PATH) # to comment

dfMain = readPrepared(PATH) # read from dfMain.csv
dfMain[sportCol] = dfMain[sportCol].astype(str)
dfMain[sexCol] = dfMain[sexCol].astype(str)
dfMain[groupCol] = dfMain[groupCol].astype(str)
dfMain[totalGroupCol] = dfMain[totalGroupCol].astype(str)
qualityCols = [col for col in dfMain.columns if col.endswith(qualitySuffix)==True]
for col in qualityCols:
    dfMain[col] = dfMain[col].astype(float).apply(lambda v: np.NaN if v==0 else v)
#saveDf(dfMain, PATH, 'dfMain_NaN.csv')
#print(dfMain.dtypes)

buildBoxes(dfMain, [sportCol, sexCol], PATH)
buildBoxes(dfMain, [sportCol, sexCol, ageCol], PATH)
buildBoxes(dfMain, [sportCol, sexCol, groupCol], PATH)
buildBoxes(dfMain, [sportCol, sexCol, totalGroupCol], PATH)
buildBoxes(dfMain, [sportCol, sexCol, ageCol, totalGroupCol], PATH)
buildBoxes(dfMain, [sportCol, sexCol, groupCol, totalGroupCol], PATH)

dfMain = dfMain[dfMain[totalGroupCol]!='очень слабо']
buildBoxes(dfMain, [sportCol, sexCol], PATH+'part/')
