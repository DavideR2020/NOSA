import pyqtgraph as pg
import matplotlib.pyplot as plt
import numpy as np

white = (254,254,254)

prop_cycle = plt.rcParams['axes.prop_cycle']
colors = prop_cycle.by_key()['color']
n = len(colors)

alternative = pg.mkColor(colors[0]).getRgb()
alternative_2 = pg.mkColor(colors[1]).getRgb()

colorMap = pg.ColorMap(np.linspace(0, 1, num=n-2), [pg.mkColor(clr).getRgb() for clr in colors[2:]])

def getColorTable(size):
    if size is None or size < n-2:
        size = n-2
    return colorMap.getLookupTable(nPts = size, alpha = False, mode = 'byte')