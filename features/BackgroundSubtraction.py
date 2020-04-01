# load Modules
from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
import math


from util.conf import bs_roi_params, bs_perisomatic_params
from util import colors
from features.Feature import Feature
from view.ImageView import ImageView

class BackgroundSubtraction(Feature):

    def __init__(self, data, parent=None, liveplot=None):

        # Init Feature
        Feature.__init__(self, 'Background Subtraction', data, parent, liveplot)

        # data
        self.input = {'y': None, 'roi_params':None, 'roi_image':None, 'cell': None, 'roi_ellipse_mode': None}
        self.output = {'background mean':None, 'y':None}

        self.imv = self.liveplot
        self.activateFunc = self.showGUI

        ## METHODS ##

        # 1 ROI Background Subtraction
        self.addMethod('ROI', bs_roi_params, self.ROIBackgroundSubtraction)

        # 2 Perisomatic Background Subtraction
        self.addMethod('Perisomatic', bs_perisomatic_params, self.perisomaticBackgroundSubtraction)

        self.initMethodUI()
        self.initParametersUI()

        self.undisplayPlots()

    def initParametersUI(self):

        pen = pg.mkPen(color=colors.alternative, style=QtCore.Qt.DotLine, width=2)

        # 1 ROI 
        pos, size, angle = self.methods['ROI'].parameters['background_roi']
        roi = self.methods['ROI'].initROI(self.imv, pos, size, angle, pen, updateFunc=self.updateROIOnlyProcessed, releaseFunc=self.updateROIAll)
        roi.setZValue(10)
        rect_roi = self.methods['ROI'].initRectROI(self.imv, pos, size, pen, updateFunc=self.updateROIOnlyProcessed, releaseFunc=self.updateROIAll)
        rect_roi.setZValue(10)
        rect_roi.hide()

        # 2 Perisomatic
        self.methods['Perisomatic'].initSlider('radius', slider_params=(1,25,1,1), updateFunc=self.updateOnlyProcessed, releaseFunc=self.update)
        p_roi = self.methods['Perisomatic'].initROI(self.imv, 0, 10, 0, pen)
        p_roi.setZValue(10)
        for h in p_roi.getHandles():
            p_roi.removeHandle(h)
        p_rect_roi = self.methods['Perisomatic'].initRectROI(self.imv, 0, 10, pen)
        p_rect_roi.setZValue(10)
        for h in p_rect_roi.getHandles():
            p_rect_roi.removeHandle(h)
        p_rect_roi.hide()

        self.updateParametersUI()

    def updateLivePlot(self):
        roi_to_show = 'rect_roi' if (self.input['roi_ellipse_mode'] is not None and not self.input['roi_ellipse_mode']) else 'roi'
        self.getMethod().getParametersGUI(roi_to_show).show()

    def showGUI(self):
        curr_pipeline = self.data.getCurrentPipeline()
        if self.active and self is curr_pipeline._background_subtraction:
            if self.input['roi_ellipse_mode'] is not None and not self.input['roi_ellipse_mode']:
                show = 'rect_roi'
                hide = 'roi'
            else:
                show = 'roi'
                hide = 'rect_roi'
            roi_show = self.getMethod().getParametersGUI(show)
            if roi_show is not None:
                # show roi of that method
                roi_show.show()
            roi_hide = self.getMethod().getParametersGUI(hide)
            if roi_hide is not None:
                roi_hide.hide()
            

    def activateLivePlot(self):
        pass

    def clear(self):
        self.clearData()
        self.undisplayPlots()

    def undisplayPlots(self):
        Feature.undisplayPlots(self)

        # hide the self rois
        for roi_name in ['roi', 'rect_roi']:
            roi_view = self.getMethod().getParametersGUI(roi_name)
            if roi_view is not None:
                roi_view.hide()

    def updateOnlyProcessed(self, *args):
        if self.data.cell_selection.preview_mode:
            self.update(stop_after_processing=True)

    def updateROIOnlyProcessed(self, *args):
        self.updateROI(only_processed = True)

    def updateROIAll(self, *args):
        self.updateROI(only_processed = False)

    def updateROI(self, only_processed):
        if self.input['roi_ellipse_mode']:
            background_roi = self.methods['ROI'].getParametersGUI('roi')
            self.methods['ROI'].parameters['background_roi'] = (background_roi.pos(),background_roi.size(),background_roi.angle())
        else:
            background_roi = self.methods['ROI'].getParametersGUI('rect_roi')
            pos = background_roi.pos()
            size = background_roi.size()
            pos = (math.floor(pos[0]), math.floor(pos[1]))
            size = (math.ceil(size[0]), math.ceil(size[1]))
            self.methods['ROI'].parameters['background_roi'] = (pos,size,0)
        if only_processed and self.data.cell_selection.preview_mode:
            self.update(stop_after_processing = True)
        else:
            self.update()

    def disconnectUserROISignals(self):
        name = 'roi' if self.input['roi_ellipse_mode'] else 'rect_roi'
        roi = self.methods['ROI'].getParametersGUI(name)
        try:
            roi.sigRegionChanged.disconnect()
        except:
            pass
        roi.sigRegionChangeFinished.disconnect()

    def connectUserROISignals(self):
        name = 'roi' if self.input['roi_ellipse_mode'] else 'rect_roi'
        roi = self.methods['ROI'].getParametersGUI(name)
        if self.data.cell_selection.preview_mode:
            roi.sigRegionChanged.connect(self.updateROIOnlyProcessed)
        roi.sigRegionChangeFinished.connect(self.updateROIAll)

    # roi background subtraction
    def ROIBackgroundSubtraction(self, y, roi_params, roi_image, cell, roi_ellipse_mode, background_roi):
        """Subtract the mean value of the background ROI from cell mean (frame by frame)."""

        img = self.imv.getProcessedImage()

        if self.input['roi_ellipse_mode']:
            pos, size, angle = self.methods['ROI'].parameters['background_roi']
            background_roi = self.methods['ROI'].getParametersGUI('roi')
            self.disconnectUserROISignals()
            background_roi.setPos(pos)
            background_roi.setSize(size)
            background_roi.setAngle(angle)
            self.connectUserROISignals()
            background = background_roi.getArrayRegion(img.view(np.ndarray), self.imv.imageItem, axes=(1,2))
        else:
            pos, size, _ = self.methods['ROI'].parameters['background_roi']
            background_roi = self.methods['ROI'].getParametersGUI('rect_roi')
            self.disconnectUserROISignals()
            background_roi.setPos(pos)
            background_roi.setSize(size)
            background_roi.setAngle(0)
            self.connectUserROISignals()
            _slice = background_roi.getArraySlice(img.view(np.ndarray), self.imv.imageItem, axes=(1,2))
            background = img[_slice[0]]

        # get background roi mean
        background_mean = background.mean(axis=(1,2))

        return {'background mean': background_mean, 'y': y - background_mean}

    # perisomatic background subtraction
    def perisomaticBackgroundSubtraction(self, y, roi_params, roi_image, cell, roi_ellipse_mode, radius):
        """Subtract the mean value of the area around cell (defined by radius) from cell mean."""

        pos, size, angle = roi_params

        # save user defined radius in parameters
        self.methods['Perisomatic'].parameters['radius'] = radius

        # get perisomatic roi and set its radius
        roi_name = 'roi' if roi_ellipse_mode else 'rect_roi'
        p_roi = self.methods['Perisomatic'].getParametersGUI(roi_name)
        angle_of_position = math.radians(angle-135)
        shift_x = math.sqrt(2) * math.cos(angle_of_position) * radius / 2
        shift_y = math.sqrt(2) * math.sin(angle_of_position) * radius / 2
        p_roi.setPos((pos[0] + shift_x, pos[1] + shift_y))
        p_roi.setSize((size[0] + radius, size[1] + radius))
        p_roi.setAngle(angle)

        # get perisomatic roi data
        img = self.imv.getProcessedImage()
        if roi_ellipse_mode:
            p_cell = p_roi.getArrayRegion(img.view(np.ndarray), self.imv.imageItem, axes=(1,2))
        else:
            _slice = p_roi.getArraySlice(img.view(np.ndarray), self.imv.imageItem, axes=(1,2))
            p_cell = img[_slice[0]]

        # get roi mean. subtract cell mean because p_cell contains the cell and the area around it
        p_ring = np.sum(p_cell, axis=(1,2)) - np.sum(cell, axis=(1,2))
        _, p1, p2 = p_cell.shape
        _, c1, c2 = cell.shape
        p_ring_size = (p1 * p2) - (c1 * c2)
        background_mean = p_ring / p_ring_size

        return {'background mean': background_mean, 'y': y - background_mean}
