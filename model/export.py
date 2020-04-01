from PyQt5 import QtCore, QtWidgets
import numpy as np
import xlsxwriter
import time

from threads.Worker import Worker

def writeLoop(worksheet, row, col, values):
    if not isinstance(values, np.ndarray):
        row += 1
        worksheet.write(row, col, round(values, 4))
        return
    for value in values:
        row += 1
        worksheet.write(row, col, round(value, 4))

def writeFeature(worksheet, wrap, col, objects_names, data, label, x_axis = False, x_axis_label = None, x_axis_values = None):
    prev_x_axis_value = None

    for index, object_name in enumerate(objects_names):

        if x_axis:
            x_axis_value = x_axis_values[index]
            if not np.array_equal(prev_x_axis_value, x_axis_value):
                if col != 0:
                    col += 2
                row = 0
                worksheet.write(row, col, x_axis_label, wrap)
                writeLoop(worksheet, row, col, x_axis_value)
                col += 1
                prev_x_axis_value = x_axis_value

        row = 0
        title = object_name + ' ' + label
        worksheet.write(row, col, title, wrap)
        writeLoop(worksheet, row, col, data[index])
        col += 1

    return col


def export_work(data_manager, objects, data, file_info, export_time, cc_only_inside_sources, worker_progress_signal):
    try:
        progress = 0
        # get object indices list from binary list
        objects_indices = []
        for index, object_ in enumerate(objects):
            if object_:
                objects_indices.append(index)

        # sort objects such that they are grouped by source
        objects_indices_by_source = [
            [object_index for object_index in objects_indices if data_manager.objects[object_index].source is source]
            for source in data_manager.sources]

        # ungroup objects (but sorted now)
        objects_indices = []
        for objects_indices_ in objects_indices_by_source:
            for object_index in objects_indices_:
                objects_indices.append(object_index)

        # raw and processed?
        raw_cell_mean = data[0]
        processed = data[1]
        
        # get feature indices from binary list
        feature_indices = []
        for index, feature in enumerate(data[2:]):
            if feature:
                feature_indices.append(index)

        # get the current pipeline
        pipeline = data_manager.getCurrentPipeline()
        pipeline_array = pipeline.getCalculatingPipeline()

        # get the active states of all features grouped by pipeline
        active_states = [data_manager.objects[object_index].pipeline.getCalculatingActiveStates() for object_index in objects_indices]

        # get the feature indices whose features are not all inactive
        active_feature_indices = [feature_index for feature_index in feature_indices if any([active_state[feature_index] for active_state in active_states])]
        
        # get cc indices
        spike_cc_index = pipeline_array.index(pipeline._spike_cross_correlation)
        amplitude_cc_index = pipeline_array.index(pipeline._amplitude_cross_correlation)

        # get source index for every object
        sources_indices = [data_manager.sources.index(data_manager.objects[object_index].source) for object_index in objects_indices]

        # get the pipeline outputs, method names and parameters grouped by pipeline
        outputs = [
            [step.output for step in data_manager.objects[object_index].pipeline.getCalculatingPipeline()]
            for object_index in objects_indices]
        method_names = [
            [step.getMethod().name for step in data_manager.objects[object_index].pipeline.getCalculatingPipeline()]
            for object_index in objects_indices]
        parameters = [
            [
                {method.name: method.parameters for method in step.methods.values()}
                for step in data_manager.objects[object_index].pipeline.getCalculatingPipeline()]
            for object_index in objects_indices]

        # get the object names
        names = [data_manager.objects[object_index].name for object_index in objects_indices]

        # get the adjusted frequencies, if not available get original
        frequencies = [data_manager.sources[source_index].getFrequency() for source_index in sources_indices]

        # get secondsRange and frameRange for every object
        seconds_ranges = [data_manager.sources[source_index].secondsRange() for source_index in sources_indices]
        frame_ranges = [data_manager.sources[source_index].frameRange() for source_index in sources_indices]

        # get movement correction for every object
        movement_corrections = [
            None if data_manager.movement_corrections[source] is None
            else data_manager.movement_corrections[source].methods['Movement Correction'].getParameters()['correction']
            for source in sources_indices]

        progress += 1
        worker_progress_signal.emit(progress)

        # creating the excel file
        
        workbook = xlsxwriter.Workbook(file_info.absoluteFilePath())
        wrap = workbook.add_format({'text_wrap': True})

        # metadata
        
        metadata = workbook.add_worksheet('metadata')

        row = 0
        metadata.write(row, 0, 'Date of export:')
        metadata.write(row, 1, time.strftime('%x', export_time))
        row += 1
        metadata.write(row, 0, 'Time of export:')
        metadata.write(row, 1, time.strftime('%X', export_time))
        row += 1

        for col, header in enumerate([
            'object index',
            'name',
            'active',
            'source name',
            'source unit',
            'source recording frequency',
            'source start frame',
            'source end frame',
            'source offset',
            'source movement correction',
            'position',
            'angle',
            'size',
            'invert',
            'ellipse mode'
        ]):
            metadata.write(row, col, header)

        for feature_index in active_feature_indices:
            col += 1
            metadata.write(row, col, pipeline_array[feature_index].name + '\nMethod')
            col += 1
            metadata.write(row, col, pipeline_array[feature_index].name + '\nParameters')

        for index, object_index in enumerate(objects_indices):
            row += 1
            object_data = data_manager.objects[object_index]
            for col, content in enumerate([
                index + 1,
                object_data.name,
                str(object_data.active),
                object_data.source.name,
                object_data.source.unit,
                object_data.source.original_frequency,
                object_data.source.start,
                object_data.source.end,
                object_data.source.offset,
                movement_corrections[index],
                str(object_data.pos),
                str(object_data.angle),
                str(object_data.size),
                str(object_data.invert),
                str(object_data.ellipse_mode)
            ]):
                metadata.write(row, col, content)
                
            for feature_index in active_feature_indices:
                if active_states[index][feature_index]:
                    col += 1
                    method_name = method_names[index][feature_index]
                    metadata.write(row, col, method_name)
                    col += 1
                    metadata.write(row, col, str(parameters[index][feature_index][method_name]))
                else:
                    col += 2

        progress += 1
        worker_progress_signal.emit(progress)

        # raw

        if raw_cell_mean:
            cell_mean = workbook.add_worksheet('Raw')
            cell_mean_data = [data_manager.objects[oject_index].cell_mean for oject_index in objects_indices]
            for index, cell_mean_data_ in enumerate(cell_mean_data):
                if cell_mean_data_ is None:
                    cell_mean_data[index] = data_manager.sources[sources_indices[index]].getData()
            writeFeature(cell_mean, wrap, 0, names, cell_mean_data, 'Raw', x_axis=True, x_axis_label='Time (frame)', x_axis_values=frame_ranges)
            progress += 1
            worker_progress_signal.emit(progress)

        # processed

        if processed:
            processed = workbook.add_worksheet('Processed')
            processed_data = [data_manager.objects[object_index].processed for object_index in objects_indices]
            writeFeature(processed, wrap, 0, names, processed_data, 'Processed', x_axis=True, x_axis_label='Time (s)', x_axis_values=seconds_ranges)
            progress += 1
            worker_progress_signal.emit(progress)

        # features, except for cc
        index = 0
        for feature_index in feature_indices:

            # ignore cc for now
            if feature_index in [spike_cc_index, amplitude_cc_index]:
                continue

            # only do stuff (add worksheet and fill) if any of the features is active, and never create for AdjustFrequency
            if feature_index in active_feature_indices and pipeline_array[feature_index].name != 'Adjust Frequency':
                col = 0
                worksheet = workbook.add_worksheet(pipeline_array[feature_index].name)

                for (output_key, label, use_seconds_as_x) in [
                    ('background mean', 'Background Mean', False),
                    ('baseline', 'Baseline', False),
                    ('train', 'Train', True)
                ]:
                    if output_key in pipeline_array[feature_index].output.keys():
                        objects_indices_ = [object_index for object_index in range(len(objects_indices)) if active_states[object_index][feature_index] and outputs[object_index][feature_index][output_key] is not None]
                        objects_names = [names[object_index] for object_index in objects_indices_]
                        data_ = [outputs[object_index][feature_index][output_key] for object_index in objects_indices_]
                        x_axis_values = [seconds_ranges[object_index] if use_seconds_as_x else frame_ranges[object_index] for object_index in objects_indices_]
                        x_axis_label = 'Time (s)' if use_seconds_as_x else 'Time (frames)'
                        col = writeFeature(worksheet, wrap, col, objects_names, data_, label, x_axis=True, x_axis_label=x_axis_label, x_axis_values=x_axis_values)

                for (output_key, label) in [
                    ('mean shape', 'Mean Shape'),
                    ('mean shape smoothed', 'Mean Shape Smoothed')
                ]:
                    if output_key in pipeline_array[feature_index].output.keys():
                        objects_indices_ = [object_index for object_index in range(len(objects_indices)) if active_states[object_index][feature_index] and outputs[object_index][feature_index][output_key] is not None]
                        objects_names = [names[object_index] for object_index in objects_indices_]
                        data_ = [outputs[object_index][feature_index][output_key] for object_index in objects_indices_]
                        x_axis_values = []
                        for index, object_index in enumerate(objects_indices_):
                            left,right = parameters[object_index][feature_index][method_names[object_index][feature_index]]['interval']
                            data_len = len(data_[index])
                            x_axis_values.append(np.linspace(-left / 1000.0, right / 1000.0, num=data_len))
                        col = writeFeature(worksheet,wrap, col, objects_names, data_, label, x_axis=True, x_axis_label='Time (s)', x_axis_values=x_axis_values)

                if 'psd' in pipeline_array[feature_index].output.keys():
                    objects_indices_ = [object_index for object_index in range(len(objects_indices)) if active_states[object_index][feature_index] and outputs[object_index][feature_index]['psd'] is not None]
                    objects_names = [names[object_index] for object_index in objects_indices_]
                    data_ = [outputs[object_index][feature_index]['psd'] for object_index in objects_indices_]
                    x_axis_values = [outputs[object_index][feature_index]['frequencies'] for object_index in objects_indices_]
                    col = writeFeature(worksheet, wrap, col, objects_names, data_, 'PSD', x_axis=True, x_axis_label='Frequency (Hz)', x_axis_values=x_axis_values)

                if col != 0:
                    col += 2

                for (output_key, label)  in [
                    ('noise_std', 'Standard Deviation of Noise'),
                    ('time', 'Time of Peak (s)'),
                    ('amplitude', 'Amplitude of Peak'),
                    ('mean amplitude', 'Mean Amplitude'),
                    ('duration', 'Duration (s)'),
                    ('mean duration', 'Mean Duration (s)'),
                    ('max power frequency', 'Frequency of Max PSD Value (Hz)'),
                    ('max power', 'Max PSD Value'),
                    ('spike frequency', 'Spike Frequency (#Spikes / second)'),
                    ('burst frequency', 'Burst Frequency (#Bursts / second)')
                ]:
                    if output_key in pipeline_array[feature_index].output.keys():
                        objects_indices_ = [object_index for object_index in range(len(objects_indices)) if active_states[object_index][feature_index] and outputs[object_index][feature_index][output_key] is not None]
                        objects_names = [names[object_index] for object_index in objects_indices_]
                        data_ = [outputs[object_index][feature_index][output_key] for object_index in objects_indices_]
                        if output_key in ['time', 'mean duration', 'duration']:
                            freqs = [frequencies[object_index] for object_index in objects_indices_]
                            data_ = [d / freqs[idx] for idx,d in enumerate(data_)]
                        col = writeFeature(worksheet, wrap, col, objects_names, data_, label, x_axis=False)
                        col += 2

                index += 1
            
            # update progress for every feature that was selected
            progress += 1
            worker_progress_signal.emit(progress)

        # cc

        for feature_index in [spike_cc_index, amplitude_cc_index]:
            # check if feature was selected
            if feature_index in feature_indices:
                
                feature = pipeline_array[feature_index]

                # only do stuff (create worksheet and fill) if there is output
                if feature.active and len([out for out in feature.output.values() if out is None]) == 0:
                    cross_correlation = workbook.add_worksheet(pipeline_array[feature_index].name)
                    row = 0
                    col = 0

                    cc_objects_names = [data_['name'] for data_ in feature.input[feature.input_data_name] if not 'train' in data_.keys() or data_['train'] is not None]
                    if cc_only_inside_sources:
                        cc_objects = []
                        for name in cc_objects_names:
                            for object_ in data_manager.objects:
                                if object_.name == name:
                                    cc_objects.append(object_)
                                    break
                    n = len(cc_objects_names)
                    combinations = []
                    for i in range(n-1):
                        for j in range(i+1, n):
                            if not cc_only_inside_sources or cc_objects[i].source is cc_objects[j].source:
                                combinations.append((i,j))
                    
                    cc_names = ['{}\n{}'.format(cc_objects_names[i], cc_objects_names[j]) for (i,j) in combinations]
                    data_ = [feature.output['correlation'][i,j] for (i,j) in combinations]
                    x_axis_values = [feature.output['xrange'] for _ in combinations]
                    col = writeFeature(cross_correlation, wrap, col, cc_names, data_, 'Correlation', x_axis=True, x_axis_label='Lag (s)', x_axis_values=x_axis_values)
                    col += 2
                    data_ = [feature.output['coefficient'][i,j] for (i,j) in combinations]
                    col = writeFeature(cross_correlation, wrap, col, cc_names, data_, 'Correlation Coefficient', x_axis=False)
                    col += 2
                    title = 'Main Lag' if feature_index == amplitude_cc_index else 'Center of Bin that contains Main Lag'
                    data_ = [feature.output['delay'][i,j] for (i,j) in combinations]
                    col = writeFeature(cross_correlation, wrap, col, cc_names, data_, title, x_axis=False)
                    if feature_index == amplitude_cc_index:
                        col += 2
                        data_ = [feature.output['delay coefficient'][i,j] for (i,j) in combinations]
                        col = writeFeature(cross_correlation, wrap, col, cc_names, data_, 'Correlation Coefficient at Main Lag', x_axis=False)

                # update progress for every feature that was selected
                progress += 1
                worker_progress_signal.emit(progress)

        # finish xlsx file
        try:
            workbook.close()
            result = True
        except IOError:
            result = False
        progress += 1
        worker_progress_signal.emit(progress)
    except (SystemExit, KeyboardInterrupt):
        raise
    except:
        result = False

    return result

def export(data_manager, objects, data, file_info, export_time, cc_only_inside_sources):
    data_manager.progressDialog()
    data_manager.progress_dialog.setMaximum(sum(data) + 3)

    def progress_callback(progress):
        data_manager.progress_dialog.setValue(progress)

    def callback(result):
        # if unsuccessful: show dialog
        if not result['result']:
            data_manager.progress_dialog.hide()
            QtWidgets.QMessageBox.warning(
                data_manager.parent,
                'Export not successful',
                'Exporting data was not successful.'
            )
        else:
            QtWidgets.QMessageBox.information(
                data_manager.parent,
                'Export successful',
                'Exporting data was successful.'
            )

    export_worker = Worker(
        export_work,
        kwargs = {
            'data_manager': data_manager,
            'objects': objects,
            'data': data,
            'file_info': file_info,
            'export_time': export_time,
            'cc_only_inside_sources': cc_only_inside_sources
        },
        progress_callback = progress_callback,
        callback = callback
    )

    QtCore.QThreadPool.globalInstance().start(export_worker)