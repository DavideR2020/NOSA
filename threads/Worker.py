from PyQt5 import QtCore
from threads.WorkerSignals import WorkerSignals

class Worker(QtCore.QRunnable):
    def __init__(self, work, kwargs = {}, callback = None, callback_kwargs = None, max_progress_callback = None, progress_callback = None):
        '''
        work:
            function.
            function to execute.
        kwargs:
            dict. default is {}.
            keyword arguments for the work function.
        callback:
            function, or None. default is None.
            callback to be called when the work function is done.
        callback_kwargs:
            dict, or None. default is None.
            keyword arguments for the callback function.
        max_progress_callback:
            function, or None. default is None.
            function that will be connected to the signal worker_max_progress_signal that will be part of the kwargs dict
                if max_progress_callback is not None. Used to set the max progress of a progressdialog.
        progress_callback:
            function, or None. default is None.
            function that will be connected to the signal worker_progress_signal that will be part of the kwargs dict
                if progress_callback is not None. Used to set the progress of a progressdialog.
        '''
        QtCore.QRunnable.__init__(self)
        self.work = work
        self.kwargs = kwargs
        self.worker_signals = WorkerSignals()
        if max_progress_callback is not None:
            self.worker_signals.max_progress.connect(max_progress_callback)
            self.kwargs['worker_max_progress_signal'] = self.worker_signals.max_progress
        if progress_callback is not None:
            self.worker_signals.progress.connect(progress_callback)
            self.kwargs['worker_progress_signal'] = self.worker_signals.progress
        if callback is not None:
            self.callback_kwargs = callback_kwargs
            self.worker_signals.finished.connect(callback)

    def run(self):
        result = self.work(**self.kwargs)
        if hasattr(self, 'callback_kwargs'):
            self.worker_signals.finished.emit({'result': result, 'callback_kwargs': self.callback_kwargs})