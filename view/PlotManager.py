from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np

from view.Plot import Plot
from util import colors

class PlotManager(QtWidgets.QSplitter):

    def __init__(self, data_manager, cell_selection_imv, parent=None):
        
        QtWidgets.QSplitter.__init__(self, QtCore.Qt.Vertical, parent)

        self.setMinimumSize(600,700)

        self.data_manager = data_manager
        self.data_manager.plot_manager = self
        
        self.roi_views = []
        self.background_roi_view = None

        self.cell_selection = cell_selection_imv
        self.background_subtraction = cell_selection_imv
        self.merged_tif = cell_selection_imv
        self.baseline = pg.PlotCurveItem(name='Baseline', pen=pg.mkPen(color=colors.alternative, width=2))
        self.background_subtraction_plotitem = pg.PlotCurveItem(name='Background Mean', pen=pg.mkPen(color=colors.white))
        self.cell_selection.ui.roiPlot.addItem(self.baseline)
        self.cell_selection.ui.roiPlot.addItem(self.background_subtraction_plotitem)
        self.smoothing = None
        self.processed = Plot('Processed', {'bottom': 'Time (s)'}, self, self)
        self.detection_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.spike_detection = Plot('Spike Detection', {'bottom':'Time (s)'}, self.detection_splitter, self)
        self.burst_detection = Plot('Burst Detection', {'bottom':'Time (s)'}, self.detection_splitter, self)
        self.event_frequency_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.event_shape = Plot('Event Shape', {'bottom':'Time (s)'}, self.event_frequency_splitter, self)
        self.frequency_spectrum = Plot('Power Spectrum', {'bottom':'Frequency (Hz)', 'left': 'PSD'}, self.event_frequency_splitter, self)
        self.cross_correlation_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.spike_cross_correlation = Plot('Spike Cross Correlation', {'bottom': 'Lag (s)', 'left': 'C(t)'}, self.cross_correlation_splitter, self, allowCompare=False)
        self.amplitude_cross_correlation = Plot('Amplitude Cross Correlation', {'bottom': 'Lag(s)', 'left': 'C(t)'}, self.cross_correlation_splitter, self, allowCompare=False)

        self.addWidget(self.processed)
        self.addWidget(self.detection_splitter)
        self.addWidget(self.event_frequency_splitter)
        self.addWidget(self.cross_correlation_splitter)

        self._plots = [
            self.baseline,
            None,
            self.spike_detection,
            self.burst_detection,
            self.event_shape,
            self.frequency_spectrum,
            self.spike_cross_correlation,
            self.amplitude_cross_correlation
        ]

        self._data = [
            None, # processed done manually
            None, # belongs to processed too
            [
                {'name': 'y', 'color': colors.alternative},
                {'name': 'train', 'color': colors.white, 'stepMode': True, 'fillLevel': 0, 'brush': pg.mkBrush(color=colors.white)},
                {'name': 'minimal amplitude', 'color': colors.alternative_2},
                {'name': 'train symbols', 'color': colors.alternative_2, 'pen': None, 'symbol': 't', 'symbolSize': 5, 'symbolPen': pg.mkPen(color=colors.alternative_2), 'symbolBrush': pg.mkBrush(colors.alternative_2)}
            ],
            [
                {'name': 'y', 'color': colors.alternative},
                {'name': 'train', 'color': colors.white, 'stepMode': True},
                {'name': 'minimal base', 'color': colors.alternative_2},
                {'name': 'minimal amplitude', 'color': colors.alternative_2},
                {'name': 'train start symbols', 'color': colors.alternative_2, 'pen': None, 'symbol': 't2', 'symbolSize': 5, 'symbolPen': pg.mkPen(color=colors.alternative_2), 'symbolBrush': pg.mkBrush(colors.alternative_2)},
                {'name': 'train end symbols', 'color': colors.alternative_2, 'pen': None, 'symbol': 't3', 'symbolSize': 5, 'symbolPen': pg.mkPen(color=colors.alternative_2), 'symbolBrush': pg.mkBrush(colors.alternative_2)}
            ],
            [
                {'name': 'shape', 'color': colors.alternative},
                {'name': 'smoothed shape'}
            ],
            [
                {'name': 'PSD'}
            ],
            None, # CC stuff is dynamically
            None # CC stuff dynamically
        ]

        # processed manually 
        self.processed.addData(name='Processed')

        # others, except for CC, in loop
        for index, plot in enumerate(self._plots):
            if self._data[index] is not None:
                for kargs in self._data[index]:
                    plot.addData(**kargs)

        self._plots_to_splitter_contents_indices = [
            (0, -1), # baseline: processed
            (0, -1), # smoothing: processed
            (1, 0), # spike_detection: detection_splitter, left
            (1, 1), # burst_detection: detection_splitter, right
            (2, 0), # event_shape: event_frequency_splitter, left
            (2, 1),  # frequency_spectrum: event_frequency_splitter, right
            (3, 0), # spike cross_correlation: cross_correlation, left
            (3, 1) # amplitude cross_correlation: cross_correlation, right
        ]

        self.showPlotsDefault()
        self.namePlotYAxis(baseline_active = False)

        '''
        the index of the last feature in the Pipeline that belongs to the Processed Plot.
        '''
        processed_features_indices = [
            idx for idx,indices
            in enumerate(self._plots_to_splitter_contents_indices)
            if indices[0] == 0
        ]
        # add one because self._plots_to_splitter_contents_indices ignores BackgroundSubtraction (is at index 0)
        self.max_processed_features_index = max(processed_features_indices) + 1

    def hideBaselinePlot(self):
        self.baseline.hide()

    def showBaselinePlot(self):
        self.baseline.show()

    def getComparisonPlots(self):
        return [self.processed] + [p for p in self._plots if hasattr(p, 'compare')]

    def addAllPlotsForObjectComparison(self):
        for plot in self.getComparisonPlots():
            if plot.compare.isChecked():
                self.addPlotsForObjectComparison(plot)

    def removeAllPlotsForObjectComparison(self):
        for plot in self.getComparisonPlots():
            if plot.compare.isChecked():
                self.removePlotsForObjectComparison(plot)

    def refreshAllPlotsForObjectComparison(self, objects = None):
        for plot in self.getComparisonPlots():
            if plot.compare.isChecked():
                self.refreshPlotsForObjectComparison(plot, objects = objects)

    def addPlotsForObjectComparison(self, plot):
        """
        add data for the calling plot for every object_.
        """

        if plot not in self.getComparisonPlots():
            return

        objects = [object_ for object_ in self.data_manager.objects if object_.active]

        colorTable = colors.getColorTable(len(self.data_manager.objects))

        addData = {
            'compare': True
        }

        if plot is self.processed:
            plotname = 'processed'
        elif plot is self.spike_detection or plot is self.burst_detection:
            plotname = 'train'
            addData['stepMode'] = True
        elif plot is self.event_shape:
            plotname = 'smoothed shape'
        elif plot is self.frequency_spectrum:
            plotname = 'PSD'
        
        for object_ in objects:

            full_list_idx = self.data_manager.objects.index(object_)

            name = object_.name
            pre_name = str(full_list_idx) + '_' + name + ' - '

            addData['color'] = colorTable[full_list_idx]
            addData['name'] = pre_name + plotname

            plot.addData(**addData)

    def refreshPlotsForObjectComparison(self, plot, objects = None):
        '''
        plot:
            plot from getComparisonPlots
            determines the plot whose comparison is being refreshed
        objects:
            array of Objects, or None. default is None.
            determines what Objects shall be refreshed. 
            if None: all Objects that are active shall be refreshed.
        '''
        """
        set data for the calling plot for every object_ that belongs to the current source.
        """

        if plot not in self.getComparisonPlots():
            return

        if objects is None:
            objects = [object_ for object_ in self.data_manager.objects if object_.active]
        
        for object_ in objects:

            if object_.source.filetype == 'abf':
                y_axis_label = object_.source.unit
            else:
                pipeline = object_.pipeline
                if pipeline._baseline.active:
                    y_axis_label = 'dF/F (%)'
                else:
                    y_axis_label = 'Fluorescence Int.'

            seconds_range = object_.source.secondsRange()
            frequency = object_.source.getFrequency()

            name = object_.name
            pre_name = str(self.data_manager.objects.index(object_)) + '_' + name + ' - '

            pipeline = object_.pipeline.getPipeline()
            outputs = [pipeline[idx].output for idx in range(1,len(pipeline))]

            y = None
            
            if plot is self.processed:
                x = seconds_range
                y = object_.processed
                data_name = pre_name + 'processed'
            elif plot is self.spike_detection:
                x = seconds_range
                y = outputs[self._plots.index(self.spike_detection)]['train']
                data_name = pre_name + 'train'
            elif plot is self.burst_detection:
                x = seconds_range
                y = outputs[self._plots.index(self.burst_detection)]['train']
                data_name = pre_name + 'train'
            elif plot is self.event_shape:
                y = outputs[self._plots.index(self.event_shape)]['mean shape smoothed']
                if y is not None:
                    amount = len(y)
                    seconds = amount / frequency
                    x = np.linspace(-seconds/2, seconds/2, amount)
                data_name = pre_name + 'smoothed shape'
                y_axis_label = None
            elif plot is self.frequency_spectrum:
                plot_idx = self._plots.index(self.frequency_spectrum)
                y = outputs[plot_idx]['psd']
                if y is not None:
                    x = outputs[plot_idx]['frequencies']
                data_name = pre_name + 'PSD'
                y_axis_label = None

            if y is not None:
                plot.setData(data_name, x, y, y_axis_label)

        plot.refreshPlots()


    def removePlotsForObjectComparison(self, plot):
        """
        remove all comparing plots for the calling plot
        """
        
        if plot not in self.getComparisonPlots():
            return
        
        plot.removeCompareData()

    def resetCrossCorrelationPlots(self):
        self.spike_cross_correlation.removeAllData()
        self.amplitude_cross_correlation.removeAllData()

        indices = [idx for idx in range(len(self.data_manager.objects)) if self.data_manager.objects[idx].active]
        n = len(indices)
        names = [self.data_manager.objects[i].name for i in indices]

        colorTable = colors.colorMap.getLookupTable(nPts = (n-1)*(n)/2, alpha = False, mode = 'byte')
        clr_counter = 0

        name = []
        refreshPlots = []
        color = []

        for i in range(n-1):
            for j in range(i+1, n):
                refreshPlots.append(clr_counter == (n-1)*(n)/2 - 1)
                name.append('CC {} -- {}'.format(names[i], names[j]))
                color.append(colorTable[clr_counter])
                clr_counter += 1
                
        self.spike_cross_correlation.addData(name = name, refreshPlots = refreshPlots, color = color, stepMode = [True for _ in name])
        
        self.amplitude_cross_correlation.addData(name = name, refreshPlots = refreshPlots, color = color)

    def namePlotYAxis(self, baseline_active = False, filetype_abf = False, source_unit = None):
        if filetype_abf:
            name = source_unit
            self.cell_selection.ui.roiPlot.setLabel('left', text = name)
        else:
            self.cell_selection.ui.roiPlot.setLabel('left', text = 'Fluorescence Int.')
            if baseline_active:
                name = 'dF/F (%)'
            else:
                name = 'Fluorescence Int.'
        for plot in [
            self.processed,
            self.spike_detection,
            self.burst_detection,
            self.event_shape
        ]:
            plot.setLabels({'left': name})

    def showPlotsDefault(self):
        self.setSizes([20000,10000,10000,10000])
        self.detection_splitter.setSizes([10000, 10000])
        self.event_frequency_splitter.setSizes([10000, 10000])
        self.cross_correlation_splitter.setSizes([10000, 10000])

    def refreshPlots(self, feature_index = None):
        """
        Sets the size of the plot that belongs to the feature at feature_index bigger. Can be None to set no plot bigger.
        If only feature belonging to processed are active, processed will be shown bigger.
        
        Sets the size of all other plots to normal.

        Must be called after the feature at feature_index was set active or inactive.
        """

        v_index = -1
        h_index = -1
        if feature_index != None:
            # the first two features, BackgroundSubtraction and MergedTif, do not have a plot
            feature_index -= 2
            # get the indices for the object we want to change the size of
            v_index, h_index = self._plots_to_splitter_contents_indices[feature_index]

        # get the active states of all features, ignoring the first two (BackgroundSubtraction and MergedTif)
        actives = self.data_manager.getCurrentPipeline().getActiveStates()[2:]

        # if the feature at feature_index is not active, we ignore that and just set all plots normal
        if feature_index != None and not actives[feature_index]:
            feature_index = None
            v_index = -1
            h_index = -1

        # # # # # # # # # vertical alignment # # # # # # # # #
        # check if only features belonging to processed are active. default true because if nothing is active, we want to show processed bigger
        processed_only_active = True
        for index, indices in enumerate(self._plots_to_splitter_contents_indices):
            if not indices[0] == 0:
                if actives[index]:
                    processed_only_active = False
        if processed_only_active:
            v_index = 0

        # get numpy array of the sizes
        sizes = np.array(self.sizes())
        # get how many space is available at all
        available = np.sum(sizes)
        # get how many plots there are, add one
        amount = len(sizes) + int(v_index != -1)
        # calculate how many pixels each plot gets
        pixels = 10000
        if amount != 0:
            pixels = int(available / amount)
        # give each plot the amount of pixels
        sizes[:] = pixels
        # give the special plot the special amount of pixels
        if v_index != -1:
            sizes[v_index] += pixels
        # call splitter api
        self.setSizes(sizes)

        # # # # # # # # # horizontal alignment # # # # # # # # #
        for index, splitter in enumerate([self.processed, self.detection_splitter, self.event_frequency_splitter, self.cross_correlation_splitter]):
            # dont align horizontally if we dont work with a splitter
            if not isinstance(splitter, QtWidgets.QSplitter):
                continue
            horizontal_active = [
                actives[idx]
                for idx,(v_index,h_index)
                in enumerate(self._plots_to_splitter_contents_indices)
                if v_index == index
            ]
            amount = np.sum(horizontal_active)
            sizes = np.array(splitter.sizes())
            available = np.sum(sizes)
            if v_index == index:
                amount += 1
            pixels = 10000
            if amount != 0:
                pixels = int(available / amount)
            sizes[:] = 0
            sizes[horizontal_active] = pixels
            if v_index == index:
                sizes[h_index] += pixels
            if np.sum(sizes) == 0:
                sizes = [10000 for _ in sizes]
            splitter.setSizes(sizes)


    def refreshROIView(self, selected_object_index = None):
        """
        Draws a user-visible ROI for every ROI that belongs to the selected source
        into the CellSelection ImageView.

        If a non-image-sequence is selecteda as source, nothing will be displayed.
        
        Also draws a ROI for the Background if it is chosen for the currently selected ROI.
        """
        if selected_object_index is None:
            selected_object_index = self.data_manager.object_selection
        # remove currently shown objects
        for roi_view in [roi_view for roi_view in self.roi_views if roi_view is not None]:
            self.cell_selection.getView().removeItem(roi_view)
        self.roi_views = []
        # remove background roi if shown
        if self.background_roi_view is not None:
            self.cell_selection.getView().removeItem(self.background_roi_view)
            self.background_roi_view = None
        # do not show anything if no roi is selected or selected roi does not belong to image
        if selected_object_index is None or self.data_manager.objects[selected_object_index].source.filetype != 'tif':
            self.data_manager.cell_selection.getUserROI().hide()
            return
        colorTable = colors.getColorTable(len(self.data_manager.objects))
        # iterate every roi
        for i in range(len(self.data_manager.objects)):
            current_is_selected = i == selected_object_index
            current_belongs_to_correct_source = self.data_manager.objects[i].source is self.data_manager.objects[selected_object_index].source
            # only show roi if it belongs to the source that the selected roi belongs to and roi is active (if its inactive but the selected, still show it!)
            if current_belongs_to_correct_source and (self.data_manager.objects[i].active or current_is_selected):
                roi = self.data_manager.objects[i]
                # get color for the roi
                pen = pg.mkPen(color=colorTable[i], width=2)
                if current_is_selected:
                    # if the roi is the currently selected roi: update the position and color of the roi view, without emitting update signals
                    roi_view = self.data_manager.cell_selection.getUserROI()
                    self.data_manager.cell_selection.disconnectUserROISignals()
                    roi_view.setPen(pen)
                    roi_view.setPos(roi.pos)
                    roi_view.setSize(roi.size)
                    roi_view.setAngle(roi.angle)
                    self.data_manager.cell_selection.connectUserROISignals()
                else:
                    # otherwise, if the roi is not the currently selected roi: create an roi view
                    if roi.ellipse_mode:
                        roi_view = pg.EllipseROI(roi.pos, roi.size, angle=roi.angle, pen=pen, movable=False)
                    else:
                        roi_view = pg.RectROI(roi.pos, roi.size, pen=pen, movable=False)
                    self.roi_views.append(roi_view)
                    self.cell_selection.getView().addItem(roi_view)
                    # remove all handles s.t. it can not be edited
                    for h in roi_view.getHandles():
                        roi_view.removeHandle(h)
            else:
                self.roi_views.append(None)

    def refreshComparePlots(self, object_index = None):
        '''
        object_index:
            int or None. Default is None.
            determines what objects plots to refresh. 
            if None: all objects plots are refreshed.
        '''
        objects = self.data_manager.objects if object_index is None else [self.data_manager.objects[object_index]]
        objects = [o for o in objects if o.active]
        if len(objects) > 0:
            self.refreshAllPlotsForObjectComparison(objects = objects)

    def resetComparePlots(self, plot = None):
        '''
        plot:
            plot or None. Default is None.
            determines what plots compareplots shall be reset.
            if None: all plots are reset.
        '''
        if plot is None:
            self.removeAllPlotsForObjectComparison()
            self.addAllPlotsForObjectComparison()
            self.refreshAllPlotsForObjectComparison()
        elif plot in self.getComparisonPlots() and plot.compare.isChecked():
            self.removePlotsForObjectComparison(plot)
            self.addPlotsForObjectComparison(plot)
            self.refreshPlotsForObjectComparison(plot)