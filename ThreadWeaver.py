# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 11:10:17 2024

@author: admin
"""

#################################################################
# THIS KING THREAD IS USING ART8912, WHICH IS MASTER AND the DO board WILL BE SLAVE
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QDialog
import time
import numpy as np
from Generaic_functions import *
from Actions import *
import os
import datetime
# import cv2
# import Requester
# from tqdm import tqdm
from matplotlib import pyplot as plt

class WeaverThread(QThread):
    request_status = pyqtSignal(str)
    request_set_value = pyqtSignal(str, float)
    request_set_checked = pyqtSignal(str, bool)
    request_set_text = pyqtSignal(str, str)
    request_set_enabled = pyqtSignal(str, bool)
    request_mosaic_preview = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        
        self.mosaic = None
        self.exit_message = 'weaver thread successfully exited'
        self.request_status.connect(self._apply_status_message)
        self.request_set_value.connect(self._apply_set_value)
        self.request_set_checked.connect(self._apply_set_checked)
        self.request_set_text.connect(self._apply_set_text)
        self.request_set_enabled.connect(self._apply_set_enabled)
        self.request_mosaic_preview.connect(self._apply_mosaic_preview)

    @pyqtSlot(str)
    def _apply_status_message(self, message):
        try:
            self.ui.statusbar.showMessage(str(message))
        except Exception:
            pass

    @pyqtSlot(str, float)
    def _apply_set_value(self, widget_name, value):
        widget = getattr(self.ui, widget_name, None)
        if widget is not None:
            try:
                widget.setValue(float(value))
            except Exception:
                pass

    @pyqtSlot(str, bool)
    def _apply_set_checked(self, widget_name, checked):
        widget = getattr(self.ui, widget_name, None)
        if widget is not None:
            try:
                widget.setChecked(bool(checked))
            except Exception:
                pass

    @pyqtSlot(str, str)
    def _apply_set_text(self, widget_name, text):
        widget = getattr(self.ui, widget_name, None)
        if widget is not None:
            try:
                widget.setText(str(text))
            except Exception:
                pass

    @pyqtSlot(str, bool)
    def _apply_set_enabled(self, widget_name, enabled):
        widget = getattr(self.ui, widget_name, None)
        if widget is not None:
            try:
                widget.setEnabled(bool(enabled))
            except Exception:
                pass

    @pyqtSlot(object)
    def _apply_mosaic_preview(self, mosaic_pattern_flattern):
        try:
            pixmap = ScatterPlot(mosaic_pattern_flattern)
            self.ui.MosaicLabel.setPixmap(pixmap)
        except Exception:
            pass

    def _set_status_message(self, message):
        self.request_status.emit(str(message))

    def _set_ui_value(self, widget_name, value):
        self.request_set_value.emit(str(widget_name), float(value))

    def _set_ui_checked(self, widget_name, checked):
        self.request_set_checked.emit(str(widget_name), bool(checked))

    def _set_ui_text(self, widget_name, text):
        self.request_set_text.emit(str(widget_name), str(text))

    def _set_ui_enabled(self, widget_name, enabled):
        self.request_set_enabled.emit(str(widget_name), bool(enabled))

    def _refresh_mosaic_preview(self, mosaic_pattern_flattern):
        self.request_mosaic_preview.emit(mosaic_pattern_flattern)

    def _wait_do_back(self, context=''):
        write_breadcrumb('WEAVER_WAIT_DO_BACK_BEGIN', log=self.log, detail=context)
        start = time.time()
        result = self.DOBackQueue.get()
        dt_ms = int((time.time() - start) * 1000)
        write_breadcrumb('WEAVER_WAIT_DO_BACK_DONE', log=self.log, detail=f'{context}; dt_ms={dt_ms}; result={result}')
        return result

    def _wait_c_back(self, context=''):
        write_breadcrumb('WEAVER_WAIT_C_BACK_BEGIN', log=self.log, detail=context)
        start = time.time()
        result = self.CBackQueue.get()
        dt_ms = int((time.time() - start) * 1000)
        write_breadcrumb('WEAVER_WAIT_C_BACK_DONE', log=self.log, detail=f'{context}; dt_ms={dt_ms}')
        return result
        
    def run(self):
        # self.InitMemory()
        self.QueueOut()
        
    def QueueOut(self):
        self.item = self.queue.get()
        while self.item.action != 'exit':
            self._set_status_message('Weaver thread is doing: '+self.item.action)
            print('Weaver thread is doing: '+self.item.action)
            try:
                if self.item.action == 'Snap':
                    message = self.Snap()
                    self._set_status_message(message)
                elif self.item.action == 'Live':
                    message = self.Live()
                    self._set_status_message(message)
                elif self.item.action in ['Mosaic']:
                    # make directories
                    if not os.path.exists(self.ui.DIR.toPlainText()+'/mosaic'):
                        os.mkdir(self.ui.DIR.toPlainText()+'/mosaic')
                    if not os.path.exists(self.ui.DIR_remote.toPlainText()+'/mosaic'):
                        os.mkdir(self.ui.DIR_remote.toPlainText()+'/mosaic')
                    if self.ui.PreMosaic.isChecked():
                        self.PreMosaic()
                    else:
                        self.LoadTileFlag()
                    message = self.Mosaic()
                    print(self.tile_flag)
                    an_action = DnSAction('WriteAgar', data = self.tile_flag, args = [self.total_Y, self.total_X]) # data in Memory[memoryLoc]
                    self.DnSQueue.put(an_action)
                    self._set_status_message(message)
                    # self.ui.PrintOut.append(message)
                    self.log.write(message)
                    self._set_ui_checked('PauseButton', False)
                    self._set_ui_text('PauseButton', 'Pause')
                    self._set_ui_checked('RunButton', False)
                    self._set_ui_text('RunButton', 'Go')
                elif self.item.action == 'Mosaic+Cut':
                    # make directories
                    if not os.path.exists(self.ui.DIR.toPlainText()+'/mosaic'):
                        os.mkdir(self.ui.DIR.toPlainText()+'/mosaic')
                    # if not os.path.exists(self.ui.DIR.toPlainText()+'/surf'):
                    #     os.mkdir(self.ui.DIR.toPlainText()+'/surf')
                    # if not os.path.exists(self.ui.DIR.toPlainText()+'/fitting'):
                    #     os.mkdir(self.ui.DIR.toPlainText()+'/fitting')
                    # disable partial vibratome settings to avoid parameter change during experiment
                    self._set_ui_enabled('SMPthickness', False)
                    self._set_ui_enabled('SliceZDepth', False)
                    # self.ui.ImageZDepth.setEnabled(False)
                    self._set_ui_enabled('SMPthickness', False)
                    if self.ui.PreMosaic.isChecked():
                        self.PreMosaic()
                    else:
                        self.LoadTileFlag()
                    message = self.OneImagePerCut()
                    self._set_status_message(message)
                    # self.ui.PrintOut.append(message)
                    self.log.write(message)
                    # re-enable settings
                    self._set_ui_enabled('SMPthickness', True)
                    self._set_ui_enabled('SliceZDepth', True)
                    # self.ui.ImageZDepth.setEnabled(True)
                    self._set_ui_enabled('SMPthickness', True)
                elif self.item.action == 'SingleCut':
                    message = self.SingleCut(self.ui.SliceZStart.value())
                    self._set_status_message(message)
                    # self.ui.PrintOut.append(message)
                    self.log.write(message)

                elif self.item.action == 'RptCut':
                    self._set_ui_enabled('SMPthickness', False)
                    self._set_ui_enabled('SliceZDepth', False)
                    # self.ui.ImageZDepth.setEnabled(False)
                    self._set_ui_enabled('SMPthickness', False)
                    message = self.RptCut(self.ui.SliceZStart.value(), np.uint16(self.ui.SMPthickness.value()*1000/self.ui.SliceZDepth.value()))
                    self._set_status_message(message)
                    # self.ui.PrintOut.append(message)
                    self.log.write(message)
                    self._set_ui_enabled('SMPthickness', True)
                    self._set_ui_enabled('SliceZDepth', True)
                    # self.ui.ImageZDepth.setEnabled(True)
                    self._set_ui_enabled('SMPthickness', True)
                    # self.ui.statusbar.showMessage(status)

            except Exception as error:
                message = "An error occurred, skip the acquisition action"
                self.log.write(message)
                report_exception(self.ui, self.log, error, where=f"WeaverThread/{self.item.action}")
            # reset RUN button
            self._set_ui_checked('RunButton', False)
            self._set_ui_text('RunButton', 'Go')
            self._set_ui_checked('PauseButton', False)
            self._set_ui_text('PauseButton', 'Pause')
            self.item = self.queue.get()
            
        self._set_status_message(self.exit_message)
            
            
    def Snap(self):
        # flush image queue
        while self.CQueue.qsize()>1:
            self.CQueue.get()
        an_action = CAction('Stream_on')
        self.CQueue.put(an_action)
        an_action = DOAction('LightON')
        self.DOQueue.put(an_action)
        self._wait_do_back('Snap/LightON')
        an_action = DOAction('ConfigZstack')
        self.DOQueue.put(an_action)
        an_action = CAction('FiniteAcquire')
        self.CQueue.put(an_action)
        self._wait_c_back('Snap/FiniteAcquire-ready')
        an_action = DOAction('Zstack')
        self.DOQueue.put(an_action)
        images = self._wait_c_back('Snap/Zstack-images')
        an_action = DOAction('LightOFF')
        self.DOQueue.put(an_action)
        an_action = CAction('Stream_off')
        self.CQueue.put(an_action)
        an_action = DOAction('StopCloseZstack')
        self.DOQueue.put(an_action)
        an_action = DnSAction('Snap', images) # data in Memory[memoryLoc]
        self.DnSQueue.put(an_action)
        message = 'Snap succesfully finished'
        return message
        

    def Live(self):
        # flush image queue
        Zstack = self.ui.Zstack.value()
        self._set_ui_value('Zstack', 1)
        while self.CQueue.qsize()>1:
            self.CQueue.get()
        an_action = CAction('Stream_on')
        self.CQueue.put(an_action)
        an_action = DOAction('LightON')
        self.DOQueue.put(an_action)
        self._wait_do_back('Live/LightON')
        an_action = CAction('ContinuousAcquire')
        self.CQueue.put(an_action)
        
        while self.ui.LiveButton.isChecked():
            images = self._wait_c_back('Live/images')
            an_action = DnSAction('Snap', images) # data in Memory[memoryLoc]
            self.DnSQueue.put(an_action)
        an_action = DOAction('LightOFF')
        self.DOQueue.put(an_action)
        an_action = CAction('Stream_off')
        self.CQueue.put(an_action)
        self._set_ui_value('Zstack', Zstack)
        message = 'Live succesfully finished'
        return message
        
    def PreMosaic(self):
        self.Mosaic_pattern, status = GenMosaic_XYGalvo(self.ui.XStart.value(),\
                                        self.ui.XStop.value(),\
                                        self.ui.YStart.value(),\
                                        self.ui.YStop.value(),\
                                        self.ui.XFOV.value(),\
                                        self.ui.YFOV.value(),\
                                        self.ui.Overlap.value())
        if self.Mosaic_pattern is None:
            self._set_status_message(status)
            self.log.write(status)
            return
        # get total number of strips, i.e.，xstage positions
        self.total_Y = self.Mosaic_pattern.shape[1]
        self.total_X = self.Mosaic_pattern.shape[2]

        self.Mosaic_pattern_flattern = self.Mosaic_pattern.reshape(2,self.total_X*self.total_Y)
        # init sample surface plot window
        args = [[0,0],[self.total_X, self.total_Y]]
        an_action = DnSAction('Init_Mosaic', args = args) # data in Memory[memoryLoc]
        self.DnSQueue.put(an_action)
        self.tile_flag = np.ones([self.total_Y, self.total_X])
        
    def LoadTileFlag(self):
        filepath = self.ui.Tile_DIR.text()
        if os.path.isfile(filepath):
            import re
            filename = os.path.basename(filepath)
            numbs = re.findall(r'\d+',filename)
            # print(numbs)
            xx = np.uint8(numbs[1])
            yy = np.uint8(numbs[2])
            
            # arr = np.fromfile(self.ui.Tile_DIR.text(), dtype=np.uint8)
            # total = xx * yy
            
            # if arr.size < total:
            #     print("tile flag file too small, ignore this file.")
            #     return 'Error'

            # if arr.size == total:
            #     self.tile_flag = arr.reshape((xx, yy))
            # else:
            #     arr2d = arr[:total].reshape((xx, yy))
            #     self.tile_flag = arr2d
            self.tile_flag = np.fromfile(filepath, dtype=np.uint8)
            # print(self.tile_flag.shape, self.tile_flag)
            self.tile_flag = self.tile_flag.reshape([yy,xx])
            # print(self.tile_flag.shape)

        else:
            print('tile flag file not found')
            return 'Error'
        self.Mosaic_pattern, status = GenMosaic_XYGalvo(self.ui.XStart.value(),\
                                        self.ui.XStop.value(),\
                                        self.ui.YStart.value(),\
                                        self.ui.YStop.value(),\
                                        self.ui.XFOV.value(),\
                                        self.ui.YFOV.value(),\
                                        self.ui.Overlap.value())
        if self.Mosaic_pattern is None:
            self._set_status_message(status)
            self.log.write(status)
            return 'Error'
        # get total number of strips, i.e.，xstage positions
        self.total_Y = self.Mosaic_pattern.shape[1]
        self.total_X = self.Mosaic_pattern.shape[2]

        self.Mosaic_pattern_flattern = self.Mosaic_pattern.reshape(2,self.total_X*self.total_Y)
        # init sample surface plot window
        args = [[0,0],[self.total_X, self.total_Y]]
        an_action = DnSAction('Init_Mosaic', args = args) # data in Memory[memoryLoc]
        self.DnSQueue.put(an_action)
            
        #     self.tile_flag = np.fromfile(self.ui.Tile_DIR.text(), dtype=np.uint8).reshape([xx,yy])
        #     print(self.tile_flag)
        #     return None
        # else:
        #     print('tile flag file not found')
        #     return 'Error'
        # # print(self.tile_flag.shape)
        

    def Mosaic(self):
        # slice number increase, tile number restart from 1
        args = [[0,0],[self.total_X, self.total_Y]]
        an_action = DnSAction('Init_Mosaic', args = args) # data in Memory[memoryLoc]
        self.DnSQueue.put(an_action)
        an_action = DnSAction('WriteAgar', data = self.tile_flag, args = [self.total_Y, self.total_X]) # data in Memory[memoryLoc]
        self.DnSQueue.put(an_action)
        ############################################################# Iterate through strips for one Mosaic
        an_action = DOAction('ConfigZstack')
        self.DOQueue.put(an_action)
        an_action = CAction('Stream_on')
        self.CQueue.put(an_action)
        # print('totalY:',self.total_Y, 'totalX:', self.total_X, self.tile_flag.shape)
        for yy in range(self.total_Y):
            for xx in range(self.total_X):
                if self.ui.RunButton.isChecked() and self.tile_flag[yy][xx] > 0:
                    
                    # stage move to start XYZ position
                    self._set_ui_value('XPosition', self.Mosaic_pattern[0,yy,xx])
                    an_action = DOAction('Xmove2')
                    self.DOQueue.put(an_action)
                    self._wait_do_back(f'Mosaic/Xmove2/yy={yy},xx={xx}')
                    self._set_ui_value('YPosition', self.Mosaic_pattern[1,yy,xx])
                    an_action = DOAction('Ymove2')
                    self.DOQueue.put(an_action)
                    self._wait_do_back(f'Mosaic/Ymove2/yy={yy},xx={xx}')
       
                    
                    an_action = DOAction('LightON')
                    self.DOQueue.put(an_action)
                    self._wait_do_back(f'Mosaic/LightON/yy={yy},xx={xx}')
                    an_action = CAction('FiniteAcquire')
                    self.CQueue.put(an_action)
                    self._wait_c_back(f'Mosaic/FiniteAcquire-ready/yy={yy},xx={xx}')
                    an_action = DOAction('Zstack')
                    self.DOQueue.put(an_action)
                    images = self._wait_c_back(f'Mosaic/Zstack-images/yy={yy},xx={xx}')
                    
                    an_action = DOAction('LightOFF')
                    self.DOQueue.put(an_action)
                    
                    
                    # update mosaic pattern
                    self.Mosaic_pattern_flattern = self.Mosaic_pattern_flattern[:,1:]
                    self._refresh_mosaic_preview(self.Mosaic_pattern_flattern)
                    # print([[xx,yy],[self.total_X, self.total_Y]])
                    an_action = DnSAction('Display_Mosaic', data = images, args = [[xx,yy],[self.total_X, self.total_Y]]) 
                    self.DnSQueue.put(an_action)  
                    ############################ check user input
                    if self.ui.PauseButton.isChecked():
                        while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                            time.sleep(0.5)
                            
        an_action = CAction('Stream_off')
        self.CQueue.put(an_action)               
        an_action = DnSAction('Save_Mosaic') 
        self.DnSQueue.put(an_action)
        an_action = DOAction('StopCloseZstack')
        self.DOQueue.put(an_action)
        an_action = DnSAction('restart_tilenum') # data in Memory[memoryLoc]
        self.DnSQueue.put(an_action)
        self.Re_evaluate_mosaic()
        # Requester.send_wechat(f"Mosaic finished, total {total_X*total_Y} tiles, saved {self.saved} tiles.",title='UVSliceScanner Finished')
        return 'Mosaic successfully finished...'

    def Re_evaluate_mosaic(self):
        # evaluate the previous mosaic figure, remove empty tiles, and extend tissue boundary
        # self.surf = np.flip(np.rot90(self.DnSBackQueue.get()),0)
        self.surf = self.DnSBackQueue.get()
        plt.figure()
        plt.subplot(2,1,1)
        plt.imshow(self.surf,vmin=0,vmax=5550)
        # segment tissue area using threshold
        mask = np.float32(self.surf>self.ui.AgarValue.value())
        plt.subplot(2,1,2)
        plt.imshow(mask)
        plt.show()
        
        # for snake-scanning of mosaic area, flip odd rows of tile_flag to make it zig-zag scan
        [xx,yy] = np.shape(self.tile_flag)
        # print('xx:', xx, 'yy:',yy)
        self.tile_flag_rearange = self.tile_flag.copy()
        # plt.figure()
        # plt.subplot(1,3,1)
        # plt.imshow(self.tile_flag)
        
        for ii in range(xx):
            tmp = self.tile_flag_rearange[ii,:]
            if np.mod(ii,2) == 0:
                self.tile_flag_rearange[ii,:] = tmp
            else:
                self.tile_flag_rearange[ii,:] = tmp[::-1]
        # plt.subplot(1,3,2)
        # plt.imshow(self.tile_flag_rearange)
        # self.tile_flag_rearange = np.flip(self.tile_flag_rearange)

        # plt.subplot(1,3,3)
        # plt.imshow(self.tile_flag_rearange)
        # plt.show()
        # get tile downsampled size
        scale = self.ui.scale.value()
        xxlength = self.ui.Width.value()//scale//2
        yylength = self.ui.Height.value()//scale//2
        # total tissue tiles in the last mosaic
        Agartiles_pre = np.sum(np.float32(self.tile_flag))
        # remove empty tiles
        for ii in range(xx):
            for jj in range(yy):
                maskij = mask[ii*xxlength:(ii+1)*xxlength, jj*yylength:(jj+1)*yylength]
                if np.sum(maskij)<xxlength*yylength//100:
                    self.tile_flag_rearange[ii,jj]=0
                    
        # add boundary tiles
        for ii in range(1,xx-1):
            for jj in range(1,yy-1):
                maskij = mask[ii*xxlength:(ii+1)*xxlength, jj*yylength:(jj+1)*yylength]
                
                if np.sum(maskij[0:xxlength//4,:])>300:
                    self.tile_flag_rearange[ii-1,jj]=1
                if np.sum(maskij[-xxlength//4:,:])>300:
                    self.tile_flag_rearange[ii+1,jj]=1
                if np.sum(maskij[:,0:yylength//4])>300:
                    self.tile_flag_rearange[ii,jj-1]=1
                if np.sum(maskij[:,-yylength//4:])>300:
                    self.tile_flag_rearange[ii,jj+1]=1
        plt.figure()
        # plt.subplot(1,3,1)
        plt.imshow(self.tile_flag_rearange)
        plt.show()
        self.tile_flag_rearange = np.flip(self.tile_flag_rearange)
        # plt.subplot(1,3,2)
        # plt.imshow(self.tile_flag_rearange)
        for ii in range(xx):
            tmp = self.tile_flag_rearange[ii,:]
            if np.mod(ii,2) == 0:
                self.tile_flag_rearange[ii,:] = tmp
            else:
                self.tile_flag_rearange[ii,:] = tmp[::-1]
        
        self.tile_flag = self.tile_flag_rearange
        # plt.subplot(1,3,3)
        # plt.imshow(self.tile_flag)
        # plt.show()
        # pause if large decrease of tiles
        # print(Agartiles_pre, np.sum(self.tile_flag), np.float32(Agartiles_pre) - np.float32(np.sum(self.tile_flag)))
        if np.float32(Agartiles_pre) - np.sum(np.float32(self.tile_flag))>30:
            print('large loss of tiles detected, manual check if light is blocked...')
            self._set_ui_checked('PauseButton', True)
            self._set_ui_text('PauseButton', 'Resume')
            
    
    def OneImagePerCut(self):
        completion_flag = True
        total_slices = np.uint16(self.ui.SMPthickness.value()*1000//self.ui.SliceZDepth.value())
        print('\n total_slices: ', total_slices,'\n')
        self.log.write('total_slices: '+ str(total_slices))
        for ii in range(total_slices):
            # cut one slice
            message = self.SingleCut(self.ui.SliceZStart.value()+ii*self.ui.SliceZDepth.value()/1000.0)
            print(message)
            if message != 'Slice success':
                return message
            message = '\nCUT HEIGHT:'+str(self.ui.SliceZStart.value()+ii*self.ui.SliceZDepth.value()/1000.0)+'\n'
            print(message)
            self.log.write(message)
            ##################################################
            if self.ui.PauseButton.isChecked():
                while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                    time.sleep(0.5)
            if not self.ui.RunButton.isChecked():
                return 'user stopped service'
            
            # move to X Y Z
            self._set_ui_value('XPosition', self.ui.XStart.value())
            self._set_ui_value('YPosition', self.ui.YStart.value())
            an_action = DOAction('Xmove2')
            self.DOQueue.put(an_action)
            self.DOBackQueue.get()
            ##################################################
            if self.ui.PauseButton.isChecked():
                while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                    time.sleep(0.5)
            if not self.ui.RunButton.isChecked():
                return 'user stopped service'
            ########################################################
            an_action = DOAction('Ymove2')
            self.DOQueue.put(an_action)
            self.DOBackQueue.get()
            ##################################################
            if self.ui.PauseButton.isChecked():
                while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                    time.sleep(0.5)
            if not self.ui.RunButton.isChecked():
                return 'user stopped service'
            #Pump
            an_action = DOAction('PumpOFF')
            self.DOQueue.put(an_action)
            
            message = self.Mosaic()
            if self.ui.PauseButton.isChecked():
                while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                    time.sleep(0.5)
            if not self.ui.RunButton.isChecked():
                return 'user stopped service'
        
            completion = ii/total_slices
            
            if completion >= 0.5 and completion_flag:
                message = f'Mosaic + Cut {completion*100}%'
                # Requester.send_wechat(message)
                completion_flag = False
        # LAST CUT 
        message = self.SingleCut(self.ui.SliceZStart.value()+(ii+1)*self.ui.SliceZDepth.value()/1000.0)
        # Requester.send_wechat(message)
        if message != 'Slice success':
            return message
        return 'Mosaic+Cut successful...'
        
    
    def SingleCut(self, zpos):

        # go to start Y
        self._set_ui_value('YPosition', self.ui.SliceY.value())
        an_action = DOAction('Ymove2')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        
        
        ##################################################
        if self.ui.PauseButton.isChecked():
            while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                time.sleep(0.5)
        if not self.ui.RunButton.isChecked():
            return 'user stopped service'
        
        # go to start X
       
        self._set_ui_value('XPosition', self.ui.SliceX.value())
        an_action = DOAction('Xmove2')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        
        ##################################################
        if self.ui.PauseButton.isChecked():
            while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                time.sleep(0.5)
        if not self.ui.RunButton.isChecked():
            return 'user stopped service'
        
        # start vibratome
        self._set_ui_text('VibEnabled', 'Stop Vibratome')
        self._set_ui_checked('VibEnabled', True)
        an_action = DOAction('startVibratome')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        
        # go to start Z
        self._set_ui_value('ZPosition', zpos)
        an_action = DOAction('Zmove2')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        
        
        ##################################################
        ##################################################
        if self.ui.PauseButton.isChecked():
            while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                time.sleep(0.5)
        if not self.ui.RunButton.isChecked():
            # stop vibratome
            self._set_ui_text('VibEnabled', 'Start Vibratome')
            self._set_ui_checked('VibEnabled', False)
            an_action = DOAction('stopVibratome')
            self.DOQueue.put(an_action)
            self.DOBackQueue.get()
            return 'user stopped service'

        ########################################################
        # slicing
       
        if self.ui.SliceDir.isChecked():
            sign = 1
        else:
            sign = -1
        self._set_ui_value('YPosition', self.ui.SliceLength.value()*sign+self.ui.YPosition.value())
        speed = self.ui.YSpeed.value()
        print(speed)
        self._set_ui_value('YSpeed', self.ui.SliceSpeed.value())
        print(self.ui.YSpeed.value())
        an_action = DOAction('Ymove2')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        self._set_ui_value('YSpeed', speed)
        # stop vibratome
        self._set_ui_text('VibEnabled', 'Start Vibratome')
        self._set_ui_checked('VibEnabled', False)
        an_action = DOAction('stopVibratome')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        return 'Slice success'
        
    def RptCut(self, start_height, cuts):
        # # move to defined zero
        # self.ui.ZPosition.setValue(self.ui.definedZero.value())
        # an_action = DOAction('Zmove2')
        # self.DOQueue.put(an_action)
        # self.DOBackQueue.get()
        # ##################################################
        # interrupt = self.check_interrupt()
        # if interrupt == 'Stop':
        #     message = 'user stopped acquisition...'
        #     return message
        
        # go to start Y
        self._set_ui_value('YPosition', self.ui.SliceY.value())
        an_action = DOAction('Ymove2')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        ##################################################
        if self.ui.PauseButton.isChecked():
            while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                time.sleep(0.5)
        if not self.ui.RunButton.isChecked():
            return 'user stopped service'
        # ########################################################
        ########################################################
        # go to start X
        self._set_ui_value('XPosition', self.ui.SliceX.value())
        an_action = DOAction('Xmove2')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        ##################################################
        if self.ui.PauseButton.isChecked():
            while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                time.sleep(0.5)
        if not self.ui.RunButton.isChecked():
            return 'user stopped service'
        ########################################################
        
        # # go to start Z
        # self.ui.ZPosition.setValue(start_height)
        # an_action = DOAction('Zmove2')
        # self.DOQueue.put(an_action)
        # self.DOBackQueue.get()
        # ##################################################
        # interrupt = self.check_interrupt()
        # if interrupt == 'Stop':
        #     message = 'user stopped acquisition...'
        #     return message
        # ########################################################
        # slicing
        # start vibratome
        self._set_ui_text('VibEnabled', 'Stop Vibratome')
        self._set_ui_checked('VibEnabled', True)
        an_action = DOAction('startVibratome')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        for ii in range(cuts):
            # Z stage move up
            self._set_ui_value('ZPosition', start_height+self.ui.SliceZDepth.value()/1000.0*ii)
            an_action = DOAction('Zmove2')
            self.DOQueue.put(an_action)
            self.DOBackQueue.get()
            # Move Y stage slowly to cut
            if self.ui.SliceDir.isChecked():
                sign = 1
            else:
                sign = -1
            self._set_ui_value('YPosition', self.ui.SliceLength.value()*sign+self.ui.YPosition.value())
            speed = self.ui.YSpeed.value()
            self._set_ui_value('YSpeed', self.ui.SliceSpeed.value())
            an_action = DOAction('Ymove2')
            self.DOQueue.put(an_action)
            self.DOBackQueue.get()
            self._set_ui_value('YSpeed', speed)
            
            if self.ui.PauseButton.isChecked():
                while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                    time.sleep(0.5)
            if not self.ui.RunButton.isChecked():
                message = 'user stopped acquisition...'
                # stop vibratome
                self._set_ui_text('VibEnabled', 'Start Vibratome')
                self._set_ui_checked('VibEnabled', False)
                an_action = DOAction('stopVibratome')
                self.DOQueue.put(an_action)
                self.DOBackQueue.get()
                return message
                
            # move Y stage back to position
            self._set_ui_value('YPosition', self.ui.SliceY.value())
            an_action = DOAction('Ymove2')
            self.DOQueue.put(an_action)
            self.DOBackQueue.get()
            
            if self.ui.PauseButton.isChecked():
                while self.ui.PauseButton.isChecked() and self.ui.RunButton.isChecked():
                    time.sleep(0.5)
            if not self.ui.RunButton.isChecked():
                message = 'user stopped acquisition...'
                # stop vibratome
                self._set_ui_text('VibEnabled', 'Start Vibratome')
                self._set_ui_checked('VibEnabled', False)
                an_action = DOAction('stopVibratome')
                self.DOQueue.put(an_action)
                self.DOBackQueue.get()
                return message
            


        # stop vibratome
        self._set_ui_text('VibEnabled', 'Start Vibratome')
        self._set_ui_checked('VibEnabled', False)
        an_action = DOAction('stopVibratome')
        self.DOQueue.put(an_action)
        self.DOBackQueue.get()
        self._set_ui_value('SliceZStart', self.ui.ZPosition.value())
        return 'Slice success'