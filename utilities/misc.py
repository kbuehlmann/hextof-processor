# -*- coding: utf-8 -*-

import configparser
import os
from datetime import datetime

import h5py
import numpy as np
import psutil
import ast
import os
from configparser import ConfigParser
from collections import OrderedDict

from processor import DldFlashDataframeCreator as DldFlashProcessor

# ================================================================================
"""Functions for calculation of pulse energy and pulse energy density of optical laser.
Calibration values taken from Pump beam energy converter 800 400.xls
Units are uJ for energy, um for beam diameter, uJ/cm^2 for energy density (and arb. for diode signal)
"""

def PulseEnergy400(Diode):
    """Calculate the pulse energy of 400nm laser in uJ. The unit is um for beam diameter.
    
        :Parameter:
            Diode : numeric
                Measured value from photodiode (arb. units)
    """
    return 0.86 * (Diode * 0.0008010439 + 0.0352573)


def PulseEnergy800(Diode):
    """Calculate the pulse energy of 800nm laser in uJ. The unit is um for beam diameter.
    
        :Parameter:
            Diode : numeric
                Meausred value from photodiode (arb. units)
    """

    return 0.86 * (Diode * 0.0009484577 + 0.1576)


def EnergyDensity400(Diode, Diameter=600):
    """Calculate the pulse energy density of 400nm laser in uJ/cm^2.
    The units are um for beam diameter, uJ/cm^2 for energy density.
    
    :Parameters:
        Diode : numeric
            Measured value from photodiode (arb. units)
        Diameter : numeric
            Beam diameter
    """

    return PulseEnergy400(Diode) / (np.pi * np.square((Diameter * 0.0001) / 2))


def EnergyDensity800(Diode, Diameter=600):
    """Calculate the pulse energy density of 800nm laser in uJ/cm^2.
    The units are um for beam diameter, uJ/cm^2 for energy density.
    
    :Parameters:
        Diode : numeric
            Measured value from photodiode (arb. units)
        Diameter : numeric
            Beam diameter
    """

    return PulseEnergy800(Diode) / (np.pi * np.square((Diameter * 0.0001) / 2))

# %% Settings
# ================================================================================


def parse_category(category, settings_file='default'):
    """ parse setting file and return desired value
    Args:
        category (str): title of the category
        setting_file (str): path to setting file. If set to 'default' it takes
            a file called SETTINGS.ini in the main folder of the repo.
    Returns:
        dictionary containing name and value of all entries present in this
        category.
    """
    settings = ConfigParser()
    if settings_file == 'default':
        current_path = os.path.dirname(__file__)
        while not os.path.isfile(os.path.join(current_path, 'SETTINGS.ini')):
            current_path = os.path.split(current_path)[0]

        settings_file = os.path.join(current_path, 'SETTINGS.ini')
    settings.read(settings_file)
    try:
        cat_dict = {}
        for k,v in settings[category].items():
            try:
                if v[0] == "/":
                    cat_dict[k] = str(v)
                else:
                    cat_dict[k] = ast.literal_eval(v)
            except ValueError:
                cat_dict[k] = v
        return cat_dict
    except KeyError:
        print('No category {} found in SETTINGS.ini'.format(category))


def parse_setting(category, name, settings_file='default'):
    """ parse setting file and return desired value
    Args:
        category (str): title of the category
        name (str): name of the parameter
        setting_file (str): path to setting file. If set to 'default' it takes
            a file called SETTINGS.ini in the main folder of the repo.
    Returns:
        value of the parameter, None if parameter cannot be found.
    """
    settings = ConfigParser()
    if settings_file == 'default':
        current_path = os.path.dirname(__file__)
        while not os.path.isfile(os.path.join(current_path, 'SETTINGS.ini')):
            current_path = os.path.split(current_path)[0]

        settings_file = os.path.join(current_path, 'SETTINGS.ini')
    settings.read(settings_file)

    try:
        value = settings[category][name]
        if value[0] == "/":
            return str(value)
        else:
            return ast.literal_eval(value)
    except KeyError:
        print('No entry {} in category {} found in SETTINGS.ini'.format(name, category))
        return None
    except ValueError:
        return settings[category][name]

def write_setting(value, category, name, settings_file='default'):
    """ Write enrty in the settings file
    Args:
        category (str): title of the category
        name (str): name of the parameter
        setting_file (str): path to setting file. If set to 'default' it takes
            a file called SETTINGS.ini in the main folder of the repo.
    Returns:
        value of the parameter, None if parameter cannot be found.
    """
    settings = ConfigParser()
    if settings_file == 'default':
        current_path = os.path.dirname(__file__)
        while not os.path.isfile(os.path.join(current_path, 'SETTINGS.ini')):
            current_path = os.path.split(current_path)[0]

        settings_file = os.path.join(current_path, 'SETTINGS.ini')
    settings.read(settings_file)

    settings[category][name] = str(value)

    with open(settings_file, 'w') as configfile:
        settings.write(configfile)

def parse_logbook(log_text):    
    """ create a dictionary out of the log book entry 
    
    
    """
    assert isinstance(log_text,str) or os.path.isfile(log_text), 'Unrecognized format for logbook text'
    if os.path.isfile(log_text):
        with open(log_text,'r') as f:
            text = f.read()
    else:
        text = log_text
    logDict = OrderedDict()
    
    t_split = text.split('\nFEL:')
    logDict['comments'] = t_split.pop(0)
    text = 'FEL:{}'.format(t_split[0])
    log_sections = []
    for line in text.split('\n'):
        log_sections.append(line.strip())
    log_sections = '|'.join([x.strip() for x in text.split('\n')]).split('||')
    
    for section in log_sections:
        while section[:1] == '|':
            section=section[1:]
        slist = section.split('|')
        title = slist[0].split(':')
        name = title.pop(0)
        logDict[name] = OrderedDict()
        try:
            status = title[0].strip()
            if status != '':
                logDict[name]['status'] = title[0].strip()
        except:
            pass
        for line in slist[1:]:
            linelist = line.replace(':','=').split('=')
            try:
                logDict[name][linelist[0].strip()] = linelist[1].strip()
            except IndexError:
                logDict[name][linelist[0].strip()] = None
    return logDict


# %% Math
# ================================================================================


def radius(df, center=(0, 0)):
    """ Calculate the radius
    """

    return np.sqrt(np.square(df.posX - center[0]) + np.square(df.posY - center[1]))


def argnearest(array, val, rettype='vectorized'):
    """Find the coordinates of the nD array element nearest to a specified value

    :Parameters:
        array : numpy array
            Numeric data array
        val : numeric
            Look-up value
        rettype : str | 'vectorized'
            return type specification
            'vectorized' denotes vectorized coordinates (integer)
            'coordinates' denotes multidimensional coordinates (tuple)
    :Return:
        argval : numeric
            coordinate position
    """

    vnz = np.abs(array - val)
    argval = np.argmin(vnz)

    if rettype == 'vectorized':
        return argval
    elif rettype == 'coordinates':
        return np.unravel_index(argval, array.shape)


# %% Data Input/Output
# ================================================================================

def save_H5_hyperstack(data_array, filename, path=None, overwrite=True):
    """ Saves an hdf5 file with 4D (Kx,Ky,E,Time) images for import in FIJI

    :Parameters:
        data_array : numpy array
            4D data array, order must be Kx,Ky,Energy,Time
        filename : str
            The name of the file to save
        path : str
            The path to where to save hdf5 file. If None, uses the "results" folder from SETTINGS.ini
        overwrite : str
            If true, it overwrites existing file with the same
            name. Otherwise raises and error.
    """

    mode = "w-"  # fail if file exists
    if overwrite:
        mode = "w"

    if path is None:
        settings = configparser.ConfigParser()
        settings.read('SETTINGS.ini')
        path = settings['paths']['RESULTS_PATH']

    filepath = path + filename

    if not os.path.isdir(path):
        os.makedirs(path)
    if os.path.exists(
            filepath):  # create new files every time, with new trailing number
        i = 1
        new_filepath = filepath + "_1"
        while os.path.exists(new_filepath):
            new_filepath = filepath + "_{}".format(i)
            i += 1
        filepath = new_filepath

    f = h5py.File(filepath, mode)
    pumpProbeTimeSteps = len(data_array[..., :])
    print(
        'Creating HDF5 dataset with {} time steps'.format(pumpProbeTimeSteps))

    for timeStep in range(pumpProbeTimeSteps):
        xyeData = data_array[..., timeStep]
        dset = f.create_dataset(
            "experiment/xyE_tstep{}".format(timeStep),
            xyeData.shape,
            dtype='float64')
        dset[...] = xyeData

    print("Created file " + filepath)


def get_available_runs(rootpath):  # TODO: store the resulting dictionary to improve performance.
    """ Collects the filepaths to the available experimental run data.

    :Parameters:
        rootpath : str
            path where to look for data (recursive in subdirectories)

    :Return:
        available_runs : dict
            dict with run numbers as keys (e.g. 'run12345') and path where to load data from as str.
    """

    available_runs = {}

    for dir in os.walk(rootpath):
        if 'fl1user2' in dir[0]:
            try:
                run_path = dir[0][:-8]
                for name in dir[2]:
                    runNumber = name.split('_')[4]
                    if runNumber not in available_runs:
                        available_runs[runNumber] = run_path
            except:  # TODO: use an assertion method for more solid error tracking.
                pass

    return available_runs


def get_path_to_run(runNumber, rootpath):
    """ Returns the path to the data of a given run number

    :Parameters:
        runNumber : str or int
            run number as integer or string.
        rootpath : str
            path where to look for data (recursive in subdirectories)


    :Return:
        path : str
            path to where the raw data of the given run number is stored.
    """

    available_runs = get_available_runs(rootpath)

    try:
        return (available_runs['run{}'.format(runNumber)])
    except KeyError:
        raise KeyError('No run number {} under path {}'.format(runNumber, rootpath))


# %% String operations
# ================================================================================

def camelCaseIt(snake_case_string):
    """ Format a string in camel case
    """

    titleCaseVersion = snake_case_string.title().replace("_", "")
    camelCaseVersion = titleCaseVersion[0].lower() + titleCaseVersion[1:]

    return camelCaseVersion

# %% plotting
# # ================================================================================

def plot_lines(data, normalization='None', range=None, color_range=(0, 1),
               x_label='', y_label='', xlim=None, ylim=None, savefig=False,
               save_dir='E:/data/FLASH/', save_name='fig', static_curve=None):
    """ function to fit a series of curves with nice colorplot. """

    from matplotlib import pyplot as plt, cm

    f, axis = plt.subplots(1, 1, figsize=(8, 6), sharex=True)

    if range is None:
        from_ = 0
        to_ = len(data[:, ...])
    else:
        from_ = range[0]
        to_ = range[1]

    n_curves = len(data[from_:to_, 0])
    print('Number of curves: {}'.format(n_curves))
    cm_subsection = np.linspace(color_range[0], color_range[1], n_curves)
    colors = [cm.coolwarm(1 - x) for x in cm_subsection]

    for i, color in enumerate(colors[from_:to_]):
        label = '{}'.format(i)  # 20*(i+from_),
        curve = data[i + from_, :]  # result_unpumped[i]
        if normalization == 'sum':
            curve /= curve.sum()
        elif normalization == 'max':
            curve /= curve.max()

        axis.plot(curve, '-', color=color, label=label)
    #    axis[1].plot(x_axis_energy,curve_pump, '-', color=color,label=label)
    if static_curve is not None:
        plt.plot(static_curve, '--', color='black', label='static')
    plt.grid()
    plt.legend(fontsize='large')
    plt.xlabel(x_label, fontsize='xx-large')
    plt.ylabel(y_label, fontsize='xx-large')
    plt.xticks(fontsize='large')
    plt.yticks(fontsize='large')
    if xlim is not None:
        plt.xlim(xlim[0], xlim[1])
    if ylim is not None:
        plt.ylim(ylim[0], ylim[1])

    if savefig:
        plt.savefig('{}{}.png'.format(save_dir, save_name),
                    dpi=200, facecolor='w', edgecolor='w', orientation='portrait',
                    papertype=None, format=None, transparent=True, bbox_inches=None,
                    pad_inches=0.1, frameon=None)
    plt.show()


# ==================
# Methods by Mac!
# ==================


def shiftQuadrants(self, shiftQ1=0.231725, shiftQ2=-0.221625, shiftQ3=0.096575, shiftQ4=-0.106675, xCenter=1350,
                   yCenter=1440):
    """ Apply corrections to the dataframe. (Maciej Dendzik)

    Each quadrant of DLD is shifted in DLD time by shiftQn.
    xCenter and yCenter are used to define the center of the division.

         Q2     |     Q4
    ------------|------------
         Q1     |     Q3

    this picture is upside-down in plt.imshow because it starts from 0 in top right corner
    """
    # Q1
    # daskdataframe.where(condition,value) keeps the data where condition is True
    # and changes them to value otherwise.
    cond = ((self.dd['dldPosX'] > xCenter) | (self.dd['dldPosY'] > yCenter))
    self.dd['dldTime'] = self.dd['dldTime'].where(cond, self.dd['dldTime'] + shiftQ1)
    cond = ((self.dd['dldPosX'] > xCenter) | (self.dd['dldPosY'] < yCenter))
    self.dd['dldTime'] = self.dd['dldTime'].where(cond, self.dd['dldTime'] + shiftQ2)
    cond = ((self.dd['dldPosX'] < xCenter) | (self.dd['dldPosY'] > yCenter))
    self.dd['dldTime'] = self.dd['dldTime'].where(cond, self.dd['dldTime'] + shiftQ3)
    cond = ((self.dd['dldPosX'] < xCenter) | (self.dd['dldPosY'] < yCenter))
    self.dd['dldTime'] = self.dd['dldTime'].where(cond, self.dd['dldTime'] + shiftQ4)


def filterCircleDLDPos(self, xCenter=1334, yCenter=1426, radius=1250):
    """ Apply corrections to the dataframe. (Maciej Dendzik)

    Filters events with dldPosX and dldPosY within the radius from (xCenter,yCenter)

    """

    self.dd = self.dd[
        (((self.dd['dldPosX'] - xCenter) ** 2 + (self.dd['dldPosY'] - yCenter) ** 2) ** 0.5 <= radius)]


def correctOpticalPath(self, poly1=-0.00020578, poly2=4.6813e-7, xCenter=1334, yCenter=1426):
    """ Apply corrections to the dataframe. (Maciej Dendzik)

    Each DLD time is subtracted with a polynomial poly1*r + poly2*r^2,
    where r=sqrt((posx-xCenter)^2+(posy-yCenter)^2)

    This function makes corrections to the time of flight which take into account
    the path difference between the center of the detector and the edges of the detector

    """
    # Q1
    # daskdataframe.where(condition,value) keeps the data where condition is True
    # and changes them to value otherwise.

    self.dd['dldTime'] = self.dd['dldTime'] - \
                         (poly1 * ((self.dd['dldPosX'] - xCenter) ** 2 + (
                                 self.dd['dldPosY'] - yCenter) ** 2) ** 0.5 + \
                          poly2 * ((self.dd['dldPosX'] - xCenter) ** 2 + (self.dd['dldPosY'] - yCenter) ** 2))


# ==================
# Methods by Steinn!
# ==================

def load_binned_h5(file_name, mode='r', ret_type='list'):
    """ Load an HDF5 file saved with ``save_binned()`` method.

    :Parameters:
        file_name : str
            name of the file to load, including full path

        mode : str | 'r'
            Read mode of h5 file ('r' = read).
        ret_type: str | 'list','dict'
            output format for axes and histograms:
            'list' generates a list of arrays, ordered as
            the corresponding dimensions in data. 'dict'
            generates a dictionary with the names of each axis.

    :Returns:
        data : numpy array
            Multidimensional data read from h5 file.
        axes : numpy array
            The axes values associated with the read data.
        hist : numpy array
            Histogram values associated with the read data.
    """
    if file_name[-3:] == '.h5':
        filename = file_name
    else:
        filename = '{}.h5'.format(file_name)

    with h5py.File(filename, mode) as h5File:

        # Retrieving binned data
        frames = h5File['frames']
        data = []
        if len(frames) == 1:
            data = np.array(frames['f0000'])

        else:
            for frame in frames:
                data.append(np.array(frames[frame]))
            data = np.array(data)

        # Retrieving axes
        axes = [0 for i in range(len(data.shape))]
        axes_d = {}
        for ax in h5File['axes/']:
            vals = h5File['axes/' + ax][()]
            #             axes_d[ax] = vals
            idx = int(ax.split(' - ')[0][2:])
            if len(frames) == 1:  # shift index to compensate missing time dimension
                idx -= 1
            axes[idx] = vals

            # Retrieving delay histograms
        hists = []
        hists_d = {}
        for hist in h5File['histograms/']:
            hists_d[hist] = h5File['histograms/' + hist][()]
            hists.append(h5File['histograms/' + hist][()])

    if ret_type == 'list':
        return data, axes, hists
    elif ret_type == 'dict':
        return data, axes_d, hists_d


def reshape_binned(result, axes, hists, order_in='texy', order_out='etxy',
                   eoff=None, toff=None, t0=0, kx0=0, ky0=0, revert='te'):
    """ attempt to make a reshaping function. Not to be used yet"""
    print('using an unsafe function: reshape_binned')
    norm_array = hists[0] / max(hists[0])
    norm_array = norm_array[:, None, None, None]
    res_c = np.nan_to_num(result / norm_array)

    ax_order_in = list(order_in)
    ax_order_out = list(order_out)

    axes_c = []
    for axis in ax_order_out:  # reorder and invert axes
        if axis in revert:
            axes_c.append(axes[ax_order_in.index(axis)][::-1])
        else:
            axes_c.append(axes[ax_order_in.index(axis)])

    temp_order = ax_order_in[:]
    for i, axis in enumerate(ax_order_out):  # reorder data array
        if temp_order[i] != axis:
            res_c = res_c.swapaxes(i, temp_order.index(axis))
            print(temp_order)
            print('swapped axes {} and {}'.format(i, temp_order.index(axis)))
            temp_order[temp_order.index(axis)] = temp_order[i]
            temp_order[i] = axis
            print(temp_order)

    if ax_order_out[0] in revert:
        res_c = res_c[::-1, :, :, :]
    if ax_order_out[1] in revert:
        res_c = res_c[:, ::-1, :, :]
    if ax_order_out[2] in revert:
        res_c = res_c[:, :, ::-1, :]
    if ax_order_out[3] in revert:
        res_c = res_c[:, :, :, ::-1]

    for i, axis in enumerate(ax_order_out):
        if axis == 't':
            axes[i] -= t0
        elif axis == 'e':
            if None not in [eoff, toff]:
                axes[i] = t2e(axis[i], eoffset=eoff, toffset=toff)
        elif axis == 'x':
            axes[i] -= kx0
        elif axis == 'y':
            axes[i] -= ky0

    return res_c, axes_c


def get_system_memory_status(print_=False):
    mem_labels = ('total', 'available', 'percent', 'used', 'free')
    mem = psutil.virtual_memory()
    memstatus = {}
    for i, val in enumerate(mem):
        memstatus[mem_labels[i]] = val
    if print_:
        for key, value in memstatus.items():
            if key == 'percent':
                print('{}: {:0.3}%'.format(key, value))
            else:
                print('{}: {:0,.4} GB'.format(key, value / 2 ** 30))
    return memstatus


def read_and_binn(runNumber, *args, static_bunches=False, source='raw', save=True):
    print(datetime.now())

    processor = DldFlashProcessor.DldFlashProcessor()
    processor.runNumber = runNumber
    if source == 'raw':
        processor.readData()
    elif source == 'parquet':
        try:
            processor.readDataframes()
        except:
            print('No Parquet data found, loading raw data.')
            processor.readData()
            processor.storeDataframes()
    processor.postProcess()
    if static_bunches is True:
        processor.dd = processor.dd[processor.dd['dldMicrobunchId'] > 400]
    else:
        processor.dd = processor.dd[processor.dd['dldMicrobunchId'] > 100]
        processor.dd = processor.dd[processor.dd['dldMicrobunchId'] < 400]
    shortname = ''
    processor.resetBins()
    dldTime = delayStage = dldPos = None
    for arg in args:
        if arg[0] == 'dldTime':
            dldTime = arg[1:]
        elif arg[0] == 'delayStage':
            delayStage = arg[1:]
        elif arg[0] == 'dldPos':
            dldPos = arg[1:]

    if dldTime:
        processor.addBinning('dldTime', *dldTime)
        shortname += 'E'
    if delayStage:
        processor.addBinning('delayStage', *delayStage)
        shortname += 'T'
    if dldPos:
        processor.addBinning('dldPosX', *dldPos)
        processor.addBinning('dldPosY', *dldPos)
        shortname += 'KxKy'

    if save:
        saveName = 'run{} - {}'.format(runNumber, shortname)
        result = processor.computeBinnedData(saveName=saveName)
    else:
        result = processor.computeBinnedData()
    axes = processor.binRangeList
    return result, axes, processor

def create_dataframes(runNumbers, *args):
    """ Creates a parquet dataframe for each run passed.
    Returns
        fails: dictionary of runs and error which broke the dataframe generation
    """
    if isinstance(runNumbers, int):
        runNumbers = [runNumbers,]
    for run in args:
        if isinstance(run,list) or isinstance(run,tuple):
            runNumbers.extend(run)
        else:
            runNumbers.append(run)
    fails = {}
    for run in runNumbers:
        try:
            prc = DldFlashProcessor.DldFlashProcessor()
            prc.runNumber = run
            prc.readData()
            prc.storeDataframes()
            print('Stored dataframe for run {} in {}'.format(run,prc.DATA_PARQUET_DIR))
        except Exception as E:
            fails[run] = E
    for key, val in fails.items():
        print('{} failed with error {}'.format(key, val))

    return fails
