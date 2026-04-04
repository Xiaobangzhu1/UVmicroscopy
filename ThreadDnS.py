
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 12 18:26:44 2023

@author: admin
"""

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from Generaic_functions import RGBImagePlot, report_exception
import numpy as np
import matplotlib.pyplot as plt
import datetime
import os
from scipy import ndimage
from libtiff import TIFF
import time

class DnSThread(QThread):
    request_status = pyqtSignal(str)
    request_image_refresh = pyqtSignal(object)
    request_mosaic_refresh = pyqtSignal(object)
    request_value_set = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self.SampleMosaic= []
        self.sliceNum = 1
        self.tileNum = 1
        self.SnapNum = 1
        self.totalTiles = 0
        self.display_actions = 0
        self.request_status.connect(self._apply_status_message)
        self.request_image_refresh.connect(self._apply_image_refresh)
        self.request_mosaic_refresh.connect(self._apply_mosaic_refresh)
        self.request_value_set.connect(self._apply_value_set)

    @pyqtSlot(str)
    def _apply_status_message(self, message):
        try:
            self.ui.statusbar.showMessage(str(message))
        except Exception:
            pass

    @pyqtSlot(object)
    def _apply_image_refresh(self, image):
        try:
            if image is None:
                return
            scale = max(1, int(self.ui.scale.value()))
            pixmap = RGBImagePlot(
                matrix1=np.float32(image[::scale, ::scale]),
                m=self.ui.Imagemin.value(),
                M=self.ui.Imagemax.value(),
            )
            self.ui.Image.setPixmap(pixmap)
        except Exception:
            pass

    @pyqtSlot(object)
    def _apply_mosaic_refresh(self, mosaic):
        try:
            if mosaic is None:
                return
            pixmap = RGBImagePlot(
                matrix1=mosaic,
                m=self.ui.Mosaicmin.value(),
                M=self.ui.Mosaicmax.value(),
            )
            self.ui.Mosaic.setPixmap(pixmap)
        except Exception:
            pass

    @pyqtSlot(str, object)
    def _apply_value_set(self, widget_name, value):
        try:
            widget = getattr(self.ui, widget_name, None)
            if widget is not None:
                widget.setValue(value)
        except Exception:
            pass

    def _set_status_message(self, message):
        self.request_status.emit(str(message))

    def _refresh_image_view(self, image):
        self.request_image_refresh.emit(image)

    def _refresh_mosaic_view(self, mosaic):
        self.request_mosaic_refresh.emit(mosaic)

    def _set_ui_value(self, widget_name, value):
        self.request_value_set.emit(str(widget_name), value)
        
    def run(self):
        self.sliceNum = self.ui.SliceN.value()
        self.Imagemax = self.ui.Imagemax.value()
        self.Imagemin = self.ui.Imagemin.value()
        self.Mosaicmax = self.ui.Mosaicmax.value()
        self.Mosaicmin = self.ui.Mosaicmin.value()
        self.QueueOut()
        
    def QueueOut(self):
        self.item = self.queue.get()
        while self.item.action != 'exit':
            start=time.time()
            #self.ui.statusbar.showMessage('Display thread is doing ' + self.item.action)
            try:
                if self.item.action in ['Snap']:
                    self.display_actions += 1
                    self.Display_Snap(self.item.data)
                elif self.item.action == 'Display_Mosaic':
                    self.Display_Mosaic(self.item.data, self.item.args)
                elif self.item.action == 'UpdateContrastImage':
                    self.Update_contrast_Image()
                elif self.item.action == 'UpdateContrastMosaic':
                    self.Update_contrast_Mosaic()
                elif self.item.action == 'display_counts':
                    self.print_display_counts()
                elif self.item.action == 'restart_tilenum':
                    self.restart_tilenum()
                elif self.item.action == 'change_slice_number':
                    self.sliceNum = self.ui.SliceN.value()
                    self._set_ui_value('CuSlice', self.sliceNum)
                elif self.item.action == 'WriteAgar':
                    self.WriteAgar(self.item.data, self.item.args)
                elif self.item.action == 'Init_Mosaic':
                    self.Init_Mosaic(self.item.args)
                elif self.item.action == 'Save_Mosaic':
                    self.Save_Mosaic()
                    
                else:
                    message = 'Display and save thread is doing something invalid' + self.item.action
                    self._set_status_message(message)
                    # self.ui.PrintOut.append(message)
                    self.log.write(message)
                if time.time()-start>1:
                    print('time for DnS:',round(time.time()-start,3))
            except Exception as error:
                message = "An error occurred: skip the display and save action"
                self.log.write(message)
                report_exception(self.ui, self.log, error, where=f"DnSThread/{self.item.action}")
            # num+=1
            # print(num, 'th display\n')
            self.item = self.queue.get()
            
        self._set_status_message("Display and save Thread successfully exited...")
            
    def print_display_counts(self):
        message = str(self.display_actions)+ self.ui.ACQMode.currentText() +' displayed\n'
        print(message)
        # self.ui.PrintOut.append(message)
        self.log.write(message)
        self.display_actions = 0
        
    
    def Display_Snap(self, data):
        # print(data.shape)
        scale = self.ui.scale.value()
        Xpixels = self.ui.Width.value()
        Ypixels = self.ui.Height.value()
        Zpixels = data.shape[0]
        data = np.uint16(data.reshape(Zpixels, Ypixels//2, 2, Xpixels//2, 2).mean(axis=(2, 4))*16)
        Xpixels = Xpixels//2
        Ypixels = Ypixels//2
        if Zpixels > 1:
            self.image=data[Zpixels//2]
        else:
            self.image = data[0]
        # print(self.image[0,0:5])
        self._refresh_image_view(self.image)
        
        if self.ui.Save.isChecked():
            
            tif = TIFF.open(self.ui.DIR.toPlainText()+'/'+self.SnapFilename([Ypixels,Xpixels,Zpixels]), mode='w')
            for ii in range(Zpixels):
                # self.WriteData(data, self.AlineFilename([Yrpt,Xpixels,Zpixels]))
                tif.write_image(data[ii])
            tif.close()
            
    
    def Init_Mosaic(self, args = []):
        Xtiles = args[1][0]  # 马赛克列数
        Ytiles = args[1][1]  # 马赛克行数
        #self.scale = min(math.gcd(self.h,self.w),32) #求小于32的最大公约数作为scale
        scale = self.ui.scale.value()
        Xpixels = self.ui.Width.value()//2
        Ypixels = self.ui.Height.value()//2
        self.SampleMosaic = np.zeros([Ytiles*(Ypixels//scale), Xtiles*(Xpixels//scale)], dtype=np.uint16)

        self._refresh_mosaic_view(self.SampleMosaic)

    
    
    def Display_Mosaic(self, data, args = []):
        scale = self.ui.scale.value()
        Xpixels = self.ui.Width.value()
        Ypixels = self.ui.Height.value()
        Zpixels = data.shape[0]
        # print(np.array(data).shape)
        data = np.uint16(data.reshape(Zpixels, Ypixels//2, 2, Xpixels//2, 2).mean(axis=(2, 4))*16)
        # print(np.array(data).shape)
        Xpixels = Xpixels//2
        Ypixels = Ypixels//2
        if data.shape[0]> 1:
            self.image=data[data.shape[0]//2]
        else:
            self.image = data[0]
            
        self._refresh_image_view(self.image)
        
        tileMean = np.mean(self.image)
        self._set_ui_value('tileMean', tileMean)
        
        Xtiles = args[1][0]
        Ytiles = args[1][1]
        Y = Ytiles - args[0][1] - 1
        X = args[0][0] if args[0][1] % 2 == 1 else Xtiles - args[0][0] - 1

        self.SampleMosaic[Ypixels//scale*Y:Ypixels//scale*(Y+1),\
                  Xpixels//scale*X:Xpixels//scale*(X+1)] = self.image[::scale, ::scale]
    
        self._refresh_mosaic_view(self.SampleMosaic)
        if self.ui.Save.isChecked():
            filenametiff, filenamebin = self.MosaicFilename([Ypixels,Xpixels,Zpixels])
            mosaic_dir = os.path.join(self.ui.DIR.toPlainText(), 'mosaic')
            os.makedirs(mosaic_dir, exist_ok=True)
            tif = TIFF.open(os.path.join(mosaic_dir, filenametiff), mode='w')
            for ii in range(Zpixels):
                tif.write_image(data[ii,:,:])
            tif.close()
    
    # 保存马赛克拼图图像
    def Save_Mosaic(self):
        if self.ui.Save.isChecked():
            pixmap = RGBImagePlot(matrix1=self.SampleMosaic, m=self.ui.Mosaicmin.value(), M=self.ui.Mosaicmax.value())
            pixmap.save(f'{self.ui.DIR.toPlainText()}/slice{self.sliceNum}coase.tif', "TIFF")
        self.DnSBackQueue.put(self.SampleMosaic)


    def Update_contrast_Image(self):
        if self.ui.Imagemin.value() != self.Imagemin or self.ui.Imagemax.value() != self.Imagemax:
            try:
                self._refresh_image_view(self.image)
            except:
                pass
            self.Imagemax = self.ui.Imagemax.value()
            self.Imagemin = self.ui.Imagemin.value()

    def Update_contrast_Mosaic(self):
        if self.ui.Mosaicmin.value() != self.Mosaicmin or self.ui.Mosaicmax.value() != self.Mosaicmax:
            try:
                self._refresh_mosaic_view(self.SampleMosaic)
            except:
                pass
            self.Mosaicmax = self.ui.Mosaicmax.value()
            self.Mosaicmin = self.ui.Mosaicmin.value()
            
    
    def restart_tilenum(self):
        self.tileNum = 1
        self.sliceNum = self.sliceNum+1
        print('/n slicenum: ', self.sliceNum,'/n')
        self._set_ui_value('CuSlice', self.sliceNum)
        # if not os.path.exists(self.ui.DIR.toPlainText()+'/mosaic/slice'+str(self.sliceNum)):
        #     os.mkdir(self.ui.DIR.toPlainText()+'/mosaic/slice'+str(self.sliceNum))
        # if not os.path.exists(self.ui.DIR.toPlainText()+'/surf/vol'+str(self.sliceNum)):
        #     os.mkdir(self.ui.DIR.toPlainText()+'/surf/vol'+str(self.sliceNum))
        # if not os.path.exists(self.ui.DIR.toPlainText()+'/fitting/vol'+str(self.sliceNum)):
        #     os.mkdir(self.ui.DIR.toPlainText()+'/fitting/vol'+str(self.sliceNum))
        
    def MosaicFilename(self, shape = [0,0,0]):
        filename = 'slice-'+str(self.sliceNum)+'-tile-'+str(self.tileNum)+'-'+str(shape[0])+'-'+str(shape[1])+'-'+str(shape[2])+'.tif'
        filenamebin = 'slice-'+str(self.sliceNum)+'-tile-'+str(self.tileNum)+'-'+str(shape[0])+'-'+str(shape[1])+'-'+str(shape[2])+'.bin'
        
        self.tileNum = self.tileNum + 1
    
        print(filename)
        # self.ui.PrintOut.append(filename)
        self.log.write(filename)
        return filename, filenamebin

    
    def SnapFilename(self, shape):
        filename = 'Snap-'+str(self.SnapNum)+'-'+str(shape[0])+'-'+str(shape[1])+'-'+str(shape[2])+'.tif'
        self.SnapNum = self.SnapNum + 1
        return filename
    
        
    # def WriteAgar(self, data, args):
    #     [Ystep, Xstep] = args
    #     filename = 'slice-'+str(self.sliceNum)+'-agarTiles X-'+str(Xstep)+'-by Y-'+str(Ystep)+'-.bin'
    #     filePath = self.ui.DIR.toPlainText()
    #     filePath = filePath + "/" + filename
    #     dataArg = np.asarray(data)
    #     # print(dataArg.shape)
    #     if dataArg.ndim == 3:
    #         data2d = dataArg[:, :,0] 
    #     elif data.ndim == 2:
    #         data2d = dataArg
    #     else:
    #         raise ValueError(f"WriteAgar: unexpected data.ndim={data.ndim}, expect 2 or 3")
    #     # print(data2d.shape, Ystep, Xstep, data2d.shape != (Ystep, Xstep))
    #     if data2d.shape != (Ystep, Xstep):
    #         print("Warning: tile_flag shape", data2d.shape, "!= expected", (Ystep, Xstep))
        
    #     print(data2d)
    #     fp = open(filePath, 'wb')
    #     np.uint8(data2d).tofile(fp)
    #     fp.close()
    def WriteAgar(self, data, args):
        [Ystep, Xstep] = args
        filename = 'slice-'+str(self.sliceNum)+'-agarTiles X-'+str(Xstep)+'-by Y-'+str(Ystep)+'-.bin'
        filePath = self.ui.DIR.toPlainText()
        filePath = filePath + "/" + filename
        # print(filePath)
        # print(data.shape, data)
        fp = open(filePath, 'wb')
        np.uint8(data).tofile(fp)
        fp.close()
        
    def WriteData(self, data, filename):
        filePath = self.ui.DIR.toPlainText()
        filePath = filePath + '/' + filename
        # print(filePath)
        import time
        start = time.time()
        fp = open(filePath, 'wb')
        data.tofile(fp)
        fp.close()
        if time.time()-start > 1:
            message = 'time for saving: '+str(round(time.time()-start,3))
            print(message)
            # self.ui.PrintOut.append(message)
            self.log.write(message)
