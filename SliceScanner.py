# -*- coding: utf-8 -*-
"""
Created on Wed Oct 16 11:09:15 2024

@author: admin
"""
import sys, os
import threading
import numpy as np
from queue import Queue
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets as QW
import PyQt5.QtCore as qc
from Generaic_functions import LOG, report_exception
from Actions import *
from MainWindow import MainWindow
from Dialogs import  StageDialog

CQueue = Queue()
CBackQueue = Queue()
DOQueue = Queue()
DOBackQueue = Queue()
WeaverQueue = Queue()
DnSQueue = Queue()
DnSBackQueue = Queue()

from Camera import Camera
class CameraThread_2(Camera):
    def __init__(self, ui, log):
        super().__init__()
        self.ui = ui
        self.log = log
        self.queue = CQueue
        # self.DOBackQueue = DOBackQueue
        self.CBackQueue = CBackQueue
        # self.PathQueue = PathQueue
        # self.DnSBackQueue = DnSBackQueue
        
from ThreadDO_150mm import DOThread
class DOThread_2(DOThread):
    def __init__(self, ui, log):
        super().__init__()
        self.ui = ui
        self.queue = DOQueue
        self.DOBackQueue = DOBackQueue
        self.log = log
        self.SIM = False
        

from ThreadWeaver import WeaverThread
class WeaverThread_2(WeaverThread):
    def __init__(self, ui, log):
        super().__init__()
        self.ui = ui
        self.log = log
        self.queue = WeaverQueue
        self.CQueue = CQueue
        self.DOQueue = DOQueue
        self.DOBackQueue = DOBackQueue
        self.CBackQueue = CBackQueue
        self.DnSQueue = DnSQueue
        self.DnSBackQueue = DnSBackQueue
        
# wrap Display and save thread with queues   
from ThreadDnS import DnSThread
class DnSThread_2(DnSThread):
    def __init__(self, ui, log):
        super().__init__()
        self.ui = ui
        self.queue = DnSQueue
        self.log = log
        self.DnSBackQueue = DnSBackQueue
        
class GUI(MainWindow):
    def __init__(self):
        super().__init__()
        self.log = LOG(self.ui)
        sys.excepthook = self._handle_uncaught_exception
        threading.excepthook = self._handle_threading_exception
        self.ui.RunButton.clicked.connect(self.run_task)
        self.ui.PauseButton.clicked.connect(self.PauseFunction)
        
        self.ui.SnapButton.clicked.connect(self.Snap)
        self.ui.LiveButton.clicked.connect(self.Live)
        
        self.ui.Exposure.valueChanged.connect(self.SetExposure)
        self.ui.Gain.valueChanged.connect(self.SetGain)
        self.ui.AutoExpo.stateChanged.connect(self.AutoExposure)
        self.ui.AutoGain.stateChanged.connect(self.AutoGain)

        self.ui.Imagemax.valueChanged.connect(self.Update_contrast_Image)
        self.ui.Imagemin.valueChanged.connect(self.Update_contrast_Image)
        self.ui.Mosaicmax.valueChanged.connect(self.Update_contrast_Mosaic)
        self.ui.Mosaicmin.valueChanged.connect(self.Update_contrast_Mosaic)
        
        self.ui.Xmove2.clicked.connect(self.Xmove2)
        self.ui.Ymove2.clicked.connect(self.Ymove2)
        self.ui.Zmove2.clicked.connect(self.Zmove2)
        self.ui.ZMmove2.clicked.connect(self.ZMmove2)
        self.ui.XUP.clicked.connect(self.XUP)
        self.ui.YUP.clicked.connect(self.YUP)
        self.ui.ZUP.clicked.connect(self.ZUP)
        self.ui.ZMUP.clicked.connect(self.ZMUP)
        self.ui.XDOWN.clicked.connect(self.XDOWN)
        self.ui.YDOWN.clicked.connect(self.YDOWN)
        self.ui.ZDOWN.clicked.connect(self.ZDOWN)
        self.ui.ZMDOWN.clicked.connect(self.ZMDOWN)
        self.ui.UpdateButton.clicked.connect(self.InitStages)
        self.ui.UninitButton.clicked.connect(self.Uninit)
        # self.ui.ZCycleButton.clicked.connect(self.ZCycle)    
        self.ui.SliceDir.clicked.connect(self.SliceDirection)
        self.ui.VibEnabled.clicked.connect(self.Vibratome)
        self.ui.SliceN.valueChanged.connect(self.change_slice_number)
        
        self.ui.LEDA.clicked.connect(self.LightAON)
        self.ui.LEDB.clicked.connect(self.LightBON)
        
        self.ui.PumpA.clicked.connect(self.PumpAON)
        self.ui.PumpB.clicked.connect(self.PumpBON)

        self.weaver_thread = WeaverThread_2(self.ui, self.log)
        self.weaver_thread.start()
        self.DO_thread = DOThread_2(self.ui, self.log)
        self.DO_thread.start()
        self.Camera_thread = CameraThread_2(self.ui, self.log)
        self.Camera_thread.start()
        self.DnS_thread = DnSThread_2(self.ui, self.log)
        self.DnS_thread.start()

    def _handle_uncaught_exception(self, exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        report_exception(self.ui, self.log, exc_value, where='MainThread/Uncaught')

    def _handle_threading_exception(self, args):
        # args: threading.ExceptHookArgs
        if args.exc_value is None:
            return
        report_exception(self.ui, self.log, args.exc_value, where=f'Threading/{args.thread.name}')
        
    def Stop_allThreads(self):
        exit_element=EXIT()
        DnSQueue.put(exit_element)
        CQueue.put(exit_element) 
        DOQueue.put(exit_element) 
        WeaverQueue.put(exit_element) 
    
    def run_task(self):
        if self.ui.ACQMode.currentText() in ['Mosaic','Mosaic+Cut','RptCut','SingleCut']:
            if self.ui.RunButton.isChecked():
                self.ui.RunButton.setText('Stop')
                # for surfScan and SurfSlice, popup a dialog to double check stage position
                if self.ui.ACQMode.currentText() in ['Mosaic','Mosaic+Cut','RptCut','SingleCut']:
                    dlg = StageDialog( self.ui.XPosition.value(), self.ui.YPosition.value(), self.ui.ZPosition.value(),\
                             self.ui.SliceZStart.value()         )
                    dlg.setWindowTitle("double-check stage position")
                    if dlg.exec():
                        an_action = WeaverAction(self.ui.ACQMode.currentText())
                        WeaverQueue.put(an_action)
                    else:
                        # reset RUN button
                        self.ui.RunButton.setChecked(False)
                        self.ui.RunButton.setText('Go')
                        self.ui.PauseButton.setChecked(False)
                        self.ui.PauseButton.setText('Pause')
                        print('user aborted due to stage position incorrect...')
                else:
                    # for other actions, directly do the task
                    an_action = WeaverAction(self.ui.ACQMode.currentText())
                    WeaverQueue.put(an_action)

    def PauseFunction(self):
        if self.ui.PauseButton.isChecked():
            self.ui.PauseButton.setText('Resume')
        else:
            self.ui.PauseButton.setText('Pause')
        
    def Snap(self):
            # for surfScan and SurfSlice, popup a dialog to double check stage position
            an_action = WeaverAction('Snap')
            WeaverQueue.put(an_action)
        
    def Live(self):
        if self.ui.LiveButton.isChecked():
            self.ui.LiveButton.setText('Stop')
            an_action = WeaverAction('Live')
            WeaverQueue.put(an_action)
        else:
            self.ui.LiveButton.setText('Live')
            
    def Vibratome(self):
        if self.ui.VibEnabled.isChecked():
            self.ui.VibEnabled.setText('Stop Vibratome')
            an_action = DOAction('startVibratome')
            DOQueue.put(an_action)
            DOBackQueue.get()
        else:
            self.ui.VibEnabled.setText('Start Vibratome')
            an_action = DOAction('stopVibratome')
            DOQueue.put(an_action)
            DOBackQueue.get()
        
    def SliceDirection(self):
        if self.ui.SliceDir.isChecked():
            self.ui.SliceDir.setText('Forward')
        else:
            self.ui.SliceDir.setText('Backward')
            
    def change_slice_number(self):
        an_action = DnSAction('change_slice_number')
        DnSQueue.put(an_action)
        
    def SetExposure(self):
        an_action = CAction('SetExposure')
        CQueue.put(an_action)
        
    def AutoExposure(self):
        an_action = CAction('AutoExposure')
        CQueue.put(an_action)
        
    def SetGain(self):
        an_action = CAction('SetGain')
        CQueue.put(an_action)
        
    def AutoGain(self):
        an_action = CAction('AutoGain')
        CQueue.put(an_action)
        
    def InitStages(self):
        an_action = DOAction('Init')
        DOQueue.put(an_action)
        DOBackQueue.get()
        
    def Uninit(self):
        an_action = DOAction('Uninit')
        DOQueue.put(an_action)
        DOBackQueue.get()
        
    def Xmove2(self):
        an_action = DOAction('Xmove2')
        DOQueue.put(an_action)
        DOBackQueue.get()
        
    def Ymove2(self):
        an_action = DOAction('Ymove2')
        DOQueue.put(an_action)
        DOBackQueue.get()
        
    def Zmove2(self):
        an_action = DOAction('Zmove2')
        DOQueue.put(an_action)
        DOBackQueue.get()
        
    def ZMmove2(self):
        an_action = DOAction('ZMmove2')
        DOQueue.put(an_action)
        
    def XUP(self):
        an_action = DOAction('XUP')
        DOQueue.put(an_action)
        DOBackQueue.get()
    def YUP(self):
        an_action = DOAction('YUP')
        DOQueue.put(an_action)
        DOBackQueue.get()
    def ZUP(self):
        an_action = DOAction('ZUP')
        DOQueue.put(an_action)
        DOBackQueue.get()
    def ZMUP(self):
        an_action = DOAction('ZMUP')
        DOQueue.put(an_action)
        
    def XDOWN(self):
        an_action = DOAction('XDOWN')
        DOQueue.put(an_action)
        DOBackQueue.get()
    def YDOWN(self):
        an_action = DOAction('YDOWN')
        DOQueue.put(an_action)
        DOBackQueue.get()
    def ZDOWN(self):
        an_action = DOAction('ZDOWN')
        DOQueue.put(an_action)
        DOBackQueue.get()
    def ZMDOWN(self):
        an_action = DOAction('ZMDOWN')
        DOQueue.put(an_action)

    def LightAON(self):
        if self.ui.LEDA.isChecked():
            an_action = DOAction('LightAON')
            DOQueue.put(an_action)
            DOBackQueue.get()
        else:
            an_action = DOAction('LightOFF')
            DOQueue.put(an_action)
        

    def LightBON(self):
        if self.ui.LEDB.isChecked():
            an_action = DOAction('LightBON')
            DOQueue.put(an_action)
            DOBackQueue.get()
        else:
            an_action = DOAction('LightOFF')
            DOQueue.put(an_action)
        
        
    def PumpAON(self):
        if self.ui.PumpA.isChecked():
            an_action = DOAction('PumpAON')
            DOQueue.put(an_action)
            # DOBackQueue.get()
        else:
            an_action = DOAction('PumpOFF')
            DOQueue.put(an_action)
        

    def PumpBON(self):
        if self.ui.PumpB.isChecked():
            an_action = DOAction('PumpBON')
            DOQueue.put(an_action)
            # DOBackQueue.get()
        else:
            an_action = DOAction('PumpOFF')
            DOQueue.put(an_action)
        


    def Update_contrast_Image(self):
        # if not self.ui.RunButton.isChecked():
        an_action = DnSAction('UpdateContrastImage')
        DnSQueue.put(an_action)

    def Update_contrast_Mosaic(self):
        # if not self.ui.RunButton.isChecked():
        an_action = DnSAction('UpdateContrastMosaic')
        DnSQueue.put(an_action)
        
    def closeEvent(self, event):
        print('Exiting all threads')
        self.Stop_allThreads()
        settings = qc.QSettings("config.ini", qc.QSettings.IniFormat)
        self.SaveSettings()
        if self.Camera_thread.isFinished:
            event.accept()
        else:
            event.ignore()
            
if __name__ == '__main__':
    app = QApplication(sys.argv)
    example = GUI()
    example.show()
    sys.exit(app.exec_())
