from PyQt5 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from copy import deepcopy

# Feature interface
class Feature(QtWidgets.QWidget):

    def __init__(self, name, data, parent=None, liveplot=None, display_name_label=True):

        if parent is not None and isinstance(parent, QtWidgets.QStackedWidget):
            QtWidgets.QWidget.__init__(self)
            parent.addWidget(self)
        else:
            QtWidgets.QWidget.__init__(self, parent=parent)

        self.hide()
        self.setMinimumWidth(290)

        # name
        self.name = name

        # active
        self.active = False

        # data
        self.data = data
        self.input = {}
        self.output = {}

        # plot
        self.liveplot = liveplot

        # methods
        self.methods = {}
        self.method_label = QtWidgets.QLabel("Method: ")
        self.method_combo = QtWidgets.QComboBox()
        self.connectMethodCombo()
        self.method_layout = QtWidgets.QHBoxLayout()
        self.method_layout.addWidget(self.method_label)
        self.method_layout.addWidget(self.method_combo)
        self.method_layout_widget = QtWidgets.QWidget()
        self.method_layout_widget.setLayout(self.method_layout)

        # layout
        self.layout	= QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setAlignment(QtCore.Qt.AlignTop)

        if display_name_label:
            name_label = QtWidgets.QLabel(self.name)
            name_label.setAlignment(QtCore.Qt.AlignHCenter)
            self.layout.addWidget(name_label)
            font = name_label.font()
            font.setPointSize(font.pointSize() + 8)
            name_label.setFont(font)
            font_metrics = QtGui.QFontMetrics(font)
            name_label.setMaximumHeight(font_metrics.height())

    def connectMethodCombo(self):
        self.method_combo.currentIndexChanged.connect(self.activate)

    def disconnectMethodCombo(self):
        self.method_combo.currentIndexChanged.disconnect()

    # Optional
    def activateFunc(self):
        pass

    def initMethodUI(self):
        self.layout.addWidget(self.method_layout_widget)
        self.disconnectMethodCombo()
        for mname, method in self.methods.items():
            self.method_combo.addItem(mname)
            self.layout.addWidget(method)
        self.method_combo.setCurrentIndex(0)
        self.connectMethodCombo()
        if len(self.methods) < 2:
            self.method_layout_widget.hide()
            self.layout.removeWidget(self.method_layout_widget)

    def initParametersUI(self):
        pass

    # Update UI
    def updateParametersUI(self):
        """Show parameters UI (sliders/checkboxes/...) of the selected feature method and hide parameters GUI of non-selected feature methods."""
        # hide all parameters
        for name in self.methods:
            self.methods[name].hide()
            self.methods[name].hideParametersGUI()
        # show selected method parameters
        method_name = self.method_combo.currentText()
        self.methods[method_name].show()
        self.methods[method_name].showParametersGUI()

    def inputConfiguration(self):
        pass

    # Method
    def addMethod(self, name, parameters, function):
        self.methods[name] = FeatureMethod(self, name, deepcopy(parameters), function)

    def getMethod(self):
        name = self.method_combo.currentText()
        return self.methods[name]

    # Plot
    def updateLiveplot(self):
        pass

    # Clear
    def clear(self):
        """Clear function, that will be executed when deactivating a feature. If there are additional clearing processes like clearng the view, this method can be overwritten."""
        self.clearData()

    def clearData(self):
        """Clear output data in feature"""
        for name in self.output.keys():
            self.output[name] = None

    def undisplayPlots(self):
        """Resets the plots that this features uses."""
        if self.liveplot is not None and hasattr(self.liveplot, 'compare') and self.liveplot.compare.isChecked():
            self.data.plot_manager.resetComparePlots(self.liveplot)

    # Update
    def update(self, *args, updateDependend = True, plot = True, set_source_attributes_callback_kwargs = None, **kargs):
        if self.active:
            method = self.getMethod()
            if method.prevent_update:
                return
            input_dict = {**{k:v for k,v in self.input.items()}, **method.parameters}
            if set_source_attributes_callback_kwargs is not None:
                input_dict['set_source_attributes_callback_kwargs'] = set_source_attributes_callback_kwargs
            out = method.function(**input_dict)
            self.output = out
            # update plot
            if plot:
                self.updateLivePlot()
            # update dependend
            if updateDependend:
                self.data.refreshPipeline(start_with_feature = self, start_after_start_with_feature = True, plot = plot, **kargs)

    # Activate
    def setActive(self, active, **kargs_for_update):
        """Activate the feature."""
        self.active = active
        self.activate(**kargs_for_update)

    def activate(self, **kargs_for_update):
        """Will be executed when the feature is activated."""
        # update ui
        self.updateParametersUI()
        # process custom activation function
        self.activateFunc()
        # update if active
        if self.active:
            self.update(**kargs_for_update)
        # clear and update other features if not checked
        else:
            self.clear()

class FeatureMethod(QtWidgets.QWidget):

    def __init__(self, feature, name, parameters, function):
        '''
        feature:
            Feature.
            the Feature this FeatureMethod belongs to.
        name:
            string.
            the name of this FeatureMethod
        parameters:
            dict.
            the initial parameters of this FeatureMethod
        function:
            function.
            the calculating function of this FeatureMethod
        '''
        QtWidgets.QWidget.__init__(self)

        self.feature = feature
        self.name = name
        self.parameters = deepcopy(parameters)
        self.function = function
        # gui
        self.param_gui = {}

        # Layout
        self.layout	 = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)

        # for preventing an update
        self.prevent_update = False

    def getParameters(self):
        """Returns method parameters as dictionary."""
        return self.parameters

    def setParameters(self, params, prevent_update = False):
        '''
        params:
            dict.
            parameters to set. if the parameters refer the graphical objects, the values of the
                graphical objects are set too. if no change in a parameter has been made, it will
                be ignored.
        prevent_update:
            bool. default is False.
            determines if an update should be prevented.
        '''
        if prevent_update or self is not self.feature.getMethod():
            prevent_update_before = self.feature.getMethod().prevent_update
            self.feature.getMethod().prevent_update = True
        for key, value in params.items():
            # check if we can continue because value did not change
            if key in self.parameters.keys():
                if self.parameters[key] == value:
                    continue
            # check for graphical object
            if key in self.param_gui.keys():
                gui_elem = self.param_gui[key]
                if type(gui_elem) is Slider:
                    # check if absolutes are set and value may be out of range. if so, do not set value!
                    if gui_elem.absolutes_set and (gui_elem.absolute_min * gui_elem.multiplier > value or gui_elem.absolute_max * gui_elem.multiplier < value):
                        continue
                    # check if we have to set minimum of slider
                    if gui_elem.slider.minimum() * gui_elem.multiplier > value:
                        gui_elem.setMinimum(value)
                    # check if we have to set maximum of slider
                    if gui_elem.slider.maximum() * gui_elem.multiplier < value:
                        gui_elem.setMaximum(value)
                    gui_elem.setValue(value)
                elif type(gui_elem) is QtWidgets.QCheckBox:
                    gui_elem.setChecked(value)
                elif type(gui_elem) is list and len(gui_elem) > 0 and type(gui_elem[0]) is QtWidgets.QRadioButton:
                    for gui_sub_elem in gui_elem:
                        gui_sub_elem.setChecked(gui_sub_elem.text() == value)
                elif type(gui_elem) is pg.EllipseROI:
                    pos, size, angle = value
                    gui_elem.setPos(pos)
                    gui_elem.setSize(size)
                    gui_elem.setAngle(angle)
                elif type(gui_elem) is pg.RectROI:
                    pos, size, _ = value
                    gui_elem.setPos(pos)
                    gui_elem.setSize(size)
            # set the data parameter
            if key in self.parameters.keys():
                self.parameters[key] = value
        if prevent_update or self is not self.feature.getMethod():
            self.feature.getMethod().prevent_update = prevent_update_before

    ## GUI ##

    def showParametersGUI(self):
        """Show parameters GUI elements."""
        for p in self.param_gui:
            try:
                self.param_gui[p].show()
            except:
                for elem in self.param_gui[p]:
                    elem.show()

    def hideParametersGUI(self):
        """Hide parameters GUI elements."""
        for p in self.param_gui:
            try:
                self.param_gui[p].hide()
            except:
                for elem in self.param_gui[p]:
                    elem.hide()

    def getParametersGUI(self, param_name):
        """Get GUI element of a given parameter."""
        if param_name not in self.param_gui.keys():
            return None
        return self.param_gui[param_name]

    def initSlider(self, param_name, slider_params, updateFunc=None, releaseFunc=None, label=None):
        """Add Slider for a given parameter."""
        mini, maxi, tik, multiplier = slider_params
        val = round(self.parameters[param_name]/multiplier)
        slider = Slider(param_name, (val,mini,maxi,tik), multiplier, updateFunc, releaseFunc, self, label)
        self.param_gui[param_name] = slider
        self.layout.addWidget(slider)

    def initROI(self, imv, pos, size, angle, pen, updateFunc=None, releaseFunc=None):
        """Add an ROI to an ImageView."""
        roi = pg.EllipseROI(pos, size, angle=angle, pen=pen)
        if updateFunc is not None:
            roi.sigRegionChanged.connect(updateFunc)
        if releaseFunc is not None:
            roi.sigRegionChangeFinished.connect(releaseFunc)
        if updateFunc is None and releaseFunc is None:
            roi = pg.EllipseROI(pos, size, angle=angle, pen=pen, movable = False)
        imv.getView().addItem(roi)
        self.param_gui['roi'] = roi
        return roi

    def initRectROI(self, imv, pos, size, pen, updateFunc=None, releaseFunc=None):
        """Add a rectangular ROI to an ImageView"""
        roi = pg.RectROI(pos, size, pen=pen)
        if updateFunc is not None:
            roi.sigRegionChanged.connect(updateFunc)
        if releaseFunc is not None:
            roi.sigRegionChangeFinished.connect(releaseFunc)
        if updateFunc is None and releaseFunc is None:
            roi = pg.RectROI(pos, size, pen=pen, movable = False)
        imv.getView().addItem(roi)
        self.param_gui['rect_roi'] = roi
        return roi


    def initButton(self, param_name, updateFunc=None):
        """Add Button for a given parameter"""
        btn = QtWidgets.QPushButton(param_name,self)
        btn.clicked.connect(updateFunc)
        self.param_gui[param_name] = btn
        self.layout.addWidget(btn)

    def initCheckbox(self, param_name, updateFunc=None, label=None):
        """Add Checkbox for a given parameter"""
        string = param_name if label is None else label
        cb = QtWidgets.QCheckBox(string,self)
        cb.clicked.connect(updateFunc)
        self.param_gui[param_name] = cb
        self.layout.addWidget(cb)

    def initRadioButtons(self, param_name, btn_names, updateFunc=None):
        """Add number of RadioButtons for a given parameter."""
        buttons = []
        buttonGroup = QtWidgets.QButtonGroup(self)
        initial_checked_index = 0
        if param_name in self.parameters.keys():
            param_value = self.parameters[param_name]
            if param_value in btn_names:
                initial_checked_index = btn_names.index(param_value)
        for index,btn_name in enumerate(btn_names):
            button = QtWidgets.QRadioButton(btn_name, self)
            button.setChecked(index == initial_checked_index)
            self.layout.addWidget(button)
            buttonGroup.addButton(button)
            buttons.append(button)
        buttonGroup.buttonClicked.connect(updateFunc)
        self.param_gui[param_name] = buttons


class Slider(QtWidgets.QWidget):

    def __init__(self, name, settings, multiplier=1, updateFunc=None, releaseFunc=None, parent=None, display_name=None):

        # init QWidget
        QtWidgets.QWidget.__init__(self)

        # input parameters
        self.feature_method = parent
        self.name = name
        if display_name is None:
            self.display_name = name
        else:
            self.display_name = display_name
        self.updateFunc = updateFunc
        self.releaseFunc = releaseFunc
        self.multiplier = multiplier
        self.decimals = len(str(self.multiplier).split('.')[-1]) if multiplier < 1 else 0
        self.f = '.'+str(self.decimals)+'f'
        val, mini, maxi, tik = settings
        self.absolutes_set = False

        # label
        self.label = QtWidgets.QLabel(self)
        self.label.setMinimumHeight(25)

        # slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.slider.setMinimum(mini)
        self.slider.setMaximum(maxi)
        self.slider.setValue(val)
        self.slider.setTickInterval(tik)
        self.slider.setMinimumHeight(20)

        # range
        rangetxt = '('+str(round(mini*multiplier))+','+str(round(maxi*multiplier))+')'
        self.range_btn = QtWidgets.QPushButton(rangetxt, self)
        self.range_btn.setMaximumHeight(25)
        self.range_btn.setMaximumWidth(len(rangetxt)*8)
        self.range_btn.setFlat(True)

        # layout
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.layout.addWidget(self.label, 0, 0)
        self.layout.addWidget(self.range_btn, 0, 1)
        self.layout.addWidget(self.slider, 1, 0, 1, 2)

        # signals
        self.range_btn.clicked.connect(self.setSliderRange)

        if updateFunc is not None:
            self.slider.valueChanged.connect(self.update)
        else:
            self.slider.valueChanged.connect(self.setSliderLabel)
        if releaseFunc is not None:
            self.slider.sliderReleased.connect(self.releaseFunc)

        # init
        self.setSliderLabel()

    def setAbsolutes(self, absolute_min, absolute_max):
        """
        if this is used, the following must be true:
        absolute_minimum <= minimum <= value <= maximum <= absolute_maximum
        """
        self.absolutes_set = True
        self.absolute_min = absolute_min
        self.absolute_max = absolute_max

    def setUpdateFunc(self, updateFunc):
        """Set an update function that will be executed if the slider value is changed."""
        self.updateFunc = updateFunc

    def setSliderLabel(self):
        """Update label with current slider value."""
        val = self.getValue()
        self.label.setText(self.display_name+': '+format(val, self.f))
        if self.feature_method is not None:
            if self.name in self.feature_method.parameters:
                self.feature_method.parameters[self.name] = val

    def update(self):
        """Execute update function and update slider label."""
        self.setSliderLabel()
        self.updateFunc()

    def setSliderRange(self):
        """Let the user change min and max slider values with an QInputDialog."""
        if self.absolutes_set:
            mini,ok1 = QtWidgets.QInputDialog.getDouble(self,'Slider Range',"min", value=self.slider.minimum()*self.multiplier, decimals=3, min=self.absolute_min*self.multiplier, max=(self.absolute_max-1)*self.multiplier)
        else:
            mini,ok1 = QtWidgets.QInputDialog.getDouble(self,'Slider Range',"min", value=self.slider.minimum()*self.multiplier, decimals=3)
        if ok1:
            if self.absolutes_set:
                maxi,ok2 = QtWidgets.QInputDialog.getDouble(self,'Slider Range',"max", value=self.slider.maximum()*self.multiplier, decimals=3, min=max(self.absolute_min+1, mini+1)*self.multiplier, max=self.absolute_max*self.multiplier)
            else:
                maxi,ok2 = QtWidgets.QInputDialog.getDouble(self,'Slider Range',"max", value=self.slider.maximum()*self.multiplier, decimals=3, min=mini+1)
            if ok2:
                self.slider.setMinimum(round(mini/self.multiplier))
                self.slider.setMaximum(round(maxi/self.multiplier))
                
                self.range_btn.setText('('+str(mini)+':'+str(maxi)+')')
                self.range_btn.setMaximumWidth(len(self.range_btn.text())*7)

    def setValue(self,val):
        """Set slider value."""
        self.slider.setValue(round(val/self.multiplier))

    def getValue(self):
        """Get slider value"""
        return self.slider.value()*self.multiplier

    def setMaximum(self,val):
        """Set max slider value. If absolute_max is set, the following must hold: val <= absolute_max"""
        maxi = round(val/self.multiplier)
        mini = self.slider.minimum()
        self.slider.setMaximum(maxi)
        self.range_btn.setText('('+format(mini*self.multiplier, self.f)+','+format(maxi*self.multiplier, self.f)+')')
        self.range_btn.setMaximumWidth(len(self.range_btn.text())*8)

    def setMinimum(self,val):
        """Set min slider value. If absolute_min is set, the following must hold: val >= absolute_min"""
        mini = round(val/self.multiplier)
        maxi = self.slider.maximum()
        self.slider.setMinimum(mini)
        self.range_btn.setText('('+format(mini*self.multiplier, self.f)+','+format(maxi*self.multiplier, self.f)+')')
        self.range_btn.setMaximumWidth(len(self.range_btn.text())*8)
