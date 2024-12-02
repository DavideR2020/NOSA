''' Feature Parameters '''

# Cell Selection
cs_active = False
cs_roi_params = {'roi':((10,10),(20,20),0)} # pos,size,angle

# Background Subtraction
bs_active = False
bs_roi_params = {'background_roi':((20,20),(20,20),0)}
bs_perisomatic_params = {'radius':4}

# Merged Tif
mt_params = {'merge': None}

# Baseline
bl_active = False
bl_polynomial_fitting_params = {'polyorder':1, 'intercept':0, 'use_marker': False, 'marker':[]}
bl_asymmetric_ls_params = {'smooth':100,'iterations':1, 'intercept':0}
bl_top_hat_params = {'factor':0.1}
bl_moving_average_params = {'window':100}

# Smoothing
sg_active = False
sg_savitzky_golay_params = {'window':3, 'polyorder':3}
sg_moving_average_params = {'window':3}
sg_butterworth_params = {'highcut':100.0, 'order':3}
sg_scaled_window_convolution_params = {'window_len':11, 'window':'hanning'}

# Burst Detection
bd_active = False
bd_params = {
    'dynamic_threshold': False,
    'relative_threshold': False,
    'dynamic_smooth': 300,
    'absolute_amplitude': 1,
    'relative_amplitude_type': 'use std of noise',
    'relative_amplitude': 1,
    'absolute_base': 0,
    'relative_base': 'minimal base: median',
    'duration': 50,
    'phase': 'depolarization'}

# Spike Detection
sd_active = False
sd_params = {
    'dynamic_threshold': False,
    'relative_threshold': False,
    'dynamic_smooth':300,
    'absolute_amplitude':1,
    'relative_amplitude_type': 'use std of noise',
    'relative_amplitude':1,
    'interval':50}

# Frequency Spectrum
fs_active = False
fs_fft_params = {'smooth':3, 'threshold':0, 'interval':(0,5)}

# Event Shape
es_active = False
es_params = {'smooth':3, 'interval':(200,200)}

# Cross Correlation
cc_active = False
cc_train_params = {'binfactor':1, 'maxlag':1}
cc_amplitude_params = {'maxlag':1, 'use_bandpass': False, 'order': 4, 'highpass_freq': 7, 'lowpass_freq': 12, 'use_instantaneous': False}

# Movement Correction
mc_params = {'correction': 'None [original image]'}

# Adjust Frequency
af_params = {'adjusted_frequency': 250.0}