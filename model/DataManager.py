import time
from PyQt5 import QtWidgets, QtCore
import numpy as np
from copy import deepcopy

from features.AdjustFrequency import AdjustFrequency
from features.EventDetection import SpikeDetection, BurstDetection
from model.Object import Object
from util.conf import af_params, cs_roi_params

class DataManager():

    parent = None

    sources = []
    movement_corrections = []
    objects = []

    source_selection = None
    object_selection = None

    cell_selection = None

    source_manager = None
    object_manager = None
    plot_manager = None
    pipeline_manager = None

    _TIME_NEEDED_TO_SHOW_PROGRESSDIALOG = 0.75
    _time_needed_to_remove_source = 0
    _time_needed_to_add_object = 0
    _time_needed_to_remove_object = 0

    _source_name = 1

    def __init__(self, parent):
        self.parent = parent

    def finishLoadSource(self):
        # set the adjusted frequency setting for the source
        self.setSourceAttributes(len(self.sources)-1, {'frequency': af_params['adjusted_frequency']})
        # increase for naming purposes
        self._source_name += 1
        # refresh view
        self.source_manager.refreshView()
        # add object for the newly created source
        self.addObject(source_index = len(self.sources)-1)

    def selectSource(self, selection = None):
        '''
        selection:
            int or None. default is none. 
            determines what source shall be selected.
            if None: selects the last added source.
        '''
        # if no selection is specified and its not possible, return. otherwise, select an appropriate
        # source for the selected object
        if selection is None:
            if len(self.sources) == 0:
                self.source_selection = None
                # refresh cell selection view such that nothing will be shown
                self.refreshCellSelectionView()
                # may call selectobject to correctly set object_selection
                if self.object_selection is not None:
                    self.selectObject()
                return
            else:
                selection = len(self.sources) - 1

        # set the change
        self.source_selection = selection

        # disconnect sourcemanager signals and set visible row selection
        self.source_manager.tableItemSelectionChangedDisconnect()
        self.source_manager.table.selectRow(selection)
        self.source_manager.tableItemSelectionChangedConnect()

        # set sourcemanager movementcorrection button
        self.source_manager.mc_btn.setEnabled(self.sources[self.source_selection].filetype == 'tif')

        # select a correct object for the new selected source if the current object does not belong to this source
        if self.object_selection is not None and self.objects[self.object_selection].source is not self.sources[selection]:
            object_indices_for_this_source = [i for i, o in enumerate(self.objects) if o.source is self.sources[self.source_selection]]
            self.selectObject(max(object_indices_for_this_source))

    def removeSource(self, remove_source_index = None, show_progress = True):
        '''
        remove_source_index:
            int or None. default is None.
            determines what source shall be removed. 
            if None, the selected source will be removed.
        show_progress:
            bool. default is True.
            determines if a progressdialog may be shown. if True, other things must hold for a progressdialog to be shown.
        '''
    
        # if no source is specified: use selected source if possible. if not, return.
        if remove_source_index is None:
            if self.source_selection is None:
                return
            else:
                remove_source_index = self.source_selection

        # measure time for progressdialog
        start_time = time.process_time()

        # determine if progressdialog shall be shown
        update_progress = show_progress and (self._time_needed_to_remove_source >= self._TIME_NEEDED_TO_SHOW_PROGRESSDIALOG or self._time_needed_to_remove_source == 0 and len(self.objects) >= 10)

        # show progressdialog
        if update_progress:
            self.progressDialog()
            self.progress_dialog.setMaximum(3)

        # we need the reference on the source to remove for a bit longer
        removed_source = self.sources[remove_source_index]

        # remove the source from the list
        self.sources = [source for index, source in enumerate(self.sources) if index != remove_source_index]
        
        # remove the movementcorrection and adjustfrequency from the lists
        self.movement_corrections = [mc for index, mc in enumerate(self.movement_corrections) if index != remove_source_index]

        if update_progress:
            self.progress_dialog.setValue(1)

        # check what objects belong to the removed source and shall be removed
        object_indices = sorted([i for i, o in enumerate(self.objects) if o.source is removed_source])[::-1]

        # check if we have to undisplay backgroundsubtraction and baseline of pipeline of current object
        if self.object_selection in object_indices:
            background_subtraction = self.getCurrentPipeline()._background_subtraction
            if background_subtraction.active:
                background_subtraction.undisplayPlots()
            baseline = self.getCurrentPipeline()._baseline
            if baseline.active:
                baseline.undisplayPlots()

        object_indices_len = len(object_indices)
        for index, object_index in enumerate(object_indices):
            # remove every of these objects. dont check if source shall be removed and only last iteration shall refresh objectselection,
            # views and plots. no progress shall be shown. prevent check of undisplay of backgroundsubtraction of pipeline of current object
            # because we do it here already
            self.removeObject(
                object_index,
                remove_source = False,
                refresh = index == object_indices_len - 1,
                show_progress = False,
                object_selection_after = -1,
                prevent_feature_undisplay = True)

        if update_progress:
            self.progress_dialog.setValue(2)

        # refresh the sourcemanager view
        self.source_manager.refreshView()

        # hide progressdialog
        if update_progress:
            self.progress_dialog.setValue(3)

        # finish measure time
        self._time_needed_to_remove_source = time.process_time() - start_time

    def addObject(self, source_index = None, mask_object_index = None):
        '''
        source_index: 
            int or None. default is None.
            determines what source is used as source for the new object.
            if None: uses the selected source.
        mask_object_index:
            int or None. default is None.
            determines what object shall be used as copy for inital settings of the new object.
            if None: uses the selected object, but does not copy the position, size, and angle.
        '''

        # if no source is specified and there is none, return. otherwise, use the selected source.
        if source_index is None:
            if self.source_selection is None:
                return
            else:
                source_index = self.source_selection
        source = self.sources[source_index]

        # if feature merge tif is active inactivate it
        if source.merged_tif_active:
            merge_tif = self.getCurrentPipeline()._merged_tif
            if merge_tif.active:
                merge_tif.active = False
                merge_tif.setState()
        
        # measure time for progressdialog
        start_time = time.process_time()

        # determine if progressdialog shall be shown
        update_progress = self._time_needed_to_add_object >= self._TIME_NEEDED_TO_SHOW_PROGRESSDIALOG or self._time_needed_to_add_object == 0 and len(self.objects) >= 10

        # show progressdialog
        if update_progress:
            self.progressDialog()
            self.progress_dialog.setMaximum(5)

        # if no mask is specified: use selected object
        # copy spa (size, position, angle) only if there is a mask specified
        copy_spa = True
        if mask_object_index is None:
            copy_spa = False
            mask_object_index = self.object_selection

        # create name for the new object
        if source.filetype == 'tif':
            source_is_tif = True
            name = 'ROI {} - {}'.format(source.short_name, source.object_number)
        elif source.filetype == 'abf':
            source_is_tif = False
            name = 'ABF {} - {}'.format(source.short_name, source.object_number)
        
        # increase the number of objects for the source
        source.object_number += 1

        # if we add a TIF-object, we need pos, angle and size
        if source.filetype == 'tif':

            # if we dont have a TIF-object as mask, we use default params
            if mask_object_index is None or self.objects[mask_object_index].source.filetype != 'tif' or not copy_spa:
                pos, size, angle = cs_roi_params['roi']
                data = {
                    'pos': pos,
                    'angle': angle,
                    'size': size
                }
            else:
                object_mask = self.objects[mask_object_index]
                data = {
                    'pos': object_mask.pos,
                    'angle': object_mask.angle,
                    'size': object_mask.size
                }
        else:
            data = {}

        # copy invert and ellipse mode
        if mask_object_index is not None:
            data['invert'] = self.objects[mask_object_index].invert
            data['ellipse_mode'] = self.objects[mask_object_index].ellipse_mode

        if update_progress:
            self.progress_dialog.setValue(1)

        # create new object
        object_ = Object(name = name, source = source, **data)
        self.objects.append(object_)
        object_.pipeline.initPipeline(self, source_is_tif = source_is_tif, parent = self.pipeline_manager.feature_view)
        if mask_object_index is not None:
            object_.pipeline.initMethodConfigurations(self.objects[mask_object_index].pipeline, source.filetype)

        # set the adjustfrequency feature settings of the new object to the adjustfrequency settings of the source
        object_.pipeline._adjust_frequency.input['object_source_af_params'] = (source.original_frequency,
            source.adjusted_frequency,
            source.adjust_frequency_active,
            source.adjust_frequency_method)
        object_.pipeline._adjust_frequency.inputConfiguration()
        
        if update_progress:
            self.progress_dialog.setValue(2)
        
        # calculate the new pipeline for first time
        self.refreshPipeline(object_index = len(self.objects) - 1, start_with_feature = self.cell_selection, plot = False)
        
        if update_progress:
            self.progress_dialog.setValue(3)
            
        # reset the CC and compare plots. must be done before selectobject, because selectobject refreshes the plots
        # and for that we need the new created plots
        self.plot_manager.resetCrossCorrelationPlots()
        if update_progress:
            self.progress_dialog.setValue(4)
        self.plot_manager.resetComparePlots()

        # refresh objectmanagerview and select the new object
        self.object_manager.refreshView()
        self.selectObject(len(self.objects)-1)

        if (self.getCurrentPipeline()._background_subtraction.active):
            self.getCurrentPipeline()._background_subtraction.showGUI()

        # hide progressdialog
        if update_progress:
            self.progress_dialog.setValue(5)

        # finish time measure
        self._time_needed_to_add_object = time.process_time() - start_time

    def selectObject(self, selection = None, force_source_selection = False, force_plot_resizing = False, prevent_feature_undisplay = False):
        '''
        selection:
            int or None. default is None.
            determines what object shall be selected. 
            if None, the last added object will be selected.
        force_source_selection:
            bool. default is False.
            if True, forces the selectsource call.
        force_plot_resizing:
            bool. default is False.
            if True, forces a plot resizing.
        prevent_feature_undisplay
            bool. default is False.
            if True, prevents the check to undisplay plots of background_subtraction and baseline of pipeline of selected object
        '''

        # if no selection is specified: select the last added object if available, otherwise return
        if selection is None:
            if len(self.objects) == 0:
                self.object_selection = None
                # call refreshPlots s.t. plots will be undisplayed
                self.refreshPlots()
                # may call selectsource to set valid source_selection
                if self.source_selection is not None:
                    self.selectSource()
                return
            else:
                selection = len(self.objects) - 1

        # if merge tif of old object is active inactivate it for ROI cell calculation
        merge_tif = self.getCurrentPipeline()._merged_tif
        if merge_tif.active:
            merge_tif.active = False
            merge_tif.setState()

        # check if background subtraction / baseline is active. if it is, we undisplay it.
        if not prevent_feature_undisplay:
            background_subtraction = self.getCurrentPipeline()._background_subtraction
            if background_subtraction.active:
                background_subtraction.undisplayPlots()
            baseline = self.getCurrentPipeline()._baseline
            if baseline.active:
                baseline.undisplayPlots()

        # before we set the change, remember what the pipeline active states look like
        old_pipeline_active_states = None
        if self.object_selection is not None and not force_plot_resizing:
            old_pipeline_active_states = []
            for step in self.objects[self.object_selection].pipeline.getPipeline():
                old_pipeline_active_states.append(step.active)

        # set the change
        self.object_selection = selection

        # set the correct state of the objectmanager buttons
        object_manager_buttons_enabled = selection is not None and self.objects[selection].source.filetype == 'tif'
        self.object_manager.add_btn.setEnabled(object_manager_buttons_enabled)
        self.object_manager.add_masked_btn.setEnabled(object_manager_buttons_enabled)

        # disconnect objectmanager signals and make the visible row selection
        self.object_manager.tableItemSelectionChangedDisconnect()
        self.object_manager.table.selectRow(selection)
        self.object_manager.tableItemSelectionChangedConnect()
        
        # refresh the objectmanager style sheet for the correct selection color
        self.object_manager.refreshTableStyleSheet()

        # set the current source if it is not set yet
        if force_source_selection or self.source_selection is None or self.objects[selection].source is not self.sources[self.source_selection]:
            self.selectSource(self.sources.index(self.objects[selection].source))

        # refresh the cell selection view without setting the userroi because it did not change
        self.refreshCellSelectionView(prevent_setting_userroi = True)

        # refresh the plots
        self.refreshPlots()

        # refresh the pipelinemanager view and feature view
        self.pipeline_manager.refreshView()
        self.pipeline_manager.refreshPipelineView()

        # if the newly selected object has different active states than the previous object: refresh plot sizes
        if old_pipeline_active_states is None:
            change = True
        else:
            change = False
            for old_active_state, new_step in zip(old_pipeline_active_states, self.getCurrentPipeline().getPipeline()):
                if old_active_state != new_step.active:
                    change = True
                    break
        
        if change:
            self.plot_manager.refreshPlots()

    def removeObject(self, remove_object_index = None, remove_source = True, refresh = True, show_progress = True, object_selection_after = None, prevent_feature_undisplay = False):
        '''
        remove_object_index:
            int or None. default is None.
            determines what object shall be removed.
            if None: selected object will be removed.
        remove_source:
            bool. default is True.
            determines if a check whether to remove the source or not should be done.
        refresh:
            bool. default is True.
            determins if objectselection, plots and views shall be refreshed.
        show_progress:
            bool. default is True.
            determines if a progressdialog may be shown. if True, other things must hold for a progressdialog to be shown.
        object_selection_after:
            int or None. default is None.
            determines what object shall be selected after the removal. 
            if None: if the before-selected object was not removed, it will be selected after the removal. if the before-
                selected object was removed, but its source still exists, the last added object for that source will be
                selected after the removal. otherwise, the last added object will be selected.
            if -1: the last added object will be selected
        prevent_feature_undisplay:
            bool. default is False.
            if True, will prevent the check to undisplay backgroundsubtraction and baseline of the pipeline of the selected object
                if the selected object will be removed.
        '''

        # if no object is specified: use selected object if possible. if not, return.
        if remove_object_index is None:
            if self.object_selection is None:
                return
            else:
                remove_object_index = self.object_selection
        
        # measure time for progressdialog
        start_time = time.process_time()

        # determine if progressdialog shall be shown
        update_progress = show_progress and (self._time_needed_to_remove_object >= self._TIME_NEEDED_TO_SHOW_PROGRESSDIALOG or self._time_needed_to_remove_object == 0 and len(self.objects) >= 10)

        # show progressdialog
        if update_progress:
            self.progressDialog()
            self.progress_dialog.setMaximum(6)

        # reference the object to remove
        object_to_remove = self.objects[remove_object_index]
        if refresh and object_selection_after is None:
            selected_object_before_remove = self.objects[self.object_selection]

        # check if we have to undisplay background subtraction and baseline: only if we remove selected object
        if not prevent_feature_undisplay and remove_object_index == self.object_selection:
            background_subtraction = self.getCurrentPipeline()._background_subtraction
            if background_subtraction.active:
                background_subtraction.undisplayPlots()
            baseline = self.getCurrentPipeline()._baseline
            if baseline.active:
                baseline.undisplayPlots()

        # check if we have to remove the source
        source_removed = False
        if remove_source and len([o for o in self.objects if o.source is object_to_remove.source]) == 1:
            self.removeSource(self.sources.index(object_to_remove.source), show_progress = False)
            source_removed = True
        else:
            # if we dont remove the source: remove the object
            self.objects = [o for o in self.objects if o is not object_to_remove]

        if update_progress:
            self.progress_dialog.setValue(1)

        # reset the cc inputs: remove the object
        for step, input_name in [
            (self.pipeline_manager.amplitude_cross_correlation, 'amplitudes_data'),
            (self.pipeline_manager.spike_cross_correlation, 'trains_data')
        ]:
            if step.active:
                new_input_data_list = []
                for old_input_data in step.input[input_name]:
                    if old_input_data['name'] != object_to_remove.name:
                        new_input_data_list.append(old_input_data)
                step.input[input_name] = new_input_data_list

        # check if we have to refresh objectselection, plots and views
        if refresh:

            # reset the cc plots. needs to be done before selectobject because that refreshes plots and needs the new cc plots.
            self.plot_manager.resetCrossCorrelationPlots()

            if update_progress:
                self.progress_dialog.setValue(2)
                
            # reset the compare plots
            self.plot_manager.resetComparePlots()

            if update_progress:
                self.progress_dialog.setValue(3)

            # determine what object shall be selected
            force_source_selection = True
            if object_selection_after is None:
                if object_to_remove is selected_object_before_remove:
                    if not source_removed:
                        # no need to force source_selection because no source got removed and we select the same object again
                        force_source_selection = False
                        # if selected object got removed and source still exists: select last added object for this source
                        object_indices_for_this_source = [i for i, o in enumerate(self.objects) if o.source is object_to_remove.source]
                        object_selection_after = max(object_indices_for_this_source)
                        # else: if selected object got removed and source does not exist: select last added object (no need to specify, None works)
                else:
                    # if selected object did not got removed: select it again
                    object_selection_after = self.objects.index(selected_object_before_remove)
            elif object_selection_after == -1:
                object_selection_after = None
            # select new object and force a plot resize. always prevent the backgroundsubtraction and baseline undisplay check because we do it here.
            self.selectObject(object_selection_after, force_source_selection = force_source_selection, force_plot_resizing = True, prevent_feature_undisplay = True)

            # set cellselection method parameters to actual roi values
            self.cell_selection.updateROI()

            if update_progress:
                self.progress_dialog.setValue(4)

            # refresh the objectmanager view 
            self.object_manager.refreshView()

            if update_progress:
                self.progress_dialog.setValue(5)

        # hide progressdialog
        if update_progress:
            self.progress_dialog.setValue(6)

        # finish measure time
        self._time_needed_to_remove_object = time.process_time() - start_time

    def setSourceAttributes(self, source_index = None, attributes = {}, prevent_source_manager_refresh = False):
        '''
        source_index:
            int or None. default is None.
            determines what sources attributes are being set
            if None: the selected source is used
        attributes: 
            dict. default is empty dict.
            determines what attributes will be set. depending on what
            attributes are being set, refresh of data, views, plots, etc 
            might happen.
        prevent_source_manager_refresh:
            bool. default is False.
            determines if a sourcemanager view refresh shall be prevented.
        '''

        # if no source is specified: use source selection if possible. otherwise return.
        if source_index is None:
            if self.source_selection is None:
                return
            else:
                source_index = self.source_selection
                
        source = self.sources[source_index]

        # update the source.
        for key, value in attributes.items():
            setattr(source, key, value)

        # refresh the sourcemanager view
        if not prevent_source_manager_refresh:
            self.source_manager.refreshView()

        # check if start or end have been modified. if yes, movement correction must be refreshed.
        if len([k for k in attributes.keys() if k in ['start', 'end']]) > 0:
            # because movement correction will be done in a thread, we must call a callback
            mc = self.movement_corrections[source_index]
            if mc is None:
                self.setSourceAttributesCallback()
            else:
                # prepare movement correction
                mc.inputConfiguration()
                mc.calculated = [None for _ in mc.calculated]
                set_source_attributes_callback_kwargs = {
                    'source_index': source_index,
                    'movement_correction': mc
                }
                mc.update(updateDependend = False, plot = False, set_source_attributes_callback_kwargs = set_source_attributes_callback_kwargs)

        # check if offset has been modified. same callback needed.
        elif 'offset' in attributes.keys():
            self.setSourceAttributesCallback()
        elif len([k for k in attributes.keys() if k in ['adjusted_frequency', 'adjust_frequency_active', 'adjust_frequency_method']]):
            # get all objects belonging to the source and update their pipelines
            affected_object_indices = [i for i, object_ in enumerate(self.objects) if object_.source is self.sources[self.source_selection]]
            for i in affected_object_indices:
                feature = self.objects[i].pipeline._adjust_frequency
                # need to set the feature settings first
                feature.input['object_source_af_params'] = (source.original_frequency,
                        source.adjusted_frequency,
                        source.adjust_frequency_active,
                        source.adjust_frequency_method)
                feature.inputConfiguration()
                self.refreshPipeline(plot = True, object_index = i, start_with_feature = feature, ignore_cross_correlation = i != affected_object_indices[-1])

    def setSourceAttributesCallback(self, set_source_attributes_callback_kwargs = None):
        
        # if we come from movement correction calculation: set the data
        if set_source_attributes_callback_kwargs is not None:
            source_index = set_source_attributes_callback_kwargs['source_index']
            mc = set_source_attributes_callback_kwargs['movement_correction']
            self.sources[source_index].setCorrectedData(mc.output['source'])

        # get objects for the source
        object_indices_for_that_source = [i for i, o in enumerate(self.objects) if o.source is self.sources[self.source_selection]]

        # refresh the pipeline for the affected objects
        for index in object_indices_for_that_source:
            # only do CC for the last object
            self.refreshPipeline(plot = True, object_index = index, start_with_feature = self.cell_selection, ignore_cross_correlation = index != object_indices_for_that_source[-1])


    def setObjectAttributes(self, object_index = None, attributes = {}, prevent_object_manager_refresh = False, prevent_roiview_refresh = False):
        '''
        object_index:
            int or None. default is None.
            determines what objects attributes are being set
            if None: the selected object is used
        attributes: 
            dict. default is empty dict.
            determines what attributes will be set. depending on what
            attributes are being set, refresh of data, views, plots, etc 
            might happen.
        prevent_object_manager_refresh:
            bool. default is False.
            determines if a refresh of the objectmanager view shall be prevented.
        prevent_roiview_refresh:
            bool. default is False.
            determines if a refresh of the roiview shall be prevented.
        '''

        # if no object is specified: use object selection if possible. otherwise return.
        if object_index is None:
            if self.object_selection is None:
                return
            else:
                object_index = self.object_selection

        # update the object.
        for key, value in attributes.items():
            setattr(self.objects[object_index], key, value)

        # refresh the objectmanager view
        if not prevent_object_manager_refresh:
            self.object_manager.refreshView()

        # if name or active have been modified: reset plots and recalculate CC
        if len([a for a in attributes.keys() if a in ['name', 'active']]) > 0:
            self.plot_manager.resetCrossCorrelationPlots()
            self.plot_manager.resetComparePlots()
            self.refreshPipeline(only_cross_correlation = True)

        # if active, pos, size, angle or ellipse_mode have been modified: refresh the ROI View
        if not prevent_roiview_refresh:
            if len([a for a in attributes.keys() if a in ['active', 'pos', 'size', 'angle', 'ellipse_mode']]) > 0:
                self.plot_manager.refreshROIView()

        # if ellipse_mode has been modified: refresh pipeline from cellselection
        if 'ellipse_mode' in attributes.keys():
            self.refreshPipeline(plot = True, object_index = object_index, start_with_feature = self.cell_selection)

        # if invert has been modified: refresh pipeline after processing, because thats the point where invert happens.
        # set processing_changed to True to indicate that the processing data has changed
        if 'invert' in attributes.keys():
            self.refreshPipeline(plot = True, object_index = object_index, start_after_processing = True, processing_changed = True)

    def _preparePipelineLoop(self,
        object_index = None,
        start_with_feature = None,
        start_after_start_with_feature = False,
        start_after_processing = False,
        stop_after_processing = False,
        ignore_cross_correlation = False,
        only_cross_correlation = False,
        from_refresh_pipeline = False,
        processing_changed = False):
        '''
        object_index: 
            int or None. default is None.
            determines what objects pipeline shall be iterated. 
            if None: use the selected object.
        start_with_feature:
            int, feature from the calculating pipeline, or None. default is None.
            determines where to start the loop.
            if None: the complete pipeline will be iterated (CellSelection is before the pipeline so it
                will not be iterated)
            if int: start with the feature at this index.
            if feature from the calculating pipeline: start with this feature.
        start_after_start_with_feature:
            bool. default is False.
            when start_with_feature is set and start_after_start_with_feature is True, iteration starts
                after the feature, not before it.
            when start_with_feature is set to CellSelection and start_after_start_with_feature is True,
                edit_roi will be True, otherwise False.
        start_after_processing:
            bool. default is False.
            determines if iteration should start after processing. if True, will override all other start
                parameter, except only cross_correlation.
        stop_after_processing:
            bool. default is False.
            determines if iteration stops with last processing feature.
        ignore_cross_correlation:
            bool. default is False.
            determines if the CrossCorrelation will be ignored.
        only_cross_correlation:
            bool. default is False.
            determines if only the CrossCorrelation will be iterated. if True, will override all other start
                and stop parameters, including ignore_cross_correlation.
        from_refresh_pipeline:
            bool. default is False.
            indicates if the parameters come from refreshPipeline and are used for refreshPlots now. When this 
                is True, start_after_start_with is True, start_after_processing is False and only_cross_correlation
                is False, plotting will begin one feature earlier than originally indicated.
        processing_changed:
            bool. default is False.
            indicates that the processing data has changed, no matter what the other parameters are. 
        '''
        
        # if no object is specified: use the selected object, if possible. otherwise return.
        if object_index is None:
            if self.object_selection is None:
                return None
            else:
                object_index = self.object_selection

        # get the object
        object_ = self.objects[object_index]

        # get pipeline
        pipeline = object_.pipeline
        calculating_pipeline = pipeline.getCalculatingPipeline()

        # cc indices
        cc_indices = [calculating_pipeline.index(pipeline._spike_cross_correlation), calculating_pipeline.index(pipeline._amplitude_cross_correlation)]

        # max raw index
        max_raw_index = max([calculating_pipeline.index(f) for f in pipeline.getRawFeatures()])

        # max processing index
        max_processing_index = max([calculating_pipeline.index(f) for f in pipeline.getProcessingFeatures()])

        # spike detection and spike cc index
        spike_detection_index = calculating_pipeline.index(pipeline._spike_detection)
        spike_cc_index = calculating_pipeline.index(pipeline._spike_cross_correlation)

        # eventdetection and eventshape index
        burst_detection_index = calculating_pipeline.index(pipeline._burst_detection)
        event_shape_index = calculating_pipeline.index(pipeline._event_shape)

        # determine where to start
        start_with_cell = False
        start_before = 0
        if start_with_feature is not None:
            if isinstance(start_with_feature, int):
                start_before = start_with_feature
            else:
                if start_with_feature is self.cell_selection:
                    start_with_cell = True
                    start_before = 0
                else:
                    if start_with_feature in calculating_pipeline:
                        start_before = calculating_pipeline.index(start_with_feature)
                    else:
                        # this should not happen. if it happens, just start at 0.
                        start_before = 0
        # if start_after_start_with_feature is set, we want to start right after the given feature.
        # thus, add an except if cellselection is the begin.
        # however, if from_refresh_pipeline is true, we do not start one later. this is because 
        # the parameter originally come from refreshPipeline and are used for refreshPlots now and 
        # the feature that was indicated with start_with_feature must be plotted, too.
        edit_roi = False
        if start_after_start_with_feature and not from_refresh_pipeline:
            if start_with_cell:
                edit_roi = True
                start_with_cell = False
            else:
                start_before += 1
        # if start_after_processing is set, we ignore all until now
        if start_after_processing:
            start_before = max_processing_index + 1
        # if only_cross_correlation is set, we ignore all until now
        if only_cross_correlation:
            start_before = min(cc_indices)

        # determine where to stop
        # default: stop after last feature.
        stop_after = len(calculating_pipeline)-1
        # if ignore cc: stop before cc.
        if ignore_cross_correlation:
            stop_after = min(cc_indices)-1
        # if we start before the last processing feature, processing data is changed. this leads 
        # to all features after it needing to be recalculated.
        # but: if we start after the last processing feature, processing data will not be changed,
        # only the analysing feature. this means we can stop right after the analysing feature.
        # subtracting start_after_start_with_feature because this would otherwise falsify the statement.
        # also check if processing_changed is True, because this indicates a change no matter what
        if start_before - start_after_start_with_feature > max_processing_index and not processing_changed:
            # exception: if analysing feature is spike detection, spike cc and eventshape must be updated.
            if start_before - start_after_start_with_feature == spike_detection_index:
                stop_after = max(spike_cc_index, event_shape_index)
            # otherwise: if analysing feature is an eventdetection, eventshape must be updated.
            elif start_before - start_after_start_with_feature == burst_detection_index:
                stop_after = event_shape_index
            # otherwise: stop right after the analysing feature
            else:
                stop_after = start_before
        # if we should stop after processing: stop after processing.
        if stop_after_processing:
            stop_after = max_processing_index
        # if we should only do cc: stop after cc.
        if only_cross_correlation:
            stop_after = max(cc_indices)

        return (object_index,
            object_,
            pipeline,
            calculating_pipeline,
            max_raw_index,
            max_processing_index,
            start_with_cell,
            start_before,
            edit_roi, 
            stop_after,
            cc_indices)

    def refreshPipeline(self, plot = True, **kwargs):
        '''
        plot:
            bool. default is True.
            determines if refreshPlots will be called.
        for keyword arguments, see self._preparePipelineLoop
        '''

        prepare_pipeline_loop = self._preparePipelineLoop(**kwargs)
        if prepare_pipeline_loop is None:
            # return if there are no objects available.
            return
        object_index = prepare_pipeline_loop[0]
        object_ = prepare_pipeline_loop[1]
        calculating_pipeline = prepare_pipeline_loop[3]
        max_raw_index = prepare_pipeline_loop[4]
        max_processing_index = prepare_pipeline_loop[5]
        start_with_cell = prepare_pipeline_loop[6]
        start_before = prepare_pipeline_loop[7]
        edit_roi = prepare_pipeline_loop[8]
        stop_after = prepare_pipeline_loop[9]

        # check if we start with cellselection
        if start_with_cell:
            # set the parameters for cellselection, without refreshing the roiview. we may prevent
            # the userroi setting when we work with the selected object
            self.refreshCellSelectionView(object_index = object_index,
                prevent_roiview_refresh = True,
                prevent_setting_userroi = object_index == self.object_selection)

            # update the cellselection
            self.cell_selection.update(updateDependend = False)
        else:
            self.refreshCellSelectionView(object_index = object_index,
                prevent_roiview_refresh = True,
                prevent_setting_userroi = True)

        if start_with_cell or edit_roi:
            # let the cellselection update our data structure
            self.cell_selection.editROI(roi_index = object_index)

        # set initial object attributes
        if object_.cell_mean is None:
            object_.processed = deepcopy(object_.source.getData())
            object_.raw = deepcopy(object_.source.getData())
        else:
            object_.processed = deepcopy(object_.cell_mean)
            object_.raw = deepcopy(object_.cell_mean)
        # set variables used in loop 
        burst_time = False
        spike_time = False
        object_noise_std = 0

        for index, step in enumerate(calculating_pipeline):

            # if we just finished with raw: set raw
            if index == max_raw_index + 1:
                object_.raw = deepcopy(object_.processed)

            # if we just finished with processed: invert
            if index == max_processing_index + 1 and object_.invert:
                object_.processed = -object_.processed

            # stop if stop_after indicates it
            if index > stop_after:
                break
        
            # continue if feature is not active
            if not step.active:
                continue  

            # update feature if start_after indicates it
            if index >= start_before:

                # set input 
                for key, value in [
                    ('y', object_.processed),
                    ('roi_ellipse_mode', object_.ellipse_mode),
                    ('roi_params', (object_.pos, object_.size, object_.angle)),
                    ('object_source', object_.source),
                    ('object_source_frequency', object_.source.getFrequency()),
                    ('object_source_af_params', (object_.source.original_frequency,
                        object_.source.adjusted_frequency,
                        object_.source.adjust_frequency_active,
                        object_.source.adjust_frequency_method)),
                    ('object_noise_std', object_noise_std),
                    ('cell', object_.cell),
                    ('burst_time', burst_time),
                    ('spike_time', spike_time)
                ]:
                    if key in step.input.keys():
                        step.input[key] = value
                if 'trains_data' in step.input.keys():
                    trains_data = []
                    for o in self.objects:
                        if o.active:
                            spike_train = o.pipeline._spike_detection.output['train']
                            trains_data.append({
                                'train': spike_train,
                                'freq': o.source.getFrequency(),
                                'name': o.name,
                                'offset': o.source.offset
                            })
                    step.input['trains_data'] = trains_data
                if 'amplitudes_data' in step.input.keys():
                    amplitudes_data = []
                    for o in self.objects:
                        if o.active:
                            amplitudes_data.append({
                                'freq': o.source.getFrequency(),
                                'name': o.name,
                                'processed': o.processed,
                                'offset': o.source.offset
                            })
                    step.input['amplitudes_data'] = amplitudes_data

                # update
                step.inputConfiguration()
                step.activateFunc()
                step.update(updateDependend = False, plot = False)

            # get output
            if 'y' in step.output.keys() and step.output['y'] is not None:
                object_.processed = step.output['y']
            if 'noise_std' in step.output.keys() and step.output['noise_std'] is not None:
                object_noise_std = step.output['noise_std']
            if 'time' in step.output.keys():
                if isinstance(step, BurstDetection):
                    burst_time = step.output['time']
                elif isinstance(step, SpikeDetection):
                    spike_time = step.output['time']

        #if start_with_cell or edit_roi:
        if start_with_cell or edit_roi:
            # reset the cellselection user roi if its not the currently selected object
            if object_index != self.object_selection and self.object_selection is not None:
                self.refreshCellSelectionView(object_index = self.object_selection,
                    prevent_roiview_refresh = True)
        else:
            self.refreshCellSelectionView(object_index = self.object_selection,
                prevent_roiview_refresh = True,
                prevent_setting_userroi = True)

        if plot:
            self.refreshPlots(**kwargs, from_refresh_pipeline = True)
            
    def refreshPlots(self, **kwargs):
        '''
        for keyword arguments, see self._preparePipelineLoop
        '''
        
        prepare_pipeline_loop = self._preparePipelineLoop(**kwargs)
        if prepare_pipeline_loop is None:
            # undisplay plots and return if there are no objects available
            for step in self.getCurrentPipeline().getPipeline():
                step.undisplayPlots()
            self.cell_selection.imv.roiCurve.setData([], [])
            self.plot_manager.processed.setData('Processed', [], [])
            self.plot_manager.removePlotsForObjectComparison(self.plot_manager.processed)
            return
        object_index = prepare_pipeline_loop[0]
        object_ = prepare_pipeline_loop[1]
        pipeline = prepare_pipeline_loop[2]
        calculating_pipeline = prepare_pipeline_loop[3]
        max_raw_index = prepare_pipeline_loop[4]
        max_processing_index = prepare_pipeline_loop[5]
        start_before = prepare_pipeline_loop[7]
        stop_after = prepare_pipeline_loop[9]
        cc_indices = prepare_pipeline_loop[10]

        # refresh the compare plots for the object
        self.plot_manager.refreshComparePlots(object_index = object_index)

        # check to plot raw
        if object_index == self.object_selection and start_before <= max_raw_index:
            # plot the raw data
            self.cell_selection.imv.roiCurve.setData(object_.source.frameRange(), object_.raw, name = 'cell mean')

        # check to plot processed. add one to max_processing_index because of invert: its done right after max_processing_index.
        if object_index == self.object_selection and start_before <= max_processing_index + 1:
            # plot the processed data
            self.plot_manager.processed.setData('Processed', object_.source.secondsRange(), object_.processed)

        # set the y-axis-label for plots
        if object_index == self.object_selection:
            baseline_active = pipeline._baseline.active
            filetype_abf = object_.source.filetype == 'abf'
            source_unit = object_.source.unit
            self.plot_manager.namePlotYAxis(baseline_active = baseline_active, filetype_abf = filetype_abf, source_unit = source_unit)

        # only plot feature plots if its the selected object
        if object_index == self.object_selection:

            for index, step in enumerate(calculating_pipeline):
                # stop if stop_after indicates it
                if index > stop_after:
                    break
            
                # undisplay plots and continue if feature is not active
                if not step.active:
                    step.undisplayPlots()
                    continue

                # plot if start_after indicates it
                if index >= start_before:
                    step.updateLivePlot()

        # special case for cc plots: these shall be updated, even if the object is not the selected object
        else:
            for index in cc_indices:
                if index > stop_after or index < start_before:
                    continue
                step = calculating_pipeline[index]
                if not step.active:
                    step.undisplayPlots()
                else:
                    step.updateLivePlot()

    
    def refreshCellSelectionView(self, object_index = None, prevent_roiview_refresh = False, prevent_setting_userroi = False):
        '''
        object_index:
            int, or None. default is None.
            determines what object will be used in the cellselection.
            if None, the selected object is used.
        prevent_roiview_refresh:
            bool. default is False.
            determines whether the roiview refresh should be prevented.
        prevent_setting_userroi:
            bool. default is False.
            determines whether the cellselection userroi graphics should be set.
        '''

        if object_index is None:
            # if there is no source / object: undisplay cell selection. otherwise, if no source is selected, select the last
            if self.source_selection is None or self.object_selection is None:
                if len(self.sources) == 0:
                    self.cell_selection.input['roi_ellipse_mode'] = None
                    self.cell_selection.input['source'] = None
                    self.cell_selection.inputConfiguration()
                    self.cell_selection.setActive(False)
                    self.plot_manager.refreshROIView()
                    return
                else:
                    self.selectSource(len(self.sources)-1)
                    return
            else:
                object_index = self.object_selection

        object_ = self.objects[object_index]
        
        # set the input and call inputconfiguration
        self.cell_selection.input['roi_ellipse_mode'] = object_.ellipse_mode
        self.cell_selection.input['source'] = object_.source
        self.cell_selection.active = True
        self.cell_selection.inputConfiguration()

        # set the user roi to the selected objects parameters. prevent calculation of cellselection!
        # also need to check if source is optical. if not, do not do this!
        if not prevent_setting_userroi and object_.source.filetype == 'tif':
            self.cell_selection.disconnectUserROISignals()
            user_roi = self.cell_selection.getUserROI()
            user_roi.setPos(object_.pos)
            user_roi.setSize(object_.size)
            user_roi.setAngle(object_.angle)
            self.cell_selection.connectUserROISignals()
            self.cell_selection.updateROI(prevent_calculation = True)

        if not prevent_roiview_refresh:
            # refresh the roi view
            self.plot_manager.refreshROIView()

    def getCurrentPipeline(self):
        if self.object_selection is None:
            return self.pipeline_manager.default_pipeline
        else:
            return self.objects[self.object_selection].pipeline

    def progressDialog(self):
        self.progress_dialog = QtWidgets.QProgressDialog(labelText = 'loading', minimum = 0, maximum = 1, parent = self.parent, flags = QtCore.Qt.CustomizeWindowHint)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.show()