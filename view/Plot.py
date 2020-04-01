from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np

from util import colors

def removeExportFromContextMenu(contextMenu):
    contextMenuLen = len(contextMenu)
    if contextMenuLen > 0:
        for i in range(contextMenuLen):
            action = contextMenu[i]
            if 'Export...' == action.text():
                contextMenu.remove(action)
                break


class Plot(pg.GraphicsView):

    def __init__(self, title, labels, parent, plot_manager, allowCompare=True):
        """
        plot_manager can be None when allowCompare is False.
        """
        pg.GraphicsView.__init__(self, parent)

        removeExportFromContextMenu(self.sceneObj.contextMenu)

        self.setMinimumSize(300,150)
        self.graph_layout = pg.GraphicsLayout()
        self.setCentralItem(self.graph_layout)

        self.single_plot = pg.PlotItem(name=title, labels=dict(labels), title=title)
        self.single_plot.showGrid(x=True, y=True)
        self.graph_layout.addItem(self.single_plot)
        
        self.data = []
        self.labels = labels
        self.left_labels = []
        self.allowCompare = allowCompare
        self.plot_manager = plot_manager
        
        # legend btn
        self.btn = QtWidgets.QPushButton(self)
        self.btn.setMaximumSize(25,25)
        self.btn.setIcon(self.btn.style().standardIcon(QtGui.QStyle.SP_TitleBarUnshadeButton))
        self.btn.setCheckable(True)
        self.btn.clicked.connect(self.showLegend)
        self.btn.setStyleSheet("background-color: rgb(100, 100, 100);")
        
        # legend table
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setRowCount(0)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.move(0,25)
        self.table.hide()
        self.table.setStyleSheet("background-color: rgb(0, 0, 0);")

        # adding menu action for comparing objects
        if self.allowCompare:
            self.compare = QtWidgets.QCheckBox('compare objects', self)
            self.compare.setChecked(False)
            self.compare.stateChanged.connect(self.compareChanged)
            self.compare.move(30,0)
            self.compare.setStyleSheet('background-color:black;')

            self.single_compare = QtWidgets.QCheckBox('one plot', self)
            self.single_compare.setChecked(True)
            self.single_compare.stateChanged.connect(self.refreshPlots)
            self.single_compare.move(self.compare.pos().x()+self.compare.width()+10, 0)
            self.single_compare.setStyleSheet('background-color:black;')
            self.single_compare.hide()

    def setLabels(self, labels):
        self.labels.update(labels)
        self.refreshSinglePlotYAxisName()

    def getMultiLabels(self):
        return {k: v for k, v in self.labels.items() if k != 'bottom'}

    def addData(self, color=colors.white, compare=False, refreshPlots = True, **kargs):
        name = kargs['name']
        if not isinstance(name, list):
            color = [color]
            compare = [compare]
            refreshPlots = [refreshPlots]
            for key,value in kargs.items():
                kargs[key] = [value]
        else:
            if not isinstance(color, list):
                color = [color for _ in name]
            if not isinstance(compare, list):
                compare = [compare for _ in name]
            if not isinstance(refreshPlots, list):
                refreshPlots = [refreshPlots for _ in name]

        refreshPlots = any(refreshPlots)
        
        multi_labels = self.getMultiLabels()

        left_label = None
        if 'left' in multi_labels.keys():
            left_label = multi_labels['left']

        for idx, color_ in enumerate(color):
            self.left_labels.append(left_label)
            compare_ = compare[idx]
            kargs_ = {}
            for key,value in kargs.items():
                kargs_[key] = value[idx]
            
            if not 'pen' in kargs_.keys():
                kargs_['pen'] = pg.mkPen(color_)

            n = len(self.data)
            single_plot_data_item = self.single_plot.plot(**kargs_)
            multi_plot_data_item = None
            multi_plot_item = None
            if compare_:
                multi_plot_item = pg.PlotItem(name=kargs_['name'], labels=multi_labels)
                multi_plot_data_item = multi_plot_item.plot(**kargs_)
            table_data = {
                'color': color_,
                'compare': compare_,
                'single_plot_data_item': single_plot_data_item,
                'multi_plot_data_item': multi_plot_data_item,
                'multi_plot_item': multi_plot_item
            }
            self.data.append(table_data)
            self.table.setRowCount(n+1)
            self.addItemToTable(n)
        self.refreshSinglePlotYAxisName()
        if refreshPlots:
            self.refreshPlots()
                
    def setData(self, name, x, y, y_axis_label = None):
        for idx,d in enumerate(self.data):
            single_plot_data_item = d['single_plot_data_item']
            if single_plot_data_item.name() == name:
                y_axis_label_change = False
                if self.left_labels[idx] != y_axis_label:
                    self.left_labels[idx] = y_axis_label
                    y_axis_label_change = True
                if d['compare'] and y_axis_label is not None:
                    d['multi_plot_item'].setLabel('left', text = y_axis_label)
                    if y_axis_label_change:
                        self.refreshSinglePlotYAxisName()
                if x is None or len(x) == 0:
                    self.clearPlotDataItem(single_plot_data_item)
                    if d['compare']:
                        self.clearPlotDataItem(d['multi_plot_data_item'])
                else:
                    single_plot_data_item.setData(x, y)
                    if d['compare']:
                        d['multi_plot_data_item'].setData(x, y)
                break

    def clearPlotDataItem(self, plot_data_item):
        """
        PlotDataItem where 'stepMode' is True will throw an exception when .clear() is called. This is
        why we need a separate function for this.

        Issue described: https://github.com/pyqtgraph/pyqtgraph/issues/605
        Fix: https://github.com/pyqtgraph/pyqtgraph/pull/417
        """
        plot_data_item.xData = None
        plot_data_item.yData = None
        plot_data_item.xDisp = None
        plot_data_item.yDisp = None
        plot_data_item.curve.clear()
        plot_data_item.scatter.clear()

    def removeAllData(self):
        names = [d['single_plot_data_item'].name() for d in self.data]
        self.removeData(names)

    def removeData(self, names):
        """
        removes the plots according to data_names. To remove all data, use removeAllData.
        """
        change = False
        for name in names:
            for idx, d in enumerate(self.data):
                single_plot_data_item = d['single_plot_data_item']
                if single_plot_data_item.name() == name:
                    self.single_plot.removeItem(single_plot_data_item)
                    del self.data[idx]
                    del self.left_labels[idx]
                    change = True
                    break

        # refresh table view
        if change:
            self.table.setRowCount(0)
            self.table.setRowCount(len(self.data))
            for i in range(len(self.data)):
                self.addItemToTable(i)
            self.refreshSinglePlotYAxisName()

        self.refreshPlots()

    def refreshSinglePlotYAxisName(self):
        if self.allowCompare and self.compare.isChecked():
            left_labels = set([left_label for left_label in self.left_labels if left_label is not None])
            y_axis_name = ''
            for idx, left_label in enumerate(left_labels):
                y_axis_name += left_label
                if idx != len(left_labels) - 1:
                    y_axis_name += ' // '
            self.single_plot.setLabel('left', text = y_axis_name)
        else:
            if 'left' in self.labels.keys():
                self.single_plot.setLabel('left', text = self.labels['left'])

    def showLegend(self):
        """Show table with data/plot items. the user can select which data/plot should be displayed."""
        if self.btn.isChecked():
            self.table.show()
            self.btn.setIcon(self.btn.style().standardIcon(QtGui.QStyle.SP_TitleBarShadeButton))
        else:
            self.table.hide()
            self.btn.setIcon(self.btn.style().standardIcon(QtGui.QStyle.SP_TitleBarUnshadeButton))
            
    def addItemToTable(self, index):
        d = self.data[index]
        data_name = d['single_plot_data_item'].name()
        color = d['color']
        name = QtWidgets.QTableWidgetItem(data_name)
        self.table.setItem(index, 1, name)
        cb = QtWidgets.QCheckBox(self.table)
        cb.setChecked(True)
        cb.stateChanged.connect(self.refreshPlots)
        self.table.setCellWidget(index, 0, cb)
        self.table.item(index, 1).setForeground(QtGui.QColor(color[0], color[1], color[2]))

    def shouldMultiBeDisplayed(self, data, index):
        compare_and_checked = data['compare'] and self.table.cellWidget(index, 0).isChecked()
        has_data = data['single_plot_data_item'].xData is not None and len(data['single_plot_data_item'].xData) > 0
        return compare_and_checked and has_data

    def refreshMultiComparePlotStuff(self):
        multi_plot_items = []
        x_mins = []
        x_maxs = []

        # gather all the plotitems we want to display
        for idx, d in enumerate(self.data):
            if self.shouldMultiBeDisplayed(d, idx):
                multi_plot_items.append(d['multi_plot_item'])
                x_data = d['single_plot_data_item'].xData
                if x_data is not None:
                    x_mins.append(x_data[0])
                    x_maxs.append(x_data[-1])

        # check if there is data inside the plotitems to get a custom x range
        custom_x_range = len(x_mins) > 0
        if custom_x_range:
            x_min = min(x_mins)
            x_max = max(x_maxs)
            x_range = x_max - x_min
            padding = 0.04 * x_range
            x_min -= padding
            x_max += padding
            x_range = x_max - x_min
        
        n = len(multi_plot_items)

        # iterate all the plot items
        for idx, item in enumerate(multi_plot_items):
            # exception for last plot item: show axis and give the axis a label
            if idx == n-1:
                item.showAxis('bottom', True)
                item.setLabel('bottom', text = self.labels['bottom'])
            else:
                item.showAxis('bottom', False)

            # if we have a custom x range, we force the plots to display this and nothing else
            if custom_x_range:
                item.disableAutoRange(pg.ViewBox.XAxis)
                item.setXRange(x_min, x_max, padding=0.0)
                item.setLimits(xMin = x_min, xMax = x_max, minXRange = x_range, maxXRange = x_range)

    def removeCompareData(self):
        names = [d['single_plot_data_item'].name() for d in self.data if d['compare']]
        self.removeData(names)

    def compareChanged(self):
        if self.compare.isChecked():
            self.plot_manager.addPlotsForObjectComparison(self)
            self.plot_manager.refreshPlotsForObjectComparison(self)
            self.single_compare.show()
        else:
            self.plot_manager.removePlotsForObjectComparison(self)
            self.single_compare.hide()
        self.refreshPlots()

    def refreshPlots(self):
        # add the single plot to the layout such that we can clear it successfully afterward.
        # this is needed because clearing it will not work properly if it is not part of a layout.
        self.graph_layout.addItem(self.single_plot)
        self.single_plot.clear()
        # clear the graph layout.
        self.graph_layout.clear()
        if not self.allowCompare or not self.compare.isChecked():
            # case 1. plot is not used for comparing.
            # add single plot to the main layout
            self.graph_layout.addItem(self.single_plot)
            # add plots to the single plot.
            for idx, d in enumerate(self.data):
                if self.table.cellWidget(idx, 0).isChecked():
                    self.single_plot.addItem(d['single_plot_data_item'])
        elif self.single_compare.isChecked():
            # case 2. plot is used for comparing. mode: single plot.
            # add single plot to the main layout
            self.graph_layout.addItem(self.single_plot)
            # add plots to the single plot that are used for comparing.
            for idx, d in enumerate(self.data):
                if d['compare'] and self.table.cellWidget(idx, 0).isChecked():
                    self.single_plot.addItem(d['single_plot_data_item'])
        else:
            # case 3. plot is used for comparing. mode: multi plot.
            # add all the multi plot items to the main layout.
            for idx, d in enumerate(self.data):
                if self.shouldMultiBeDisplayed(d, idx):
                    self.graph_layout.addItem(d['multi_plot_item'], idx, 0)
            self.refreshMultiComparePlotStuff()
    