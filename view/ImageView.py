import pyqtgraph as pg
from view.Plot import removeExportFromContextMenu


class ImageView(pg.ImageView):
    def __init__(self, parent=None):
        pg.ImageView.__init__(self, parent)
        self.setWindowTitle('Image View')

        self.ui.roiBtn.hide()
        self.ui.menuBtn.hide()
        self.ui.roiPlot.setLabel('bottom','Frames')
        self.ui.roiPlot.setLabel('left','Fluorescence Int.')
        removeExportFromContextMenu(self.ui.roiPlot.sceneObj.contextMenu)
        self.hidePlot()


    def showPlot(self):
        plot = self.ui.roiPlot
        plot.setTitle('Object Mean')
        plot.showLabel('bottom', show=True)
        plot.showAxis('left')
        self.roiCurve.show()
        self.ui.splitter.setSizes([self.height()*0.6, self.height()*0.4])
        self.ui.roiPlot.setMouseEnabled(True, True)

    def hidePlot(self):
        plot = self.ui.roiPlot
        plot.setTitle(None)
        plot.showLabel('bottom', show=False)
        plot.hideAxis('left')
        self.roiCurve.hide()
        self.ui.splitter.setSizes([self.height()*0.9, self.height()*0.1])

    def addROI(self, pos, size, angle, pen, movable=True):
        roi = pg.EllipseROI(pos, size, angle=angle, pen=pen, movable=movable)
        self.getView().addItem(roi)
        return roi
