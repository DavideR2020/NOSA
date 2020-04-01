from PyQt5 import QtCore, QtWidgets, QtGui
from pystackreg import StackReg
from copy import deepcopy
from dipy.align.imwarp import SymmetricDiffeomorphicRegistration
from dipy.align.metrics import CCMetric
import numpy as np

from features.Feature import Feature
from util.conf import mc_params
from threads.Worker import Worker

class MovementCorrection(Feature):

    def __init__(self, data, parent=None, liveplot=None):
        
        Feature.__init__(self, 'Movement Correction', data, parent, liveplot, display_name_label=False)

        self.input = {'source':None}
        self.output = {'source':None}

        self.addMethod('Movement Correction', mc_params, self.movementCorrection)
        
        self.initMethodUI()
        self.initParametersUI()

        self.symmetric_diffeomorphic_option = 'Symmetric Diffeomorphic'

        self.options = [
            ('None [original image]', None),
            (self.symmetric_diffeomorphic_option, None),
            ('Translation', StackReg.TRANSLATION),
            ('Rigid Body', StackReg.RIGID_BODY),
            ('Scaled Rotation', StackReg.SCALED_ROTATION),
            ('Affine', StackReg.AFFINE)
        ]

        self.calculated = []

        compare_layout = QtWidgets.QGridLayout()
        compare_layout.setSpacing(0)
        compare_layout.setMargin(0)
        compare_layout_widget = QtWidgets.QWidget()
        self.layout.addWidget(compare_layout_widget)
        compare_layout_widget.setLayout(compare_layout)
        compare_layout.addWidget(QtWidgets.QLabel('Correction: '), 0, 0)
        compare_layout.addWidget(QtWidgets.QLabel('Compare to: '), 1, 0)
        self.correction_combobox = QtWidgets.QComboBox()
        compare_layout.addWidget(self.correction_combobox, 0, 1)
        self.compare_combobox = QtWidgets.QComboBox()
        compare_layout.addWidget(self.compare_combobox, 1, 1)

        for type_, _ in self.options:
            self.correction_combobox.addItem(type_)
            self.compare_combobox.addItem(type_)
            self.calculated.append(None)

        self._connectComboboxes()

    def show(self):
        Feature.show(self)
        self.compare_combobox.setCurrentIndex(0)
        self.correction_combobox.setCurrentText(self.methods['Movement Correction'].getParameters()['correction'])

    def _connectComboboxes(self):
        self.correction_combobox.currentIndexChanged.connect(self.correctionComboboxChanged)
        self.compare_combobox.currentIndexChanged.connect(lambda: self.update(updateDependend=False))

    def _disconnectComboboxes(self):
        self.correction_combobox.currentIndexChanged.disconnect()
        self.compare_combobox.currentIndexChanged.disconnect()

    def inputConfiguration(self):
        self.calculated = [None for _ in self.calculated]

    def correctionComboboxChanged(self, index):
        distortion, _ = self.options[index]
        self.methods['Movement Correction'].setParameters({'correction': distortion})
        self.update(updateDependend=False)

    def pystackreg_work(self, uncorrected, option, worker_progress_signal, worker_max_progress_signal):
        self.end_set = False
        def progress_callback_pystackreg(current_iteration, end_iteration):
            if not self.end_set:
                worker_max_progress_signal.emit(end_iteration)
                self.end_set = True
            worker_progress_signal.emit(current_iteration)
        sr = StackReg(option)
        corrected = sr.register_transform_stack(uncorrected, reference='first', progress_callback = progress_callback_pystackreg)
        return {'corrected': corrected}

    def dipy_work(self, uncorrected, worker_progress_signal):
        radius = 4
        sigma_diff = 3.0
        metric = CCMetric(2, sigma_diff, radius)
        level_iters = [25]
        sdr = SymmetricDiffeomorphicRegistration(metric, level_iters)
        corrected = np.zeros_like(uncorrected)
        corrected[0] = uncorrected[0]
        for i in range(1, len(uncorrected)):
            mapping = sdr.optimize(corrected[0], uncorrected[i])
            corrected[i] = mapping.transform(uncorrected[i])
            worker_progress_signal.emit(i)
        return {'corrected': corrected}

    def progress_callback(self, progress):
        self.data.progress_dialog.setValue(progress)

    def max_progress_callback(self, max_progress):
        self.data.progress_dialog.setMaximum(max_progress)

    def movementCorrection(self, source, correction, set_source_attributes_callback_kwargs = None):

        # check if we have to calculate what stands in the correction combobox
        correction_ind = self.correction_combobox.currentIndex()
        calculate_compare = False
        if self.calculated[correction_ind] is not None or correction_ind == 0:
            # if we do not have to calculate for the correction combobox, check for the compare combobox:
            compare_ind = self.compare_combobox.currentIndex()
            calculate_compare = True
            if self.calculated[compare_ind] is not None or compare_ind == 0 or not self.isVisible():
                # we already calculated everything. make callback if wanted
                if set_source_attributes_callback_kwargs is not None:
                    self.data.setSourceAttributesCallback(set_source_attributes_callback_kwargs = set_source_attributes_callback_kwargs)
                # return correctly
                if correction_ind == 0:
                    return {'source': None}
                else:
                    return {'source': self.calculated[correction_ind]}

        # we have to calculate something. find out what to calculate:
        ind = correction_ind if not calculate_compare else compare_ind

        # start progress dialog
        self.data.progressDialog()
        self.data.progress_dialog.setMinimum(0)
        self.data.progress_dialog.setMaximum(0)

        # copy the original data
        uncorrected = deepcopy(source.getOriginalData())

        # passing the callback kwargs
        callback_kwargs = {
            'set_source_attributes_callback_kwargs': set_source_attributes_callback_kwargs,
            'calculate_compare': calculate_compare,
            'calculate_ind': ind
        }

        options = self.options[ind]

        # create thread
        if options[0] == self.symmetric_diffeomorphic_option:
            mc_worker = Worker(work = self.dipy_work,
                kwargs = {'uncorrected': uncorrected},
                callback = self.mc_work_callback,
                callback_kwargs = callback_kwargs,
                progress_callback = self.progress_callback)
            self.data.progress_dialog.setMaximum(len(uncorrected) - 1)
        else:
            mc_worker = Worker(work = self.pystackreg_work,
                kwargs = {'uncorrected': uncorrected, 'option': options[1]},
                callback = self.mc_work_callback,
                callback_kwargs = callback_kwargs,
                max_progress_callback = self.max_progress_callback,
                progress_callback = self.progress_callback)
        
        # start thread
        QtCore.QThreadPool.globalInstance().start(mc_worker)

        return {'source': None}

    def mc_work_callback(self, result):
        self.data.progress_dialog.setMaximum(1)
        self.data.progress_dialog.setValue(1)

        kwargs = result['callback_kwargs']

        # if correction was calculated, we set the output
        if not kwargs['calculate_compare']:
            self.output['source'] = result['result']['corrected']

        self.calculated[kwargs['calculate_ind']] = result['result']['corrected']
        
        self.updateLivePlot()

        if kwargs['set_source_attributes_callback_kwargs'] is not None:
            self.data.setSourceAttributesCallback(set_source_attributes_callback_kwargs = kwargs['set_source_attributes_callback_kwargs'])

    def updateLivePlot(self):
        in_ = self.input['source']
        
        if in_ is None or not self.isVisible():
            return

        correction_ind = self.correction_combobox.currentIndex()
        compare_ind = self.compare_combobox.currentIndex()

        if correction_ind == 0:
            self.liveplot.setImage(in_.getOriginalData(), xvals = in_.frameRange())
        elif self.calculated[correction_ind] is None:
            self.liveplot.clear()
        else:
            self.liveplot.setImage(self.calculated[correction_ind], xvals = in_.frameRange())

        if compare_ind == 0:
            self.compare_plot.setImage(in_.getOriginalData(), xvals = in_.frameRange())
        elif self.calculated[compare_ind] is None:
            self.compare_plot.clear()
        else:
            self.compare_plot.setImage(self.calculated[compare_ind], xvals = in_.frameRange())

        if self.correction_label is not None:
            self.correction_label.setText(self.options[correction_ind][0])
        if self.compare_label is not None:
            self.compare_label.setText(self.options[compare_ind][0])

