from PyQt5 import QtCore, QtWidgets
import quantities as pq
import numpy as np
import pyabf

from threads.Worker import Worker
from view.ABFLoaderDialog import ABFLoaderDialog
from model.Source import Source

class ABFLoader():

    def __init__(self, data_manager, filepath):
        """
        Starts the ProgressDialog.

        Starts a Worker that executes initial work and calls a callback that handles the result afterwards.
        """
        data_manager.progressDialog()
        data_manager.progress_dialog.setMinimum(0)
        data_manager.progress_dialog.setMaximum(0)
        
        def initialWork(filepath):
            """
            Reads the blocks and the sampling rate.
            """
            abf = pyabf.ABF(filepath)
            return {'abf': abf,  'filepath': filepath}
        
        def initialWorkCallback(result_dict):
            """
            Stops the ProgressDialog.

            Asks the user which signals to import.

            Creates the data objects if there are signals chosen.
            """
            result = result_dict['result']
            abf = result['abf']
            data_manager.progress_dialog.setMaximum(1)
            data_manager.progress_dialog.setValue(1)

            abf_loader_dialog = ABFLoaderDialog(data_manager.source_manager, abf)
            ok = abf_loader_dialog.exec()

            if ok != QtWidgets.QDialog.Accepted:
                return

            data, number_displayed_options = abf_loader_dialog.getSelectedData()
            amount = len(data)

            if amount == 0:
                return

            filepath = result['filepath']
            name = filepath.split('/')[-1].split('.')[0]
            freq = abf.dataRate
            for  d in data:
                data_ = d['data']

                data_manager.sources.append(
                    Source(
                        filetype = 'abf',
                        name = name if number_displayed_options == 1 else '{} ({})'.format(name, d['tabledata'][0]),
                        original_frequency = freq,
                        start = 0,
                        end = len(data_),
                        offset = 0.0,
                        _data = data_,
                        short_name = data_manager._source_name,
                        unit = d['tabledata'][5]
                    )
                )

                data_manager.movement_corrections.append(None)
                data_manager.finishLoadSource()

        initial_worker = Worker(
            work = initialWork,
            kwargs = {'filepath': filepath},
            callback = initialWorkCallback
        )
        
        QtCore.QThreadPool.globalInstance().start(initial_worker)
        