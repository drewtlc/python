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
import gc

PATH = '/home/drew/4_MKS_Treners/'
groupCols = ['Вид спорта']
colStartIndex = 19

# Get time
def now():
    return strftime('%Y-%m-%d %H:%M:%S', gmtime())

def fromXls(path, colStart):
    qualityCols = list()
    xlsPath = os.path.join(PATH, 'analiz_mneniy_trenerov.xlsx')

    dfList = pd.read_excel(xlsPath, sheet_name=None)
    df = dfList[list(dfList.keys())[0]]
    for index in range(colStart, len(df.columns)):
        col = df.columns[index]
        df[col] = df[col].astype(str).fillna('')
        qualityCols.append(col)

    return df, qualityCols

def buildDiagrams(df, colList, qualityCols, path):
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
    
    nonEmptyDfList = list()
    for i in range(len(colsValues)):
        comb = colsValues[i]
        title = reduce(lambda x,y: str(x) + ',' + str(y), comb) if type(comb) is list else comb
        print('Filter.',i+1,'-',len(colsValues),':',title)
        dfFiltered = df.copy()    
        for j in range(len(colList)):
            dfFiltered = dfFiltered[dfFiltered[colList[j]]==(comb[j] if type(comb) is list else comb)]
        dfFiltered = dfFiltered[qualityCols]
        if not dfFiltered.empty:
            nonEmptyDfList.append([comb, dfFiltered])
    
    folderName = reduce(lambda x,y: str(x) + '-' + str(y), colList)
    folderPath = path + folderName + '/'
    if os.path.exists(folderPath):
        shutil.rmtree(path=folderPath)
    os.makedirs(folderPath)
    
    for i in range(len(nonEmptyDfList)):
        gc.collect()
        comb, dfBox = nonEmptyDfList[i]
        title = reduce(lambda x,y: str(x) + ',' + str(y), comb) if type(comb) is list else comb
        print('Draw.',i+1,'-',len(nonEmptyDfList),':',title)
        for j in range(len(dfBox.columns)):
            col = dfBox.columns[j]
            curValues = sorted(list(set(dfBox[col].values)))
            if (len(curValues)>1) or (len(curValues)==1 and curValues[0]!='nan'):
                print('     ',j+1,'-',len(dfBox.columns),':',col)
                plt.figure(figsize=(6,3))
                ax = sns.countplot(x=col, data=dfBox) #, orient="h", **{'whis': 0, 'showcaps' : False, 'showfliers' : False})
                ax.set_title(title+','+col)
                #plt.xlim(0, 100)
                #plt.tight_layout()
                fileName = title + ',' + col + '.png'
                fileName = fileName.replace(':',' ').replace('/',' ').replace('\\',' ')
                plt.savefig(os.path.join(folderPath, fileName), format='png')

    return

dfMain, qualityCols = fromXls(PATH, colStartIndex)
print(dfMain[qualityCols].head(10))
buildDiagrams(dfMain, groupCols, qualityCols, PATH)
