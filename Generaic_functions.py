# -*- coding: utf-8 -*-
"""
Created on Mon Dec 11 19:41:46 2023

@author: admin
"""
# DO configure: port0 line 0 for X stage, port0 line 1 for Y stage, port 0 line 2 for Z stage, port 0 line 3 for Digitizer enable

# Generating Galvo X direction waveforms based on step size, Xsteps, Aline averages and objective
# StepSize in unit of um
# bias in unit of mm
global STEPS
STEPS = 25000
# 2mm per revolve
global DISTANCE
DISTANCE = 2
# scan direction suring Cscan is Y axis
from PyQt5.QtGui import QPixmap, QImage
import numpy as np

import os
import io
import traceback
import threading
import datetime
import configparser

_BREADCRUMB_LOCK = threading.Lock()
_BREADCRUMB_SEQ = 0
_BREADCRUMB_PATH = os.path.join(os.getcwd(), 'crash_breadcrumb.log')
_BREADCRUMB_CFG_PATH = os.path.join(os.getcwd(), 'config.ini')
_BREADCRUMB_LEVEL_CACHE = None
_BREADCRUMB_LEVEL_MTIME = None
_BREADCRUMB_LEVEL_LAST_CHECK = None

_BREADCRUMB_BASIC_TAGS = {
    'DO_LIGHT_ON_BEGIN',
    'DO_LIGHT_ON_DONE',
    'DO_LIGHT_OFF_BEGIN',
    'DO_LIGHT_OFF_DONE',
    'DO_LIGHT_A_ON_BEGIN',
    'DO_LIGHT_A_ON_DONE',
    'DO_LIGHT_B_ON_BEGIN',
    'DO_LIGHT_B_ON_DONE',
    'DO_MOVE_BEGIN',
    'DO_MOVE_DONE',
    'CAMERA_FINITE_ACQUIRE_BEGIN',
    'CAMERA_FINITE_ACQUIRE_DONE',
    'CAMERA_STREAM_ON_BEFORE',
    'CAMERA_STREAM_ON_AFTER',
    'CAMERA_STREAM_OFF_BEFORE',
    'CAMERA_STREAM_OFF_AFTER',
}


def _normalize_breadcrumb_level(raw):
    text = str(raw).strip().lower()
    if text in ('0', 'off', 'basic', 'simple', 'minimal', 'low'):
        return 'basic'
    if text in ('1', 'on', 'verbose', 'detail', 'detailed', 'full', 'high'):
        return 'verbose'
    return 'verbose'


def _get_breadcrumb_level():
    """Read breadcrumb level from config.ini with lightweight cache."""
    global _BREADCRUMB_LEVEL_CACHE
    global _BREADCRUMB_LEVEL_MTIME
    global _BREADCRUMB_LEVEL_LAST_CHECK

    now = datetime.datetime.now()
    if _BREADCRUMB_LEVEL_LAST_CHECK is not None:
        dt = (now - _BREADCRUMB_LEVEL_LAST_CHECK).total_seconds()
        if dt < 1.0 and _BREADCRUMB_LEVEL_CACHE is not None:
            return _BREADCRUMB_LEVEL_CACHE

    _BREADCRUMB_LEVEL_LAST_CHECK = now
    try:
        mtime = os.path.getmtime(_BREADCRUMB_CFG_PATH)
    except OSError:
        mtime = None

    if _BREADCRUMB_LEVEL_CACHE is not None and mtime == _BREADCRUMB_LEVEL_MTIME:
        return _BREADCRUMB_LEVEL_CACHE

    level = os.environ.get('UV_BREADCRUMB_LEVEL', 'verbose')
    try:
        cfg = configparser.ConfigParser()
        if cfg.read(_BREADCRUMB_CFG_PATH, encoding='utf-8'):
            if cfg.has_option('General', 'BreadcrumbLevel'):
                level = cfg.get('General', 'BreadcrumbLevel')
    except Exception:
        pass

    level = _normalize_breadcrumb_level(level)
    _BREADCRUMB_LEVEL_CACHE = level
    _BREADCRUMB_LEVEL_MTIME = mtime
    return level


def _should_emit_breadcrumb(tag):
    """Filter breadcrumb output by configured verbosity."""
    level = _get_breadcrumb_level()
    if level == 'verbose':
        return True

    # Always keep safety/diagnostic critical events.
    critical_keywords = ('EXCEPTION', 'ERROR', 'INVALID', 'TIMEOUT', 'DISABLED')
    for key in critical_keywords:
        if key in tag:
            return True

    return tag in _BREADCRUMB_BASIC_TAGS

class LOG():
    def __init__(self, ui):
        super().__init__()
        import datetime
        current_time = datetime.datetime.now()
        self.dir = os.getcwd() + '/log_files'
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        self.filePath = self.dir +  "/" + 'log_'+\
            str(current_time.year)+'-'+\
            str(current_time.month)+'-'+\
            str(current_time.day)+'-'+\
            str(current_time.hour)+'-'+\
            str(current_time.minute)+'-'+\
            str(current_time.second)+'.txt'
    def write(self, message):
        fp = open(self.filePath, 'a')
        fp.write(message+'\n')
        fp.close()
        # return 0


def parse_debug_flag(name, default=False):
    """Parse env switch values like 1/0, true/false, on/off."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    text = str(raw).strip().lower()
    if text in ('1', 'true', 'yes', 'on'):
        return True
    if text in ('0', 'false', 'no', 'off'):
        return False
    return default


def write_breadcrumb(tag, log=None, detail=''):
    """Write a single-line flushed breadcrumb for crash boundary tracing."""
    if not _should_emit_breadcrumb(tag):
        return ''

    global _BREADCRUMB_SEQ
    with _BREADCRUMB_LOCK:
        _BREADCRUMB_SEQ += 1
        seq = _BREADCRUMB_SEQ
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    tid = threading.get_ident()
    suffix = f" | {detail}" if detail else ''
    line = f"[{seq:06d}] {ts} [T{tid}] {tag}{suffix}"
    try:
        with open(_BREADCRUMB_PATH, 'a', buffering=1, encoding='utf-8') as fp:
            fp.write(line + '\n')
            fp.flush()
    except Exception:
        pass
    try:
        if log is not None:
            log.write('[BREADCRUMB] ' + line)
    except Exception:
        pass
    return line


def _get_root_cause(exc: Exception):
    """返回异常链最深层的异常对象。"""
    root = exc
    seen = set()
    while root is not None and id(root) not in seen:
        seen.add(id(root))
        if root.__cause__ is not None:
            root = root.__cause__
        elif root.__context__ is not None:
            root = root.__context__
        else:
            break
    return root


def format_exception_with_root(exc: Exception, where: str = ''):
    """
    返回 (short_message, detail_message)
    short_message: 适合 statusbar
    detail_message: 适合日志与控制台
    """
    root = _get_root_cause(exc)
    header = f"[{where}] " if where else ''
    short_message = f"{header}{type(root).__name__}: {root}"

    chain = []
    cur = exc
    seen = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        chain.append(f"{type(cur).__name__}: {cur}")
        if cur.__cause__ is not None:
            cur = cur.__cause__
        elif cur.__context__ is not None:
            cur = cur.__context__
        else:
            break

    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    detail_message = (
        f"{header}Exception chain (outer -> inner):\n"
        + '\n'.join(chain)
        + f"\n\nRoot cause:\n{type(root).__name__}: {root}\n\nTraceback:\n{tb}"
    )
    return short_message, detail_message


def report_exception(ui=None, log=None, exc: Exception = None, where: str = ''):
    """统一输出异常：状态栏显示根因，日志/控制台打印完整链路与 traceback。"""
    if exc is None:
        return
    short_message, detail_message = format_exception_with_root(exc, where=where)
    try:
        if ui is not None:
            ui.statusbar.showMessage(short_message)
    except Exception:
        pass
    try:
        if log is not None:
            log.write(detail_message)
    except Exception:
        pass
    print(detail_message)



def GenStageWave(one_cycle_samples, Aline_frq, stageSpeed):
    # generate DO waveforms for moving stage
    if stageSpeed > 0.00001:
            time = one_cycle_samples/Aline_frq # time for one bline
            distance = time*stageSpeed # mm to move
            print(distance,'mm')
            steps = distance / DISTANCE * STEPS # how many steps needed to reach that distance
            stride = np.uint16(one_cycle_samples/steps)
            print(steps, stride)
            stagewaveform = np.zeros(one_cycle_samples)
            for ii in range(0,one_cycle_samples,stride):
                stagewaveform[ii] = 1
            return stagewaveform
    else:
        stagewaveform = np.zeros(one_cycle_samples)
        return stagewaveform

def GenStageWave_ramp(distance, AlineTriggers):
    # distance: stage movement per Cscan , mm/s
    # edges: Aline triggers
    # how many motor steps to reach that distance
    steps = (distance/DISTANCE*STEPS)
    # how many Aline triggers per motor step
    clocks_per_motor_step = np.int16(AlineTriggers/steps)
    if clocks_per_motor_step < 2:
        clocks_per_motor_step = 2
    # print('clocks per motor step: ',clocks_per_motor_step)
    # generate stage movement that ramps up and down speed so that motor won't miss signal at beginning and end
    # ramping up: the interval between two steps should be 100 clocks at the beginning, then gradually decrease.vice versa for ramping down
    if np.abs(distance) > 0.01:
        max_interval = 80
    else:
        max_interval = 40
    # the interval for ramping up and down
    ramp_up_interval = np.arange(max_interval,clocks_per_motor_step,-2)
    ramp_down_interval = np.arange(clocks_per_motor_step,max_interval+1,2)
    ramping_steps = np.sum(len(ramp_down_interval)+len(ramp_up_interval)) # number steps used in ramping up and down process
    
    # ramping up waveform generation
    ramp_up_waveform = np.zeros(np.sum(ramp_up_interval))
    if any(ramp_up_waveform):
        ramp_up_waveform[0] = 1
    time_lapse = -1
    for interval in ramp_up_interval:
        time_lapse = time_lapse + interval
        ramp_up_waveform[time_lapse] = 1

    # ramping down waveform generation
    ramp_down_waveform = np.zeros(np.sum(ramp_down_interval))
    if any(ramp_down_waveform):
        ramp_down_waveform[0] = 1
    time_lapse = -1
    for interval in ramp_down_interval:
        time_lapse = time_lapse + interval
        ramp_down_waveform[time_lapse] = 1
        
    # normal speed waveform
    steps_left = steps - ramping_steps
    clocks_left = np.int32(AlineTriggers-len(ramp_down_waveform)-len(ramp_up_waveform))
    stride = np.int16(clocks_left/steps_left)
    if stride < 2:
        stride = 2
    clocks_left = np.int32(steps_left * stride)
    stagewaveform = np.zeros(clocks_left)
    for ii in range(0,clocks_left,stride):
        stagewaveform[ii] = 1
    
    # append all arrays
    DOwaveform = np.append(ramp_up_waveform,stagewaveform)
    DOwaveform = np.append(DOwaveform,ramp_down_waveform)
    if len(DOwaveform) < AlineTriggers:
        DOwaveform = np.append(DOwaveform,np.zeros(AlineTriggers-len(DOwaveform),dtype = np.int16))
    return DOwaveform



def GenMosaic_XYGalvo(Xmin, Xmax, Ymin, Ymax, XFOV, YFOV, overlap=10):
    # all arguments are with units mm
    # overlap is with unit %
    if Xmin > Xmax:
        status = 'Xmin is larger than Xmax, Mosaic generation failed'
        return None, status
    if Ymin > Ymax:
        status = 'Y min is larger than Ymax, Mosaic generation failed'
        return None, status
    if XFOV == 0 or YFOV == 0:
        status = 'FOV set to zero!'
        return None, status
    # get FOV step size
    Xstepsize = XFOV*(1-overlap/100)
    # get how many FOVs in X direction
    Xsteps = np.ceil((Xmax-Xmin)/Xstepsize)
    # get actual X range
    actualX=Xsteps*Xstepsize
    # generate start and stop position in X direction
    # add or subtract a small number to avoid precision loss
    startX=Xmin-(actualX-(Xmax-Xmin))/2
    stopX = Xmax+(actualX-(Xmax-Xmin))/2+0.01
    # generate X positions
    Xpositions = np.arange(startX, stopX, Xstepsize)
    #print(Xpositions)
    
    Ystepsize = YFOV*(1-overlap/100)
    Ysteps = np.ceil((Ymax-Ymin)/Ystepsize)
    actualY=Ysteps*Ystepsize
    
    startY=Ymin-(actualY-(Ymax-Ymin))/2
    stopY = Ymax+(actualY-(Ymax-Ymin))/2+0.01
    
    Ypositions = np.arange(startY, stopY, Ystepsize)
    
    Positions = np.array(np.meshgrid(Xpositions, Ypositions))
    status = 'Mosaic Generation success'
    for ii in range(1,len(Ypositions),2):
        Positions[0,ii,:] = np.flip(Positions[0,ii,:])
    
    return Positions, status




from matplotlib import pyplot as plt
plt.switch_backend('Agg')

def LinePlot(AOwaveform, DOwaveform = None, m=2, M=4):
    # clear content on plot
    plt.cla()
    # plot the new waveform
    plt.plot(range(len(AOwaveform)),AOwaveform,linewidth=2)
    if np.any(DOwaveform):
        plt.plot(range(len(DOwaveform)),(DOwaveform>>3)*np.max(AOwaveform),linewidth=2)
    # plt.ylim(np.min(AOwaveform)-0.2,np.max(AOwaveform)+0.2)
    plt.ylim([m,M])
    plt.xticks(fontsize=15)
    plt.yticks(fontsize=15)
    plt.rcParams['savefig.dpi']=150
    # save plot as jpeg
    plt.savefig('lineplot.jpg')
    # load waveform image
    pixmap = QPixmap('lineplot.jpg')
    return pixmap
    
def RGBImagePlot(matrix1 = [], m=0, M=1):

    matrix1 = np.array(matrix1)
    matrix1[matrix1<m] = m
    matrix1[matrix1>M] = M
    matrix1 = np.uint8((matrix1-m+0.01)/np.abs(M-m+0.1)*255)
    height, width = matrix1.shape

    # Create an empty RGB array
    rgb_array = np.zeros((height, width, 3), dtype=np.uint8)
    
    
    # Assign each channel
    rgb_array[..., 0] = matrix1  # Red channel
    rgb_array[..., 1] = matrix1 # Green channel
    rgb_array[..., 2] = matrix1  # Blue channel
    
    # Convert to QImage
    bytes_per_line = 3 * width
    qimage = QImage(rgb_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
    
    # Convert to QPixmap and display
    pixmap = QPixmap.fromImage(qimage)
    return pixmap

def ScatterPlot(mosaic):
    # clear content on plot
    plt.cla()
    # plot the new waveform
    plt.scatter(mosaic[0],mosaic[1])
    plt.plot(mosaic[0],mosaic[1])
    # plt.ylim(-2,2)
    plt.ylabel('Y stage',fontsize=15)
    plt.xlabel('X stage',fontsize=15)
    plt.xticks(fontsize=15)
    plt.yticks(fontsize=15)
    plt.rcParams['savefig.dpi']=150
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    pixmap = QPixmap()
    pixmap.loadFromData(buf.getvalue())
    buf.close()
    return pixmap

def SharpnessPlot(position_sharpness_dict : dict):
    # clear content on plot
    plt.cla()
    # plot the new waveform
    positions = sorted(position_sharpness_dict.keys())
    sharpness = [position_sharpness_dict[pos] for pos in positions]
    plt.plot(positions, sharpness, marker='o')
    plt.xlabel('Position (mm)', fontsize=15)
    plt.ylabel('Sharpness', fontsize=15)
    plt.xticks(fontsize=15)
    plt.yticks(fontsize=15)
    plt.rcParams['savefig.dpi'] = 150
    # save plot as jpeg
    plt.savefig('sharpness_plot.jpg')
    # load waveform image
    pixmap = QPixmap('sharpness_plot.jpg')
    return pixmap

    
def findchangept(signal, step):
    # python implementation of matlab function findchangepts
    L = len(signal)
    z = np.argmax(signal)
    last = np.min([z+30,L-2])
    signal = signal[1:last]
    L = len(signal)
    residual_error = np.ones(L)*9999999
    for ii in range(2,L-2,step):
        residual_error[ii] = (ii-1)*np.var(signal[0:ii])+(L-ii+1)*np.var(signal[ii+1:L])
    pts = np.argmin(residual_error)
    # plt.plot(residual_error[2:-2])
    return pts

# 自动对焦相关函数
# import cv2
# def Check_image(image):
    
#     # 检查图像属性
#     print("空图像：",np.count_nonzero(image) == 0)
#     print("图像形状 (高度, 宽度, 通道数):", image.shape)
#     print("图像数据类型:", image.dtype)
#     print("图像总大小:", image.size)
#     print("图像是否为连续存储:", image.flags['C_CONTIGUOUS'])
    
    
# def Denoise(img, method = 'MedianBlur', ksize = 7):
#     """
#     Denoise the image using specified method.
#     """

#     if method == 'MedianBlur':
#         return cv2.medianBlur(img, ksize)
#     elif method == 'GaussianBlur':
#         return cv2.GaussianBlur(img, (ksize, ksize), 0)
#     elif method == 'BilateralFilter':
#         return cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
#     else:
#         raise ValueError("Unsupported denoise method: {}".format(method))
        
# def Sharpness_cal(img, method = 'vollath', ksize = 3):
#     """
#     Calculate the sharpness of an image using the Tenengrad method.
#     """
#     if method == 'tenengrad':
#         sobel_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=ksize)
#         sobel_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=ksize)
        
#         gradient_mag = sobel_x**2 + sobel_y**2
            
#         # 返回梯度幅值的总和（Tenengrad值）
#         sharpness = np.sum(gradient_mag)
    
#     elif method == 'vollath':
#         # Vollath's method for sharpness calculation
#         # I(i,j) * I(i+1.j)
#         term1 = img[:-1, :] * img[1:, :]
#         # I(i,j) * I(i,j+1)
#         term2 = img[:-2, :] * img[2:, :]

#         term1_cropped = term1[:-1, :]
#         F4 = np.sum(term1_cropped) - np.sum(term2)
#         return F4
    
# from queue import Queue,Empty

# def clear_queue(q):
#     while not q.empty():
#         try:
#             q.get_nowait()
#         except Empty:
#             break

# def print_queue(q):
#     # 临时取出元素打印，再放回队列
#     temp_list = []
#     while not q.empty():
#         item = q.get()
#         temp_list.append(item)
    
#     # 将元素重新放回队列
#     for item in temp_list:
#         q.put(item)
#     print(f"Current Queue:{temp_list}")
    

        