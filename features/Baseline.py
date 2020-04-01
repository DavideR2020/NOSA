from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
from copy import copy

from util.conf import bl_moving_average_params, bl_asymmetric_ls_params, bl_polynomial_fitting_params, bl_top_hat_params
from util import colors
from util.functions import fitting, getGradient, topHat, als, movingAverage, butter_lowpass_filter
from features.Feature import Feature

class Baseline(Feature):

    def __init__(self, data, parent=None, liveplot=None):

        # Init Feature
        Feature.__init__(self, 'Baseline', data, parent, liveplot)

        self.liveplot_container, self.liveplot = self.liveplot

        # data
        self.input = {'y': None, 'object_source': None}
        self.output = {'baseline': None, 'y': None}

        # methods
        # 1 Polynomial Fitting
        self.addMethod('Polynomial Fitting', bl_polynomial_fitting_params, self.polyFit)
        self.markerItems = []
        # 2 Asymmetric Least Squares
        self.addMethod('Asymmetric Least Squares', bl_asymmetric_ls_params, self.alsWrapper)
        # 3 Top Hat
        self.addMethod('Top Hat', bl_top_hat_params, self.topHatWrapper)
        # 4 Moving Average
        self.addMethod('Moving Average', bl_moving_average_params, self.movingAverageWrapper)

        self.activateFunc = self.showMarkers

        self.initMethodUI()
        self.initParametersUI()

    def show(self):
        Feature.show(self)
        polynomial_fitting = self.methods['Polynomial Fitting']
        if self.getMethod() is polynomial_fitting and not polynomial_fitting.getParametersGUI('use_marker').isChecked(): 
            self.methods['Polynomial Fitting'].getParametersGUI('Add Marker').hide()
            self.layout.update()

    def initParametersUI(self):

        updateFunc = self.update
        # poly fit
        self.methods['Polynomial Fitting'].initSlider('polyorder', slider_params=(0,6,1,1), updateFunc=updateFunc)
        self.methods['Polynomial Fitting'].getParametersGUI('polyorder').setAbsolutes(0, 6)
        self.methods['Polynomial Fitting'].initSlider('intercept', slider_params=(0,500,20,1), updateFunc=updateFunc)
        self.methods['Polynomial Fitting'].initCheckbox('use_marker', updateFunc=self.activateMarkers, label='Use Baseline Markers')
        self.methods['Polynomial Fitting'].initButton('Add Marker', updateFunc=self.addMarkerButtonClick)     
        self.methods['Polynomial Fitting'].getParametersGUI('Add Marker').hide()
        # als
        self.methods['Asymmetric Least Squares'].initSlider('smooth', slider_params=(3,1000,1,1), updateFunc=updateFunc)
        self.methods['Asymmetric Least Squares'].initSlider('iterations', slider_params=(1,10,1,1), updateFunc=updateFunc)
        self.methods['Asymmetric Least Squares'].initSlider('intercept', slider_params=(0,500,20,1), updateFunc=updateFunc)
        # top hat
        self.methods['Top Hat'].initSlider('factor', slider_params=(1,1000,1,0.001), updateFunc=updateFunc)
        # ma
        self.methods['Moving Average'].initSlider('window', slider_params=(4,1000,1,1), updateFunc=updateFunc)
        # update GUI
        self.updateParametersUI()

    def updateLivePlot(self):
        seconds_range = self.input['object_source'].frameRange()
        baseline = self.output['baseline']
        if baseline is None or len(baseline) != len(seconds_range):
            self.liveplot.setData([], [])
        else:
            self.liveplot.setData(seconds_range, baseline)
        self.clearMarkers()
        self.showMarkers()

    ## METHOD FUNCTIONS ##

    def alsWrapper(self, y, object_source, iterations, smooth, intercept, p=0.001):
        try:
            baseline = als(y, iterations, smooth, p) + intercept
        except:
            warning = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning,
                'Method not available',
                'Asymmetric Least Squares does not work with the data. This is probably due to a memory error. Please choose another method.',
                buttons = QtWidgets.QMessageBox.Ok,
                parent = self.data.parent
                )
            warning.setWindowModality(QtCore.Qt.NonModal)
            warning.finished.connect(lambda: self.method_combo.setCurrentIndex(0))
            warning.show()
            return {'baseline': None, 'y': None}
        if object_source.filetype == 'tif':
            y = getGradient(y, baseline)
        else:
            y = y - baseline
        return {'baseline': baseline, 'y': y}

    def topHatWrapper(self, y, object_source, factor):
        baseline = topHat(y, factor)
        if object_source.filetype == 'tif':
            y = getGradient(y, baseline)
        else:
            y = y - baseline
        return {'baseline': baseline, 'y': y}

    def movingAverageWrapper(self, y, object_source, window=11):
        baseline = movingAverage(y, window)
        if object_source.filetype == 'tif':
            y = getGradient(y, baseline)
        else:
            y = y - baseline
        return {'baseline': baseline, 'y': y}

    def polyFit(self, y, object_source, intercept, polyorder, use_marker, marker):
        """Polynomial fitting function with optional baseline markers. """

        x = object_source.frameRange()

        if use_marker:
            # add marker if degree+1 is higher than marker number
            minMarkerNum = polyorder+1      #degree+1
            if len(marker) < minMarkerNum:
                diff = (minMarkerNum-len(marker))
                if diff == 1:
                    self.addMarker()
                else:
                    pos = (len(y)-1)/diff
                    for d in range(diff):
                        self.setMarker(round((d+1)*pos))
            # make least squares with markers
            marker = np.array(marker)
            baseline = fitting(x,marker,y[marker],intercept,polyorder)
        else:
            baseline = fitting(x,x,y,intercept,polyorder)
        if object_source.filetype == 'tif':
            y = getGradient(y, baseline)
        else:
            y = y - baseline
        return {'baseline': baseline, 'y': y}

    ## MARKERS ##

    def findValidMarkerPosition(self, initial_position, min_difference = 4):
        """
        Gets an initial position where a marker should be added. 

        If this initial position is not within the range of min_difference to another marker, it is valid
        and will be returned.
        
        If the initial position is not valid, another valid position with the highest difference to other markers
        will be searched for and returned. If none is found, -1 is returned.
        """

        positions = self.methods['Polynomial Fitting'].getParameters()['marker']

        # check if initial position is valid
        valid = True
        for pos in positions:
            if pos - min_difference < initial_position < pos + min_difference:
                valid = False
                break
        if valid:
            return initial_position

        # initial position is not valid. 
        # copy positions
        positions = copy(positions)

        # append borders if they are not in there yet
        if not 0 in positions:
            positions.append(0)
        input_len = len(self.input['y'])
        if not input_len in positions:
            positions.append(input_len)
        # sort positions
        positions = sorted(positions)
        # find biggest difference
        best_difference, best_difference_position = max([(positions[i+1] - positions[i], positions[i]) for i in range(len(positions)-1)], key=lambda _tuple:_tuple[0])
        # check if biggest difference is valid and return
        if best_difference >= min_difference:
            return best_difference_position + int(best_difference / 2)
        else:
            return -1

    def activateMarkers(self):
        poly = self.methods['Polynomial Fitting']
        bm = poly.getParametersGUI('use_marker')
        am = poly.getParametersGUI('Add Marker')
        poly.setParameters({'use_marker': bm.isChecked()})
        if bm.isChecked():
            self.showMarkers()
            am.show()
            y = self.input['y']
            degree = poly.getParameters()['polyorder']
            already_there = len(poly.getParameters()['marker'])
            diff = degree + 1 - already_there
            if diff == 1:
                self.addMarker()
            elif diff > 1:
                pos = int((len(y)-1) / degree)
                for i in range(0, diff):
                    self.setMarker(pos * i)
        else:
            self.clearMarkers()
            am.hide()
            poly.setParameters({'marker':[]})
            self.markerItems = []
        self.update()

    def clearMarkers(self):
        shown = [mi for mi in self.markerItems if mi in self.liveplot_container.items()]
        for mi in shown:
            self.liveplot_container.removeItem(mi)

    def showMarkers(self):
        curr_pipeline = self.data.getCurrentPipeline()
        if self.getMethod() != self.methods['Polynomial Fitting'] or not self in curr_pipeline.getPipeline():
            return
        marker = self.methods['Polynomial Fitting'].getParameters()['marker']
        invalid_marker_item = 0 < len([marker_ for marker_, marker_item in zip(marker, self.markerItems) if marker_ != int(marker_item.value())])
        if len(self.markerItems) != len(marker) or invalid_marker_item:
            self.clearMarkers()
            for marker_item in self.markerItems:
                try: marker_item.sigPositionChangeFinished.disconnect()
                except: pass
            self.markerItems = []
            for marker_ in marker:
                self.createMarkerGUIObject(marker_)
        not_shown = [mi for mi in self.markerItems if mi not in self.liveplot_container.items()]
        for mi in not_shown:
            self.liveplot_container.addItem(mi)

    def createMarkerGUIObject(self, pos):
        # create, save and add marker item to plot
        mrk = pg.InfiniteLine(pos=pos, pen=pg.mkPen(color=colors.alternative_2), movable=True, bounds=(0,len(self.input['y'])-1))
        self.markerItems.append(mrk)
        self.liveplot_container.addItem(mrk)
        # connect signal and update baseline
        mrk.sigPositionChangeFinished.connect(lambda reg:self.changeMarkerPosition(mrk))
        mrk.mouseClickEvent = lambda ev: self.markerMouseClickEvent(mrk, ev)

    def setMarker(self, pos):
        valid_pos = self.findValidMarkerPosition(pos)
        if valid_pos == -1:
            print('did not find a valid marker position.')
            return
        poly = self.methods['Polynomial Fitting']
        m = poly.getParameters()['marker']
        m.append(valid_pos)
        self.createMarkerGUIObject(valid_pos)

    def markerMouseClickEvent(self, mrk, ev):
        if ev.button() == QtCore.Qt.RightButton:
            
            self.menu = QtGui.QMenu(self)
            
            remove_marker = self.menu.addAction('remove marker')
            remove_marker.triggered.connect(lambda _, marker=mrk: self.removeMarker(mrk))

            self.menu.popup(QtGui.QCursor.pos())

            ev.accept()

    def addMarker(self):
        n = len(self.input['y'])
        midPos = round((n-1)/2)
        self.setMarker(midPos)

    def addMarkerButtonClick(self):
        self.addMarker()
        self.update()

    def removeMarker(self, marker):
        polyorder = self.methods['Polynomial Fitting'].getParameters()['polyorder']
        if len(self.markerItems) <= polyorder+1:
            QtWidgets.QMessageBox.information(self,
                'Remove not possible',
                'Marker can not be removed because the minimum number of markers is already reached. To remove a marker, you can decrease the order of the polynomial.',
                QtWidgets.QMessageBox.Ok)
            return
        index_last_used = self.markerItems.index(marker)
        self.liveplot_container.removeItem(self.markerItems[index_last_used])
        m = self.methods['Polynomial Fitting'].getParameters()['marker']
        del m[index_last_used]
        del self.markerItems[index_last_used]

    def changeMarkerPosition(self, marker):
        index = self.markerItems.index(marker)
        a = self.markerItems[index].value()
        m = self.methods['Polynomial Fitting'].getParameters()['marker']
        m[index] = int(a)
        self.update()

    def clear(self):
        self.clearData()
        self.undisplayPlots()

    def undisplayPlots(self):
        Feature.undisplayPlots(self)
        self.liveplot.clear()
        self.clearMarkers()
