import numpy as np
from numpy import abs as np_abs
from numpy.fft import rfft, rfftfreq
from scipy import signal
from scipy.integrate import simps, trapz
import matplotlib.pyplot as plt
import os

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

    fig = plt.figure(num=filename+picsuffix, figsize=(40,15), dpi=100)
    figsize = 310 # 3 строки, 1 столбец

    figsize += 1
    spY = fig.add_subplot(figsize)
    spY.plot(t, y, 'b', alpha=0.75)
    spY.plot(t, yf, 'r--')
    spY.legend(('signal', 'lfilter'), loc='best')
    spY.grid(True)

    figsize += 1
    spS = fig.add_subplot(figsize)
    spS.plot(rfftfreq(N, 1./F), np_abs(spectrum)/N, 'b', alpha=0.75)
    spS.plot(rfftfreq(N, 1./F), np_abs(spectrumf)/N, 'r--')
    spS.legend(('signal spectrum', 'lfilter spectrum'), loc='best')
    spS.grid(True)    

    figsize += 1
    spW = fig.add_subplot(figsize) 
    spW.plot(fW, PdenW, 'b', alpha=0.75)
    spW.plot(fWf, PdenWf, 'r--')
    spW.legend(('signal welch', 'lfilter welch'), loc='best')
    spW.grid(True)

    # figsize += 1
    # spP = fig.add_subplot(figsize)
    # spP.plot(fP, PdenP, 'b', alpha=0.75)
    # spP.plot(fPf, PdenPf, 'r--')
    # spP.legend(('signal periodogram', 'lfilter periodogram'), loc='best')
    # spP.grid(True)

    plt.savefig(filename+'_'+picsuffix+'.png')
    #plt.show()

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

def doFilterForFiles(dir, freqrange):
    files = os.listdir(dir)
    files = filter(lambda f: f.endswith('.txt'), files)
    for onefile in files:
        filename = dir+'/'+onefile
        print(filename+'...')        
        doFilterForSingalAndIntegrals(filename, freqrange)
    print('done')

doFilterForFiles('/home/drew/Filters', [10, 1000])