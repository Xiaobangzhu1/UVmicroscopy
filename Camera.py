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
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import *
import numpy as np
# from qimage2ndarray import *
import traceback
from Generaic_functions import *  # 自定义函数集合，可能包含图像处理或转换方法
from libtiff import TIFF
# import qimage2ndarray as qpy
import sys
from PIL import Image
import matplotlib.pyplot as plt

import os

# 主相机线程类，继承自 QThread，用于异步相机操作
class Camera(QThread):
    def __init__(self):
        #定义Camera类的初始化函数，以及一些通用变量
        super().__init__()

        self.hcam = None       # 相机句柄
        self.hcam_fr = None    # 相机外部特征句柄

        # 如果不是模拟模式，就初始化真实相机
        
            # self.SetGain()
            #if self.hcam is not None:
                #self.hcam_fr.get_float_feature("ExposureTime").set(100000.0)
                #self.hcam_fr.get_float_feature("Gain").set(12.0)

    def run(self):
        if not SIM:
            print('initializing camera...')
            self.initCamera()
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
                    self.ui.statusbar.showMessage(message)
                    self.log.write(message)
            except Exception as error:
                message = "\nError occurred, skipping: " + str(error)
                self.ui.statusbar.showMessage(message)
                self.log.write(message)
                print(traceback.format_exc())
            num += 1
            self.item = self.queue.get()  # 获取下一个任务
        self.Close()
        print('camera closed')
        self.ui.statusbar.showMessage("Camera Thread successfully exited...")
        
        
    
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
        if not SIM:
            device_manager = gx.DeviceManager()  # 打开设备

            if device_manager.update_all_device_list()[0] == 0:
                # 如果没有找到任何相机设备
                print("No camera found")
                self.hcam = None  # 清空相机句柄
            else:
                self.hcam = device_manager.open_device_by_index(1)  # 打开设备，返回相机句柄对象
                try:
                    self.hcam_fr = self.hcam.get_remote_device_feature_control() # 返回设备属性对象
                    self.hcam_fr.get_enum_feature("GainAuto").set("Off")
                    self.hcam_fr.get_enum_feature("ExposureAuto").set("Off")
                    self.hcam_fr.get_enum_feature("PixelFormat").set(self.ui.PixelFormat.currentText())
                    self.hcam_fr.get_int_feature("Width").set(self.ui.Width.value())
                    self.hcam_fr.get_int_feature("Height").set(self.ui.Height.value())
                    self.hcam_fr.get_int_feature("OffsetX").set(self.ui.Offsetx.value())
                    self.hcam_fr.get_int_feature("OffsetY").set(self.ui.Offsety.value())
                    self.ui.CurrentExpo.setValue(self.GetExposure())
                    self.ui.CurrentGain.setValue(self.GetGain())
                    # self.hcam_fr.get_int_feature("ExposureTime").set(int(self.ui.Exposure.value()*1000.0))
                    # self.hcam_fr.get_int_feature("Gain").set(self.ui.CurrentGain.value())

                    # self.hcam_fr.feature_save("export_config_file.txt")

                    self.hcam_fr.get_enum_feature("TriggerSource").set("Line0")
                    
                    self.hcam_s = self.hcam.get_stream(1).get_feature_control()  # 返回流属性对象
                    self.hcam_s.get_enum_feature("StreamBufferHandlingMode").set("NewestOnly")
                    print('camera init success')
                except Exception as ex:
                    # 打开失败，打印错误
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
            self.hcam_fr.get_float_feature("ExposureTime").set(self.ui.Exposure.value()*1000.0)
            self.ui.CurrentExpo.setValue(self.GetExposure())
        
    # 获取曝光时间
    def GetExposure(self):
        if self.hcam is not None:
            return np.uint16(self.hcam_fr.get_float_feature("ExposureTime").get()/1000.0)

    # 控制自动曝光开关
    def AutoExposure(self):
        if self.hcam is not None:
            if self.ui.AutoExpo.isChecked():
                self.hcam_fr.get_enum_feature("ExposureAuto").set("Continuous")
            else:
                self.hcam_fr.get_enum_feature("ExposureAuto").set("Off")
                self.ui.Exposure.setValue(self.ui.CurrentExpo.value())
                
    def SetGain(self):
        if self.hcam is not None:
            self.hcam_fr.get_float_feature("Gain").set(self.ui.Gain.value()*1.0)
            self.ui.CurrentGain.setValue(self.GetGain())
        
    # 获取曝光时间
    def GetGain(self):
        if self.hcam is not None:
            return np.uint8(self.hcam_fr.get_float_feature("Gain").get())

    # 控制自动曝光开关
    def AutoGain(self):
        if self.hcam is not None:
            if self.ui.AutoGain.isChecked():
                self.hcam_fr.get_enum_feature("GainAuto").set("Continuous")
            else:
                self.hcam_fr.get_enum_feature("GainAuto").set("Off")
                self.ui.Gain.setValue(self.ui.CurrentGain.value())

    
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