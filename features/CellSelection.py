# load Modules
from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
import math

from util.conf import cs_roi_params
from util import colors
from features.Feature import Feature
from view.ImageView import ImageView
from model.Object import Object

class CellSelection(Feature):

    def __init__(self, data, parent=None, liveplot=None):
        # Init Feature
        Feature.__init__(self, 'Cell Selection', data, parent, liveplot, display_name_label=False)

        self.data_manager = data
        self.data_manager.cell_selection = self

        self.setMinimumSize(350, 450)
        
        self.allowEditROI = True
        self.disabled_roi_handles = []
        self.preview_mode = True
        self.show_user_roi = False
        self.ellipse_mode = True
        self.update_on_ellipse_mode_change = True

        # data
        self.input = {'source':None, 'roi_ellipse_mode': None}
        self.output = {'cell':None, 'cell mean':None, 'roi':None}

        # view / plot
        self.imv = ImageView()
        self.imv.setMinimumHeight(450)
        self.layout.addWidget(self.imv)
        self.imv.view.mouseClickEvent = lambda ev: self.imvViewMouseClickEvent(self.imv.view, ev)
        self.imv.view.raiseContextMenu = lambda ev: self.imvViewRaiseContextMenu(self.imv.view, ev)
        self.imv.view.getContextMenus = lambda ev=None: self.imvViewGetContextMenus(self.imv.view, ev)

        self.imv.view.preview_mode = self.imv.view.menu.addAction('live preview mode')
        self.imv.view.preview_mode.setCheckable(True)
        self.imv.view.preview_mode.setChecked(self.preview_mode)
        self.imv.view.preview_mode.triggered.connect(self.switchPreviewMode)
        
        self.imv.view.ellipse_mode = self.imv.view.menu.addAction('ellipse mode')
        self.imv.view.ellipse_mode.setCheckable(True)
        self.imv.view.ellipse_mode.setChecked(self.ellipse_mode)
        self.connectEllipseMode()

        # methods
        self.addMethod('ROI', cs_roi_params, self.calculateROI)
        self.initMethodUI()
        self.initParametersUI()

        self.show()

        """
        the image must be displayed once such that the roicurve is created and can be shown
        even if the user loads a non-TIF source before he loads a TIF source.
        """
        self.imv.setImage(np.zeros((1, 10, 10)), xvals = np.arange(10))
        self.imv.clear()

    def show(self):
        Feature.show(self)
        self.refreshROIVisibleState()
        self.imv.getRoiPlot().enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    def refreshROIVisibleState(self):
        roi = self.methods['ROI'].getParametersGUI('roi')
        rect_roi = self.methods['ROI'].getParametersGUI('rect_roi')
        if not self.show_user_roi:
            if roi is not None:
                roi.hide()
            if rect_roi is not None:
                rect_roi.hide()
        elif self.ellipse_mode:
            if rect_roi is not None:
                rect_roi.hide()
        else:
            if roi is not None:
                roi.hide()

    def updateParametersUI(self):
        Feature.updateParametersUI(self)
        self.refreshROIVisibleState()


    def switchPreviewMode(self, checked):
        self.preview_mode = checked
        self.disconnectUserROISignals()
        self.connectUserROISignals()

    def connectEllipseMode(self):
        self.imv.view.ellipse_mode.triggered.connect(self.switchEllipseMode)

    def disconnectEllipseMode(self):
        try:
            self.imv.view.ellipse_mode.triggered.disconnect()
        except:
            pass

    def switchEllipseMode(self, checked):
        self.ellipse_mode = checked
        if self.ellipse_mode:
            show = 'roi'
            hide = 'rect_roi'
        else:
            show = 'rect_roi'
            hide = 'roi'
        self.methods['ROI'].getParametersGUI(show).show()
        self.methods['ROI'].getParametersGUI(hide).hide()
        if self.update_on_ellipse_mode_change:
            if not self.ellipse_mode:
                # if we just changed to rectangle mode: set angle to 0, pos and size and update graphics afterwards,
                # such that the pos and size are set correctly (rounded). but prevent calculation, because 
                # setObjectAttributes does it
                pos, size, _ = self.methods['ROI'].parameters['roi']
                rect_roi = self.methods['ROI'].getParametersGUI('rect_roi')
                self.disconnectUserROISignals()
                rect_roi.setPos(pos)
                rect_roi.setSize(size)
                rect_roi.setAngle(0)
                self.connectUserROISignals()
                self.updateROI(prevent_calculation = True)
            self.data.setObjectAttributes(self.data.object_selection, {'ellipse_mode': self.ellipse_mode})

    def imvViewGetContextMenus(self, view, ev=None):
        return view.menu

    def imvViewRaiseContextMenu(self, view, ev):
        # return if we are not in user mode
        if not self.show_user_roi:
            return
        menu = view.getContextMenus()
        
        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
        return True

    def imvViewMouseClickEvent(self, view, ev):
        if ev.button() == QtCore.Qt.RightButton:
            if view.raiseContextMenu(ev):
                ev.accept()

    def initParametersUI(self):
        pos, size, angle = self.methods['ROI'].parameters['roi']
        pen = pg.mkPen(color=colors.alternative)
        roi = self.methods['ROI'].initROI(self.imv, pos, size, angle, pen, updateFunc=self.updateROIOnlyProcessed, releaseFunc=self.updateROIAll)
        roi.setZValue(20)
        pos = (math.floor(pos[0]), math.floor(pos[1]))
        size = (math.ceil(size[0]), math.ceil(size[1]))
        rect_roi = self.methods['ROI'].initRectROI(self.imv, pos, size, pen, updateFunc=self.updateROIOnlyProcessed, releaseFunc=self.updateROIAll)
        rect_roi.setZValue(20)
        rect_roi.hide()
        self.updateParametersUI()

    def inputConfiguration(self):
        source = self.input['source']
        if source is not None:
            if source.filetype == 'tif':
                if not np.array_equal(self.imv.image, source.getData()):
                    self.imv.setImage(source.getData(), xvals = source.frameRange())
                    self.imv.showPlot()
                    if not (source.start <= self.imv.timeLine.value() <= source.end):
                        self.imv.timeLine.setValue(source.start)
                self.show_user_roi = True
            else:
                self.imv.clear()
                self.imv.showPlot()
                self.imv.roiCurve.setData(source.frameRange(), source.getData())
                self.imv.timeLine.hide()
                self.show_user_roi = False
                self.refreshROIVisibleState()
                self.imv.getRoiPlot().enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
            ellipse_mode = self.input['roi_ellipse_mode']
            if ellipse_mode is not None:
                # set attribute s.t. we do not update. the reason behind that is that inputConfiguration should never update.
                self.update_on_ellipse_mode_change = False
                self.disconnectEllipseMode()
                self.imv.view.ellipse_mode.setChecked(ellipse_mode)
                self.switchEllipseMode(ellipse_mode)
                self.connectEllipseMode()
                self.update_on_ellipse_mode_change = True
        else:
            self.imv.hidePlot()
            self.imv.clear()
            self.show_user_roi = False
            self.getUserROI().hide()

    def updateROIAll(self):
        self.updateROI(only_processed = False)

    def updateROIOnlyProcessed(self):
        self.updateROI(only_processed = True)
    
    def updateROI(self, only_processed = False, prevent_calculation = False):
        if self.ellipse_mode:
            ellipse_roi = self.methods['ROI'].getParametersGUI('roi')
            self.methods['ROI'].parameters['roi'] = (ellipse_roi.pos(),ellipse_roi.size(),ellipse_roi.angle())
        else:
            rect_roi = self.methods['ROI'].getParametersGUI('rect_roi')
            pos = rect_roi.pos()
            size = rect_roi.size()
            pos = (round(pos[0]), round(pos[1]))
            size = (round(size[0]), round(size[1]))
            self.methods['ROI'].parameters['roi'] = (pos,size,0)

        if not prevent_calculation:
            self.update(stop_after_processing = only_processed and self.preview_mode)

    def calculateROI(self, source, roi_ellipse_mode, roi):
        if source.filetype == 'tif':

            img = self.imv.getProcessedImage()

            if roi_ellipse_mode:
                ellipse_roi = self.methods['ROI'].getParametersGUI('roi')
                pos, size, angle = self.methods['ROI'].parameters['roi']
                self.disconnectUserROISignals()
                ellipse_roi.setPos(pos)
                ellipse_roi.setSize(size)
                ellipse_roi.setAngle(angle)
                self.connectUserROISignals()
                cell = ellipse_roi.getArrayRegion(img.view(np.ndarray), self.imv.imageItem, axes=(1,2))
            else:
                rect_roi = self.methods['ROI'].getParametersGUI('rect_roi')
                pos, size, _ = self.methods['ROI'].parameters['roi']
                self.disconnectUserROISignals()
                rect_roi.setPos(pos)
                rect_roi.setSize(size)
                rect_roi.setAngle(0)
                self.connectUserROISignals()
                _slice = rect_roi.getArraySlice(img.view(np.ndarray), self.imv.imageItem, axes=(1,2))
                cell = img[_slice[0]]

            # Get ROI mean data
            cell_mean = cell.mean(axis=(1,2))

            # read roi params out of saved params
            pos, size, angle = self.methods['ROI'].parameters['roi'] 
            
            return {'cell':cell,'cell mean':cell_mean,'roi':(cell_mean, pos, size, angle)}
        else:
            return {'cell': None, 'cell mean': None, 'roi': None}

    def editROI(self, roi_index):
        if self.allowEditROI and self.input['source'].filetype == 'tif':
            method = self.getMethod()
            pos, size, angle = method.parameters['roi']
            cell_mean = self.output['cell mean']
            cell = self.output['cell']
            edit_data = {
                'cell_mean': cell_mean,
                'cell': cell,
                'pos': pos,
                'angle': angle,
                'size': size
            }
            self.data_manager.setObjectAttributes(roi_index, edit_data, prevent_object_manager_refresh = True, prevent_roiview_refresh = True)

    def updateLivePlot(self):
        pass

    def getUserROI(self):
        param_name = 'roi' if self.ellipse_mode else 'rect_roi'
        return self.methods['ROI'].getParametersGUI(param_name)

    def disconnectUserROISignals(self):
        roi_view = self.getUserROI()
        try:
            roi_view.sigRegionChanged.disconnect()
        except:
            pass
        roi_view.sigRegionChangeFinished.disconnect()

    def connectUserROISignals(self):
        roi_view = self.getUserROI()
        if self.preview_mode:
            roi_view.sigRegionChanged.connect(self.updateROIOnlyProcessed)
        roi_view.sigRegionChangeFinished.connect(self.updateROIAll)
            