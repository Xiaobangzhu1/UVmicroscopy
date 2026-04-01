# -*- coding: utf-8 -*-
"""
Main camera control thread using Amcam SDK with PyQt GUI integration.
Includes functionality for live preview, snap image, exposure control,
and mosaic image stitching.
"""
global SIM
# 尝试导入 amcam 模块，如果失败则进入仿真模式（模拟环境）
try:
    import gxipy as gx 
    import initAPI
    SIM = False
except:
    print('no camera driver, using simulation')
    SIM = True

###########################################


############################################
# 通用模块导入
import ctypes, sys, time
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import *
import numpy as np
# from qimage2ndarray import *
from Generaic_functions import *  # 自定义函数集合，可能包含图像处理或转换方法
from libtiff import TIFF
# import qimage2ndarray as qpy
import sys
from PIL import Image
import matplotlib.pyplot as plt

import os

DEBUG_DISABLE_CAMERA = parse_debug_flag('DEBUG_DISABLE_CAMERA', False)

# 主相机线程类，继承自 QThread，用于异步相机操作
class Camera(QThread):
    set_value_signal = pyqtSignal(object, object)
    set_status_signal = pyqtSignal(str)

    def __init__(self):
        #定义Camera类的初始化函数，以及一些通用变量
        super().__init__()
        self.set_value_signal.connect(self._set_value_on_ui)
        self.set_status_signal.connect(self._set_status_on_ui)

        self.hcam = None       # 相机句柄
        self.hcam_fr = None    # 相机外部特征句柄

    @pyqtSlot(object, object)
    def _set_value_on_ui(self, widget, value):
        try:
            widget.setValue(value)
        except Exception:
            pass

    def _set_ui_value(self, widget, value):
        self.set_value_signal.emit(widget, value)

    @pyqtSlot(str)
    def _set_status_on_ui(self, message):
        try:
            self.ui.statusbar.showMessage(message)
        except Exception:
            pass

    def _set_status_message(self, message):
        self.set_status_signal.emit(str(message))

        # 如果不是模拟模式，就初始化真实相机
        
            # self.SetGain()
            #if self.hcam is not None:
                #self.hcam_fr.get_float_feature("ExposureTime").set(100000.0)
                #self.hcam_fr.get_float_feature("Gain").set(12.0)

    def run(self):
        if DEBUG_DISABLE_CAMERA:
            self.log.write('DEBUG_DISABLE_CAMERA=1, camera hardware path disabled')
            write_breadcrumb('CAMERA_DISABLED_BY_FLAG', log=self.log)
        elif not SIM:
            print('initializing camera...')
            write_breadcrumb('CAMERA_INIT_BEGIN', log=self.log)
            self.initCamera()
            write_breadcrumb('CAMERA_INIT_DONE', log=self.log)
        self.QueueOut()

    # 异步任务处理主循环（用于执行 UI 下发的命令）
    def QueueOut(self):
        num = 0
        self.item = self.queue.get()  # 获取消息队列中的第一个任务
        while self.item.action != 'exit':
            try:
                if self.item.action == 'Stream_on':
                    self.Stream_on()
                elif self.item.action == 'Stream_off':
                    self.Stream_off()
                elif self.item.action == 'SetExposure':
                    self.SetExposure()
                elif self.item.action == 'GetExposure':
                    self.GetExposure()
                elif self.item.action == 'AutoExposure':
                    self.AutoExposure()
                elif self.item.action == 'SetGain':
                    self.SetGain()
                elif self.item.action == 'GetGain':
                    self.GetGain()
                elif self.item.action == 'AutoGain':
                    self.AutoGain()
                elif self.item.action == 'FiniteAcquire':
                    self.FiniteAcquire()
                elif self.item.action == 'ContinuousAcquire':
                    self.ContinuousAcquire()
                
                else:
                    message = 'Invalid camera action: ' + self.item.action
                    self._set_status_message(message)
                    self.log.write(message)
            except Exception as error:
                message = "Error occurred, skipping camera action"
                self.log.write(message)
                report_exception(self.ui, self.log, error, where=f"Camera/{self.item.action}")
            num += 1
            self.item = self.queue.get()  # 获取下一个任务
        self.Close()
        print('camera closed')
        self._set_status_message("Camera Thread successfully exited...")
        
        
    
    def FiniteAcquire(self):
        if self.hcam is not None:
            all_images = []
            self.hcam_fr.get_enum_feature("TriggerMode").set("On")
            self.CBackQueue.put(0)
            for i in range(self.ui.Zstack.value()):
                try:
                    buf = self.hcam.data_stream[0].get_image(timeout=10000)
                    img = buf.get_numpy_array()
                    img = np.rot90(img,3)
                    all_images.append(img)
                except:
                    print('timeout error! Camera did not receive trigger')
                
        else:
            all_images = np.uint16(np.random.rand(self.ui.Zstack.value(), self.ui.Width.value(), self.ui.Height.value())*4096)
        # print(np.array(all_images).shape)
        self.CBackQueue.put(np.array(all_images))
            
        # data shape is (Z, Y, X)
    def ContinuousAcquire(self):
        if self.hcam is not None:
            self.hcam_fr.get_enum_feature("TriggerMode").set("Off")
        while self.ui.LiveButton.isChecked():
            if self.hcam is not None:
                all_images = []
                try:
                    buf = self.hcam.data_stream[0].get_image(timeout=10000)
                    img = buf.get_numpy_array()
                    img = np.rot90(img,3)

                    all_images.append(img)
                except:
                    print('timeout error! Camera did not receive trigger')
            else:
                all_images = np.uint16(np.random.rand(self.ui.Zstack.value(), self.ui.Width.value(), self.ui.Height.value())*4096)
            # print(np.array(all_images).shape)
            self.CBackQueue.put(np.array(all_images))
            

    # 初始化并打开真实相机
    def initCamera(self):
        # 已修改完毕
        # 判断是否使用真实相机。如果导入 amcam 成功，camera_sim 为 None，代表使用真实硬件
        if (not SIM) and (not DEBUG_DISABLE_CAMERA):
            write_breadcrumb('CAMERA_DM_CREATE_BEFORE', log=self.log)
            device_manager = gx.DeviceManager()  # 打开设备
            write_breadcrumb('CAMERA_DM_CREATE_AFTER', log=self.log)

            write_breadcrumb('CAMERA_UPDATE_DEV_LIST_BEFORE', log=self.log)
            if device_manager.update_all_device_list()[0] == 0:
                write_breadcrumb('CAMERA_UPDATE_DEV_LIST_AFTER', log=self.log, detail='count=0')
                # 如果没有找到任何相机设备
                print("No camera found")
                self.hcam = None  # 清空相机句柄
            else:
                write_breadcrumb('CAMERA_UPDATE_DEV_LIST_AFTER', log=self.log, detail='count>0')
                write_breadcrumb('CAMERA_OPEN_DEVICE_BEFORE', log=self.log)
                self.hcam = device_manager.open_device_by_index(1)  # 打开设备，返回相机句柄对象
                write_breadcrumb('CAMERA_OPEN_DEVICE_AFTER', log=self.log)
                try:
                    write_breadcrumb('CAMERA_GET_REMOTE_FEATURE_BEFORE', log=self.log)
                    self.hcam_fr = self.hcam.get_remote_device_feature_control() # 返回设备属性对象
                    write_breadcrumb('CAMERA_GET_REMOTE_FEATURE_AFTER', log=self.log)
                    write_breadcrumb('CAMERA_FEATURE_CONFIG_BEGIN', log=self.log)
                    self.hcam_fr.get_enum_feature("GainAuto").set("Off")
                    self.hcam_fr.get_enum_feature("ExposureAuto").set("Off")
                    self.hcam_fr.get_enum_feature("PixelFormat").set(self.ui.PixelFormat.currentText())
                    self.hcam_fr.get_int_feature("Width").set(self.ui.Width.value())
                    self.hcam_fr.get_int_feature("Height").set(self.ui.Height.value())
                    self.hcam_fr.get_int_feature("OffsetX").set(self.ui.Offsetx.value())
                    self.hcam_fr.get_int_feature("OffsetY").set(self.ui.Offsety.value())
                    # Delay startup readback to avoid driver instability window.
                    # self.hcam_fr.get_int_feature("ExposureTime").set(int(self.ui.Exposure.value()*1000.0))
                    # self.hcam_fr.get_int_feature("Gain").set(self.ui.CurrentGain.value())

                    # self.hcam_fr.feature_save("export_config_file.txt")

                    self.hcam_fr.get_enum_feature("TriggerSource").set("Line0")
                    
                    write_breadcrumb('CAMERA_GET_STREAM_FEATURE_BEFORE', log=self.log)
                    self.hcam_s = self.hcam.get_stream(1).get_feature_control()  # 返回流属性对象
                    write_breadcrumb('CAMERA_GET_STREAM_FEATURE_AFTER', log=self.log)
                    self.hcam_s.get_enum_feature("StreamBufferHandlingMode").set("NewestOnly")
                    write_breadcrumb('CAMERA_FEATURE_CONFIG_DONE', log=self.log)
                    print('camera init success')
                except Exception as ex:
                    # 打开失败，打印错误
                    write_breadcrumb('CAMERA_INIT_EXCEPTION', log=self.log, detail=str(ex))
                    print(ex)



    # 拍照功能（一次触发）
    def Stream_on(self):
        if self.hcam is not None:
            self.hcam.stream_on() 

    def Stream_off(self):
        if self.hcam is not None:
            self.hcam.stream_off() 
            

    # 设置曝光时间（从界面获取值）
    def SetExposure(self):
        if self.hcam is not None:
            exposure_ms = float(self.ui.Exposure.value())
            if (not np.isfinite(exposure_ms)) or exposure_ms <= 0:
                message = f'invalid exposure={exposure_ms}, skip set'
                self.log.write(message)
                write_breadcrumb('CAMERA_PARAM_INVALID', log=self.log, detail=message)
                return
            write_breadcrumb('CAMERA_SET_EXPOSURE_BEFORE', log=self.log, detail=f'exposure_ms={exposure_ms}')
            self.hcam_fr.get_float_feature("ExposureTime").set(exposure_ms*1000.0)
            write_breadcrumb('CAMERA_SET_EXPOSURE_AFTER', log=self.log)
            self._set_ui_value(self.ui.CurrentExpo, self.GetExposure())
        
    # 获取曝光时间
    def GetExposure(self):
        if self.hcam is not None:
            write_breadcrumb('CAMERA_GET_EXPOSURE_BEFORE', log=self.log)
            value = np.uint16(self.hcam_fr.get_float_feature("ExposureTime").get()/1000.0)
            write_breadcrumb('CAMERA_GET_EXPOSURE_AFTER', log=self.log, detail=f'value={value}')
            return value

    # 控制自动曝光开关
    def AutoExposure(self):
        if self.hcam is not None:
            if self.ui.AutoExpo.isChecked():
                self.hcam_fr.get_enum_feature("ExposureAuto").set("Continuous")
            else:
                self.hcam_fr.get_enum_feature("ExposureAuto").set("Off")
                self._set_ui_value(self.ui.Exposure, self.ui.CurrentExpo.value())
                
    def SetGain(self):
        if self.hcam is not None:
            gain_value = float(self.ui.Gain.value())
            if not np.isfinite(gain_value):
                message = f'invalid gain={gain_value}, skip set'
                self.log.write(message)
                write_breadcrumb('CAMERA_PARAM_INVALID', log=self.log, detail=message)
                return
            write_breadcrumb('CAMERA_SET_GAIN_BEFORE', log=self.log, detail=f'gain={gain_value}')
            self.hcam_fr.get_float_feature("Gain").set(gain_value)
            write_breadcrumb('CAMERA_SET_GAIN_AFTER', log=self.log)
            self._set_ui_value(self.ui.CurrentGain, self.GetGain())
        
    # 获取曝光时间
    def GetGain(self):
        if self.hcam is not None:
            write_breadcrumb('CAMERA_GET_GAIN_BEFORE', log=self.log)
            value = np.uint8(self.hcam_fr.get_float_feature("Gain").get())
            write_breadcrumb('CAMERA_GET_GAIN_AFTER', log=self.log, detail=f'value={value}')
            return value

    # 控制自动曝光开关
    def AutoGain(self):
        if self.hcam is not None:
            if self.ui.AutoGain.isChecked():
                self.hcam_fr.get_enum_feature("GainAuto").set("Continuous")
            else:
                self.hcam_fr.get_enum_feature("GainAuto").set("Off")
                self._set_ui_value(self.ui.Gain, self.ui.CurrentGain.value())

    
    # 关闭相机并释放资源
    def Close(self):
        if self.hcam is not None:
            self.hcam.close_device()
            self.hcam = None

    
    # def downsample_stack_2x2_zyx(stack):
    #     Z, Y, X = stack.shape
    #     Yeven = Y // 2 * 2
    #     Xeven = X // 2 * 2
    #     stack = stack[:, :Yeven, :Xeven]  # (Z, Yeven, Xeven)
    #     stack_ds = stack.reshape(Z, Yeven//2, 2, Xeven//2, 2).mean(axis=(2, 4))
    #     return stack_ds.astype(np.uint16)