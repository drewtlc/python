import numpy as np
from numpy import abs as np_abs
from numpy.fft import rfft, rfftfreq
from scipy import signal
from scipy.integrate import simps, trapz
import matplotlib.pyplot as plt
import os

def makeFigure(figname, x1, y11, y12, leg11, leg12, x2, y21, y22, leg21, leg22, x3, y31, y32, leg31, leg32):
    fig = plt.figure(num=figname, figsize=(40,15), dpi=100)
    figsize = 310 # 3 строки, 1 столбец

    figsize += 1
    sp1 = fig.add_subplot(figsize)
    sp1.plot(x1, y11, 'b', alpha=0.75)
    sp1.plot(x1, y12, 'r--')
    sp1.legend((leg11, leg12), loc='best')
    sp1.grid(True)

    figsize += 1
    sp2 = fig.add_subplot(figsize)
    sp2.plot(x2, y21, 'b', alpha=0.75)
    sp2.plot(x2, y22, 'r--')
    sp2.legend((leg21, leg22), loc='best')
    sp2.grid(True)    

    figsize += 1
    sp3 = fig.add_subplot(figsize) 
    sp3.plot(x3, y31, 'b', alpha=0.75)
    sp3.plot(x3, y32, 'r--')
    sp3.legend((leg31, leg32), loc='best')
    sp3.grid(True)

    # figsize += 1
    # spP = fig.add_subplot(figsize)
    # spP.plot(fP, PdenP, 'b', alpha=0.75)
    # spP.plot(fPf, PdenPf, 'r--')
    # spP.legend(('signal periodogram', 'lfilter periodogram'), loc='best')
    # spP.grid(True)

    plt.savefig(figname+'.png')
    #plt.show()    

def doFilter(t, y, freqrange, filename, picsuffix):
    #data = np.genfromtxt(open(filename, encoding='Windows-1251'), dtype=(float, float), skip_header=18)
    #print(len(data))
    #print(data)
    # t = data[:,0]
    # y = data[:,1]
    T = (t[1] - t[0]) / 1000 # Интервал времени дискретизации. 1000 - переводит мс в с
    F = 1/T                  # Частота дискретизации
    nyq = F/2                # Частота Найквиста (половина от частоты дискретизации)
    Wn = freqrange/nyq
    N = len(t)

    b, a = signal.iirfilter(6, Wn, btype='bandpass', ftype='butter')
    yf = signal.lfilter(b, a, y)
    
    fW, PdenW = signal.welch(y, F)
    fWf, PdenWf = signal.welch(yf, F)

    fP, PdenP = signal.periodogram(y, F)
    fPf, PdenPf = signal.periodogram(yf, F)

    spectrum = rfft(y)
    spectrumf = rfft(yf)
    #print(spectrum[0], spectrum[0]/N, np_abs(spectrum[0]), np_abs(spectrum[0]/N), np.mean(y))
    #print(spectrumf[0], spectrumf[0]/N)

    makeFigure(filename+'_'+picsuffix, 
        t, y, yf, 'signal', 'lfilter',
        rfftfreq(N, 1./F), np_abs(spectrum)/N, np_abs(spectrumf)/N, 'signal spectrum', 'lfilter spectrum',
        fW, PdenW, PdenWf, 'signal welch', 'lfilter welch')

def integrateSignal(t, y, nomean):
    tI, yI = list(), list()
    m = np.mean(y)
    y_m = y if nomean==False else y-m
    blockSize = 2
    for i in range(0, len(t)-1):
        tblock = t[i:i+blockSize]
        yblock = y_m[i:i+blockSize]
        tI.append(tblock[0])
        yI.append(trapz(yblock, tblock))
    return np.asarray(tI), np.asarray(yI)

def doFilterForSingalAndIntegrals(filename, freqrange):
    data = np.genfromtxt(open(filename, encoding='Windows-1251'), dtype=(float, float), skip_header=18)
    t = data[:,0]
    y = data[:,1]
    doFilter(t, y, freqrange, filename, '0')
    tI, yI = integrateSignal(t, y, True)
    doFilter(tI, yI, freqrange, filename, '1')
    tI2, yI2 = integrateSignal(tI, yI, True)
    doFilter(tI2, yI2, freqrange, filename, '2')

def doFilterForIntegrals(filename, freqrange):
    data = np.genfromtxt(open(filename, encoding='Windows-1251'), dtype=(float, float), skip_header=18)
    t = data[:,0]
    y = data[:,1]
    tI, yI = integrateSignal(t, y, True)
    tII, yII = integrateSignal(tI, yI, True)

    T = (t[1] - t[0]) / 1000 # Интервал времени дискретизации. 1000 - переводит мс в с
    F = 1/T                  # Частота дискретизации
    nyq = F/2                # Частота Найквиста (половина от частоты дискретизации)
    Wn = freqrange/nyq

    b, a = signal.iirfilter(6, Wn, btype='bandpass', ftype='butter')
    yf = signal.lfilter(b, a, y)
    
    tIf, yIf = integrateSignal(t, yf, True)
    yIff = signal.lfilter(b, a, yIf)

    tIIf, yIIf = integrateSignal(tIf, yIff, True)

    fW, PdenW = signal.welch(yII, F)
    fWf, PdenWf = signal.welch(yIIf, F)

    N = len(tII)
    spectrum = rfft(yII)
    spectrumf = rfft(yIIf)    

    makeFigure(filename, 
        tII, yII, yIIf, 'signal 2 integ', 'lfilter 2 integ',
        rfftfreq(N, 1./F), np_abs(spectrum)/N, np_abs(spectrumf)/N, 'signal 2 integ spectrum', 'lfilter 2 integ spectrum',
        fW, PdenW, PdenWf, 'signal 2 integ welch', 'lfilter 2 integ welch')

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