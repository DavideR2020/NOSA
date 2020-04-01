# load Modules
import numpy as np
from copy import deepcopy
from scipy import signal
from scipy.optimize import curve_fit
from scipy import ndimage
from scipy import sparse
from scipy.signal import butter, lfilter, lfilter_zi



## LEAST SQUARES FITTING ##

def func_exp(x, a, b, c):
    return a * np.exp(-b * x) + c

def func_lin(x, a, b):
    return a*x + b

def func_poly2(x, a, b, c):
    return a*np.float_power(x,2) + b*x + c

def func_poly3(x, a, b, c, d):
    return a*np.float_power(x,3) + b*np.float_power(x,2) + c*x + d

def func_poly4(x, c, d, e, f, g):
    return c*np.float_power(x,4) + d*np.float_power(x,3) + e*np.float_power(x,2) + f*x + g

def func_poly5(x, b, c, d, e, f, g):
    return b*np.float_power(x,5) + c*np.float_power(x,4) + d*np.float_power(x,3) + e*np.float_power(x,2) + f*x + g

def func_poly6(x, a, b, c, d, e, f, g):
    return a*np.float_power(x,6) + b*np.float_power(x,5) + c*np.float_power(x,4) + d*np.float_power(x,3) + e*np.float_power(x,2) + f*x + g

funcList = [func_lin,func_poly2,func_poly3, func_poly4,func_poly5,func_poly6]

# fit data
def fitting(x1, x2, y, intercept=0, degree=0):
    func = funcList[degree-1]
    if degree > 0 and degree <= 6:
        popt, _ = curve_fit(func, xdata=x2, ydata=y)
        fit = func(x1, *popt)
    else:
        fit = np.repeat(np.mean(y),len(x1))
    return fit+intercept

# d/dx
def getGradient(y, baseline):
    grad = np.zeros(len(y), dtype=float)
    for i in range(len(y)):
        bli = baseline[i]
        try:
            grad[i] = (float(y[i]-bli)/bli)*100
        except:
            pass
    return grad


## TOP HAT FILTER ##

def topHat(y, pntFactor):
    '''
    y -- numpy array
    pntFactor determines how finely the filter is applied to data.
    A point factor of 0.01 is appropriate for the tophat filter of Bruker MALDI mass spectra.
    A smaller number is faster but a trade-off is imposed
    Source: http://machc.blogspot.de/2008/12/tophat-filter.html
    '''
    struct_pts = int(round(y.size*pntFactor))
    str_el = np.repeat([1], struct_pts)
    tFil = ndimage.white_tophat(y, None, str_el)
    return y-tFil


## ASYMMETRIC LEAST SQUARES FILTER ##

def als(y, iterations, smooth, p=0.001):
    '''
    Title:
        Baseline Correction with Asymmetric Least Squares Smoothing
    Author:
        Paul H. C. Eilers, and Hans F. M. Boelens
    Date:
        21 October 2005
    Link:
        https://zanran_storage.s3.amazonaws.com/www.science.uva.nl/ContentPages/443199618.pdf

    code from:
        https://stackoverflow.com/a/50160920
        Stackoverflow user jpantina (https://stackoverflow.com/users/6126163/jpantina)
    '''
    smooth=smooth**3
    L = len(y)
    D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
    w = np.ones(L)
    for i in range(iterations):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + smooth * D.dot(D.transpose())
        z = sparse.linalg.spsolve(Z, w*y)
        w = p * (y > z) + (1-p) * (y < z)
    return z

## Moving Average

def movingAverage(y, window=11):
    if window > 0:
        # need an odd-sized window
        if window%2 == 0:
            window+=1
        # pad the original data with the half window size
        s = np.pad(y, int(window/2), mode='reflect')
        # get a hanning window
        w = np.hanning(window)
        # convolve the normalized hanning window with the padded data
        z = np.convolve(w / np.sum(w), s, mode='valid')
        return z
    else:
        return y

## Butterworth ##

def butter_lowpass_filter(y, freq, highcut, order):
    nyq = 0.5 * freq
    high = highcut / nyq
    b, a = butter(order, high, btype='lowpass')
    zi = lfilter_zi(b, a)
    z, _ = lfilter(b, a, y, zi = zi * y[0])
    return z


## Alternative Spike Detection ##

def findSpikes2(y, thresh, distance):
    peakind = signal.find_peaks_cwt(y, np.arange(1,10))
    return peakind

def findSpikes3(y, thresh, distance):
    #spikes = np.array([])
    i = 1
    n = len(y)
    yright = np.roll(y,1)
    yleft = np.roll(y,-1)
    x = np.arange(n)
    spikes = x[(y>thresh) & (y>=yright & y>=yleft)]
    j=0
    while j < len(spikes)-1:
        if (spikes[j+1]-spikes[j]) < distance:
            if y[spikes[j]]>y[spikes[j+1]]:
                np.delete(spikes,j+1)
            else:
                np.delete(spikes,j)
        else:
            j+=1
    return spikes
