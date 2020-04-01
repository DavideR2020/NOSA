from dataclasses import dataclass
import numpy as np

from features.AdjustFrequency import AdjustFrequency

@dataclass
class Source():
    filetype: str = None
    name: str = 'unknown'
    adjusted_frequency: float = 250.0
    adjust_frequency_active: bool = False
    adjust_frequency_method: int = 0
    original_frequency: float = 250.0
    start: int = None
    end: int = None
    offset: float = None
    _data: np.ndarray = None
    _data_corrected: np.ndarray = None
    unit: str = ''
    # for naming purposes
    object_number: int = 1
    short_name: int = None

    def __eq__(self, other):
        return self is other

    def frameRange(self):
        return np.arange(self.start, self.end)

    def getFrequency(self):
        return self.adjusted_frequency if self.adjust_frequency_active else self.original_frequency

    def secondsRange(self):
        freq = self.getFrequency()
        factor = freq / self.original_frequency
        
        return (self.offset
            + np.linspace(
                self.start/self.original_frequency,
                self.end/self.original_frequency - 1 / freq,
                num=round(factor * (self.end-self.start)),
                endpoint=True
            ))

    def getData(self):
        if self._data_corrected is not None:
            return self._data_corrected
        else:
            return self._data[self.start:self.end]

    def getOriginalData(self):
        return self._data[self.start:self.end]

    def getMaxEndFrame(self):
        return len(self._data)

    def setCorrectedData(self, corrected_data):
        self._data_corrected = corrected_data