import tifffile
from PyQt5 import QtWidgets, QtCore
import numpy as np

from threads.Worker import Worker
from model.Source import Source
from features.MovementCorrection import MovementCorrection

class TIFLoader():

    def __init__(self, data_manager, filepath):
        """
        Starts the ProgressDialog.
        
        Starts a Worker that loads the file and calls a callback that handles the result afterwards.
        """

        data_manager.progressDialog()
        data_manager.progress_dialog.setMinimum(0)
        data_manager.progress_dialog.setMaximum(0)

        def work(filepath, worker_max_progress_signal, worker_progress_signal):
            with tifffile.TiffFile(filepath) as tif:
                frame_amount = len(tif.pages)
                worker_max_progress_signal.emit(frame_amount)
                first_page = tif.asarray(key=0)
                data = np.zeros((frame_amount, first_page.shape[0], first_page.shape[1]), first_page.dtype)
                step = int(frame_amount / 100)
                if (step == 0): #if frame_amount < 100, step will be 0. to avoid this, we set step=1.
                    step = 1
                frame_counter = 0
                while frame_counter + step < frame_amount:
                    data[frame_counter : frame_counter + step] = tif.asarray(key=slice(frame_counter, frame_counter + step, 1))
                    frame_counter += step
                    worker_progress_signal.emit(frame_counter)
                data[frame_counter : frame_amount] = tif.asarray(key=slice(frame_counter, frame_amount, 1))
                data = np.swapaxes(data, 1, 2)
                worker_progress_signal.emit(frame_amount)
                return {'data': data, 'filepath': filepath}

        def max_progress_callback(max_progress):
            data_manager.progress_dialog.setMaximum(max_progress)

        def progress_callback(progress):
            data_manager.progress_dialog.setValue(progress)

        def callback(result):
            """
            Asks the user for the image sequence frequency and creates the
            data object afterwards.
            """
            freq, ok = QtWidgets.QInputDialog.getDouble(
                data_manager.source_manager,
                'Frequency',
                'Please set the recording frequency of the image sequence (in Hz)',
                value = 250.0,
                min = 0.001,
                decimals = 3
            )
            if ok:
                data = result['result']['data']
                filepath = result['result']['filepath']
                name = filepath.split('/')[-1].split('.')[0]
                data_manager.sources.append(
                    Source(
                        filetype = 'tif',
                        name = name,
                        original_frequency = freq,
                        start = 0,
                        end = len(data),
                        offset = 0.0,
                        _data = data,
                        short_name = data_manager._source_name,
                        unit = 'Fluorescence Int.'))
                movement_correction = MovementCorrection(
                    data_manager,
                    data_manager.source_manager.movement_correction.feature_view,
                    liveplot = None)
                movement_correction.active = True
                data_manager.movement_corrections.append(movement_correction)
                data_manager.finishLoadSource()

        worker = Worker(
            work = work,
            kwargs = {'filepath': filepath},
            callback = callback,
            max_progress_callback = max_progress_callback,
            progress_callback = progress_callback
        )
        
        QtCore.QThreadPool.globalInstance().start(worker)