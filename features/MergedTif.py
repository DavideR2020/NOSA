# load Modules

from util.conf import mt_params
from features.Feature import Feature

class MergedTif(Feature):

    def __init__(self, data, parent=None, liveplot=None):
        # Init Feature
        Feature.__init__(self, 'Merge Tif', data, parent, liveplot)

        # data
        self.input = {'object_source': None}
        self.output = {'source': None}

        self.imv = self.liveplot
        self.activateFunc = self.setState

        ## METHODS ##
        self.addMethod('merge', mt_params, self.mergeTif)

        self.initMethodUI()
        self.initParametersUI()

    def initParametersUI(self):
        self.updateParametersUI()

    def setState(self):
        source = self.input['object_source']
        if source is None:
            return
        # if we just unchecked featurebox
        if not self.active and source.merged_tif_active:
            source.merged_tif_active = self.active
            self.data.cell_selection.inputConfiguration()
            self.data.cell_selection.updateROIAll()
        source.merged_tif_active = self.active

    def mergeTif(self, object_source, merge):
        if self.active and object_source._data_merged is None:
            img = object_source.getData()
            merged = img.mean(axis = 0)
            object_source.setMergedData(merged)

        return{'source': object_source}

    def updateLivePlot(self):
        if self.imv.image is not None:
            self.imv.showPlot()