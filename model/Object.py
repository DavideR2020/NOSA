from dataclasses import dataclass, field
import numpy as np

from model.Pipeline import Pipeline
from model.Source import Source

@dataclass
class Object():

    name: str 
    source: Source
    active: bool = True
    cell_mean: np.ndarray = None
    cell: np.ndarray = None
    processed: np.ndarray = None
    raw: np.ndarray = None
    pos: tuple = None
    angle: float = None
    size: tuple = None
    invert: bool = False
    ellipse_mode: bool = False
    pipeline: Pipeline = field(default_factory = Pipeline)

    def __eq__(self, other):
        return self is other