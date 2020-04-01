from PyQt5 import QtWidgets, QtCore
import tifffile
import numpy as np

from view.ImageView import ImageView
from threads.Worker import Worker
from view.Plot import removeExportFromContextMenu

class MovementCorrectionDialog(QtWidgets.QDialog):

    """
    Dialog that shows the Movement Correction Feature.

    Dialog consists of:
    - the feature view (two ComboBoxes that control the ImageView content)
    - a control area (save as file, save and cancel button)
    - two ImageViews that show the correction and a comparison
    """

    def __init__(self, parent, data_manager):
        QtWidgets.QDialog.__init__(self, parent, flags = QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        self.setModal(True)
        self.setWindowTitle('Movement Correction')

        self.data_manager = data_manager
        self.last_confirmed_parameter = None

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.feature_view = QtWidgets.QWidget(self)
        self.feature_view.setMinimumWidth(290)

        self.controls = QtWidgets.QWidget(self)
        controls_layout = QtWidgets.QVBoxLayout()
        self.controls.setLayout(controls_layout)
        save_tif_btn = QtWidgets.QPushButton('Save Correction as File', self)
        save_tif_btn.clicked.connect(self.saveAsFile)
        save_btn = QtWidgets.QPushButton('Save Correction in NOSA', self)
        save_btn.clicked.connect(self.save)
        cancel_btn = QtWidgets.QPushButton('Cancel', self)
        cancel_btn.clicked.connect(self.cancel)
        controls_layout.addWidget(save_tif_btn)
        controls_layout.addWidget(save_btn)
        controls_layout.addWidget(cancel_btn)

        layout.addWidget(self.feature_view, 0, 0)
        layout.addWidget(self.controls, 0, 1)
        corrected_label = QtWidgets.QLabel('Corrected')
        corrected_label.setAlignment(QtCore.Qt.AlignHCenter)
        corrected_font = corrected_label.font()
        corrected_font.setPointSize(corrected_font.pointSize() + 8)
        corrected_label.setFont(corrected_font)
        layout.addWidget(corrected_label, 1, 0)
        compare_label = QtWidgets.QLabel('Compare')
        compare_label.setAlignment(QtCore.Qt.AlignHCenter)
        compare_font = compare_label.font()
        compare_font.setPointSize(compare_font.pointSize() + 8)
        compare_label.setFont(compare_font)
        layout.addWidget(compare_label, 1, 1)
        self.corrected_sublabel = QtWidgets.QLabel('')
        self.corrected_sublabel.setAlignment(QtCore.Qt.AlignHCenter)
        layout.addWidget(self.corrected_sublabel, 2, 0)
        self.compare_sublabel = QtWidgets.QLabel('')
        self.compare_sublabel.setAlignment(QtCore.Qt.AlignHCenter)
        layout.addWidget(self.compare_sublabel, 2, 1)

    def timeChanged(self, ind, time, plot):
        """
        Called when the index of an ImageView has changed.

        Sets the index of the other ImageView to the same.
        """
        if self.liveplot.getImageItem().image is None or self.compare_plot.getImageItem().image is None:
            return
        if plot == self.liveplot:
            self.compare_plot.setCurrentIndex(ind)
        else:
            self.liveplot.setCurrentIndex(ind)

    def show(self):
        """
        Closes (rejects) the Dialog (self) and returns if there is no source selected.

        If there is a source selected, the correct MovementCorrection Feature is shown, others are
        hidden. The ImageViews are created and connected with the Feature. The input of the Feature
        is set and Feature is updated such that the ImageViews are set.
        """
        QtWidgets.QDialog.show(self)

        if self.data_manager.source_selection is None:
            self.done(QtWidgets.QDialog.Rejected)
            return
        
        for i in range(len(self.data_manager.sources)):
            mc_ = self.data_manager.movement_corrections[i]
            if i == self.data_manager.source_selection:
                if mc_ is None:
                    self.done(QtWidgets.QDialog.Rejected)
                    return
                self.mc = mc_
                # self.mc.show() is called later! settings must be done first.
            else:
                if mc_ is not None:
                    mc_.hide()

        src = self.data_manager.sources[self.data_manager.source_selection]

        self.liveplot = ImageView(self)
        removeExportFromContextMenu(self.liveplot.scene.contextMenu)
        self.liveplot.setMinimumSize(300,300)
        self.compare_plot = ImageView(self)
        removeExportFromContextMenu(self.compare_plot.scene.contextMenu)
        self.compare_plot.setMinimumSize(300,300)
        self.liveplot.sigTimeChanged.connect(lambda ind, time, plot=self.liveplot: self.timeChanged(ind, time, plot))
        self.compare_plot.sigTimeChanged.connect(lambda ind, time, plot=self.compare_plot: self.timeChanged(ind, time, plot))
        self.layout().addWidget(self.liveplot, 3, 0)
        self.layout().addWidget(self.compare_plot, 3, 1)

        self.mc.liveplot = self.liveplot
        self.mc.compare_plot = self.compare_plot
        self.mc.correction_label = self.corrected_sublabel
        self.mc.compare_label = self.compare_sublabel

        self.mc.input['source'] = src
        self.mc.inputConfiguration()
        # we dont want to calculate the current correction (has not been changed)
        correction_ind = 0
        correction_string = self.mc.methods['Movement Correction'].getParameters()['correction']
        for index, (option) in enumerate(self.mc.options):
            if correction_string == option[0]:
                correction_ind = index
                break
        if correction_ind != 0:
            self.mc.calculated[correction_ind] = src.getData()
        self.mc.show()
        self.mc.update(updateDependend = False)

        # save the parameter the mc has
        self.last_confirmed_parameter = correction_string

    def done(self, r):
        """
        Closes both ImageViews nicely.

        Clears the calculated list and the feature output.
        """
        self.compare_plot.close()
        self.liveplot.close()
        self.layout().removeWidget(self.compare_plot)
        self.layout().removeWidget(self.liveplot)

        self.mc.calculated = [None for _ in self.mc.calculated]
        self.mc.clearData()
        self.mc = None

        QtWidgets.QDialog.done(self, r)
                 
    def save(self):
        """
        Does nothing if self is not visible.

        If self is visible, the corrected data of the currently selected source is set to the output of the 
        MovementCorrection Feature. The Dialog (self) is closed (accepted).
        All Pipelines for the source will be refreshed.
        """
        if self.isVisible():
            selected_source = self.data_manager.sources[self.data_manager.source_selection]
            selected_source.setCorrectedData(self.mc.output['source'])
            self.done(QtWidgets.QDialog.Accepted)
            object_indices_for_this_source = [i for i, o in enumerate(self.data_manager.objects) if o.source is selected_source]
            for index in object_indices_for_this_source:
                # refresh pipeline for all objects belonging to the source. only make cc when refreshing the last pipeline.
                self.data_manager.refreshPipeline(object_index = index, start_with_feature = self.data_manager.cell_selection, ignore_cross_correlation = index != max(object_indices_for_this_source))

    def cancel(self):
        """
        Does nothing if self is not visible.

        If self is visible, resets the parameter of the mc and closes (rejects) the Dialog (self).
        """
        if self.isVisible():
            self.mc.methods['Movement Correction'].parameters['correction'] = self.last_confirmed_parameter
            self.done(QtWidgets.QDialog.Rejected)

    def saveAsFile(self):
        """
        Saves the corrected image sequence as a TIF. User has to choose a directory
        where to save the file.

        Does nothing if there is no correction.
        """
        if self.mc is None or not self.isVisible():
            return

        corrected = self.mc.output['source']

        if corrected is None:
            return

        filename, ok = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Save Corrected as File',
            directory = '',
            filter='(*.tiff)')
        if ok and filename.endswith('.tiff'):
            self.data_manager.progressDialog()
            self.data_manager.progress_dialog.setMinimum(0)
            self.data_manager.progress_dialog.setMaximum(0)

            def saveFileWork():
                tifffile.imwrite(filename, corrected, dtype = np.float32)

            def saveFileCallback():
                self.data_manager.progress_dialog.setMaximum(1)
                self.data_manager.progress_dialog.setValue(1)

            save_file_worker = Worker(
                work = saveFileWork,
                callback = saveFileCallback
            )

            QtCore.QThreadPool.globalInstance().start(save_file_worker)