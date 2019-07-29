import numpy as np
from numpy.fft import rfft, rfftfreq, irfft
from scipy import signal
from scipy.integrate import simps, trapz
import matplotlib.pyplot as plt
import os

def alignLen(x,y):
    return y if len(y)==len(x) else np.concatenate((y, np.zeros(len(x)-len(y))))

def makeFigure(figname, params):
    plotsCount = len(params)
    fig = plt.figure(num=figname, figsize=(40,5*plotsCount), dpi=100)
    figsize = 100*plotsCount + 10 # plotsCount строк, 1 столбец
    colors = ['r', 'g', 'b']
    lines, alllines = ['-','--','-.'], []
    for line in lines:
        alllines = np.concatenate((alllines, np.repeat(line, len(colors))))
    for param in params:
        figsize += 1
        sp = fig.add_subplot(figsize)
        x = param[0]
        yList = param[1]
        legList = param[2]
        for i in range(len(yList)):
            y = yList[i]
            plotY = alignLen(x, y)
            color = colors[i % len(colors)]
            line = alllines[i % len(alllines)]
            sp.plot(x, plotY, color, linestyle=line)
            # sp.plot(x1, y12, 'r--')
        sp.legend(legList, loc='best')
        sp.grid(True)

    plt.savefig(figname+'.png')
    #plt.show()    

# def doFilter(t, y, freqrange, filename, picsuffix):
#     #data = np.genfromtxt(open(filename, encoding='Windows-1251'), dtype=(float, float), skip_header=18)
#     #print(len(data))
#     #print(data)
#     # t = data[:,0]
#     # y = data[:,1]
#     T = (t[1] - t[0]) / 1000 # Интервал времени дискретизации. 1000 - переводит мс в с
#     F = 1/T                  # Частота дискретизации
#     nyq = F/2                # Частота Найквиста (половина от частоты дискретизации)
#     Wn = freqrange/nyq
#     N = len(t)

#     b, a = signal.iirfilter(6, Wn, btype='bandpass', ftype='butter')
#     yf = signal.lfilter(b, a, y)
    
#     fW, PdenW = signal.welch(y, F)
#     fWf, PdenWf = signal.welch(yf, F)

#     fP, PdenP = signal.periodogram(y, F)
#     fPf, PdenPf = signal.periodogram(yf, F)

#     spectrum = rfft(y)
#     spectrumf = rfft(yf)
#     #print(spectrum[0], spectrum[0]/N, np.abs(spectrum[0]), np.abs(spectrum[0]/N), np.mean(y))
#     #print(spectrumf[0], spectrumf[0]/N)

#     makeFigure(filename+'_'+picsuffix, 
#         [[t, [y, yf], ['signal', 'lfilter']],
#         [rfftfreq(N, 1./F), [np.abs(spectrum)/N, np.abs(spectrumf)/N], ['signal spectrum', 'lfilter spectrum']],
#         [fW, [PdenW, PdenWf], ['signal welch', 'lfilter welch']]])

def integrateSignal(t, y, nomean):
    tI, yI, I = list(), list(), 0
    m = np.mean(y)
    y_m = y if nomean==False else y-m
    blockSize = 2
    for i in range(0, len(t)-1):
        tblock = t[i:i+blockSize]
        yblock = y_m[i:i+blockSize]
        I += trapz(yblock, tblock)
        tI.append(tblock[0])
        yI.append(I)
    return np.asarray(tI), np.asarray(yI)

def diffSignal(t, y):
    td, yd = list(), list()
    blockSize = 2
    for i in range(0, len(t)-1):
        tblock = t[i:i+blockSize]
        yblock = y[i:i+blockSize]
        td.append(tblock[0])
        yd.append((yblock[1]-yblock[0])/(tblock[1]-tblock[0]))
    return np.asarray(td), np.asarray(yd)

# def doFilterForSingalAndIntegrals(filename, freqrange):
#     data = np.genfromtxt(open(filename, encoding='Windows-1251'), dtype=(float, float), skip_header=18)
#     t = data[:,0]
#     y = data[:,1]
#     doFilter(t, y, freqrange, filename, '0')
#     tI, yI = integrateSignal(t, y, True)
#     doFilter(tI, yI, freqrange, filename, '1')
#     tI2, yI2 = integrateSignal(tI, yI, True)
#     doFilter(tI2, yI2, freqrange, filename, '2')

def filterRFFT(freq, spectr, level=0.001):
    freqFilter, spectrFilter = list(), list()
    flt = filter(lambda t: np.abs(t[1])>level, zip(freq, spectr))
    for f,s in flt:
        freqFilter.append(f)
        spectrFilter.append(s)
    return np.asarray(freqFilter), np.asarray(spectrFilter)

def doFilterForIntegrals(filename, freqrange):
    data = np.genfromtxt(open(filename, encoding='Windows-1251'), dtype=(float, float), skip_header=18)
    t = data[:,0]
    y = data[:,1]

    # m = np.mean(y)
    # y = np.ones(len(t))
    # Генерируем тестовый сигнал. Фильтр будет работать в полосе [10, 1000]
    y1 = np.sin(2*np.pi*t/1000*80)          # 80 Гц
    y2 = np.sin(2*np.pi*t/1000*1005)        # 1005 Гц
    y3 = np.sin(2*np.pi*t/1000*5)           # 5 Гц
    y4 = np.sin(2*np.pi*t/1000*0.5)*0.001   # 0.5 Гц и малая амплитуда
    y = y1+y2+y3+y4

    T = (t[1] - t[0]) / 1000 # Интервал времени дискретизации. 1000 - переводит мс в с
    F = 1/T                  # Частота дискретизации
    nyq = F/2                # Частота Найквиста (половина от частоты дискретизации)
    Wn = freqrange/nyq

    #sp = rfft(y)
    #sp_abs = np.abs(sp)
    #sp2 = sp_abs[700:900]

    #y_r = irfft(sp)
    #err = y-y_r

    freqFilterY, spectrFilterY = filterRFFT(rfftfreq(len(t), 1./F), rfft(y), 0.1)
    freqSpAbsFilter = list(map(lambda t: list([t[0], t[1][1], t[1][0]]), zip(freqFilterY, zip(spectrFilterY, np.abs(spectrFilterY)))))

    b, a = signal.iirfilter(6, Wn, btype='bandpass', ftype='butter')
    yf = signal.lfilter(b, a, y)                 # фильтрованный сигнал

    #spf = rfft(yf)
    #spf_abs = np.abs(spf)

    tI, yI = integrateSignal(t, y, False)         # первый интеграл сигнала
    yIm = yI - np.mean(yI)                       # первый интеграл сигнала за вычетом средней
    yIf = signal.lfilter(b, a, yI)               # фильтрованный первый интеграл сигнала
    tfI, yfI = integrateSignal(t, yf, False)      # первый интеграл фильтрованного сигнала
    yfIf = signal.lfilter(b, a, yfI)             # фильтрованный первый интеграл фильтрованного сигнала
    
    # print('mean(yI)='+str(np.mean(yI))+', mean(yIf)='+str(np.mean(yIf))) 
    _, yd = diffSignal(tI, yI)
    s = np.sum(np.std(y-alignLen(y, yd)))
    print(s)

    tII, yII = integrateSignal(tI, yI, False)     # второй интеграл сигнала
    #yIIm = yII - np.mean(yII)                    # второй интеграл сигнала за вычетом средней
    yIIf = signal.lfilter(b, a, yII)             # фильтрованный второй интеграл сигнала
    _, yfII = integrateSignal(tfI, yfI, False) # второй интеграл фильтрованного сигнала
    yfIIf = signal.lfilter(b, a, yfII)           # фильтрованный второй интеграл фильтрованного сигнала

    fW, W = signal.welch(y, F)
    _, Wf = signal.welch(yf, F)

    fWI, WI = signal.welch(yI, F)
    _, WIf = signal.welch(yIf, F)
    _, WfI = signal.welch(yfI, F)
    _, WfIf = signal.welch(yfIf, F)

    fWII, WII = signal.welch(yII, F)
    _, WIIf = signal.welch(yIIf, F)
    _, WfII = signal.welch(yfII, F)
    _, WfIIf = signal.welch(yfIIf, F)

    #N = len(tII)
    #spectrumII = rfft(yII)
    #spectrumIIf = rfft(yIIf)    
    #spectrumfII = rfft(yfII)    

    #freqFilter, spectrFilter = filterRFFT(rfftfreq(len(tII), 1./F), rfft(yII), 0.1)

    makeFigure(filename, 
        [[t, [y, yf, yd], ['сигнал', 'фильтрованный сигнал', 'инт/диф сигнал']],
        [fW, [W, Wf], ['спектр сигнала по Уэлчу', 'спектр фильтрованного сигнала по Уэлчу']],
        [tI, [yI, yIm, yIf, yfI, yfIf], ['первый интеграл сигнала', 'первый интеграл сигнала за вычетом средней', 'фильтрованный первый интеграл сигнала', 'первый интеграл фильтрованного сигнала', 'фильтрованный первый интеграл фильтрованного сигнала']],
        [fWI, [WI, WIf, WfI, WfIf], ['спектр первого интеграла сигнала по Уэлчу', 'спектр фильтрованного первого интеграла сигнала по Уэлчу', 'спектр первого интеграла фильтрованного сигнала по Уэлчу', 'спектр фильтрованного первого интеграла фильтрованного сигнала по Уэлчу']],
        [tII, [yII, yIIf, yfII, yfIIf], ['второй интеграл сигнала', 'фильтрованный второй интеграл сигнала', 'второй интеграл фильтрованного сигнала', 'фильтрованный второй интеграл фильтрованного сигнала']],
        #[rfftfreq(N, 1./F), [np.abs(spectrumII)/N, np.abs(spectrumIIf)/N, np.abs(spectrumfII)/N], ['спектр второго интеграла сигнала', 'спектр фильтрованного второго интеграла сигнала', 'спектр второго интеграла фильтрованного сигнала']],
        [fWII, [WII, WIIf, WfII, WfIIf], ['спектр второго интеграла сигнала по Уэлчу', 'спектр фильтрованного второго интеграла сигнала по Уэлчу', 'спектр второго интеграла фильтрованного сигнала по Уэлчу', 'спектр фильтрованного второго интеграла фильтрованного сигнала по Уэлчу']]])

def doFilterForFiles(dir, freqrange):
    files = os.listdir(dir)
    files = filter(lambda f: f.endswith('.txt'), files)
    for onefile in files:
        filename = dir+'/'+onefile
        print(filename+'...')        
        # doFilterForSingalAndIntegrals(filename, freqrange)
        doFilterForIntegrals(filename, freqrange)
    # print('done')

doFilterForFiles('/home/drew/Filters', [10, 1000])