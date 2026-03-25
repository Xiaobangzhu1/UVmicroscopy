# -*- coding: utf-8 -*-

"""
Created on Tue Dec 12 16:51:20 2023

@author: admin
"""
###########################################
# 25000 steps per revolve
global STEPS
STEPS = 25000
# 2mm per revolve
global XDISTANCE
XDISTANCE = 2
global YDISTANCE
YDISTANCE = 2
global ZDISTANCE
ZDISTANCE = 1

global SIM
SIM = False
###########################################
from PyQt5.QtCore import  QThread

try:
    import artdaq as daq
    from artdaq.constants import AcquisitionType as Atype
    from artdaq.constants import Edge
    from artdaq.constants import (LineGrouping)
except:
    SIM = True
import time
import numpy as np
from Generaic_functions import report_exception

# stage enable/disable digital value
# enable = 0
global XDISABLE
XDISABLE = pow(2,0) # port 2 line 0
global YDISABLE
YDISABLE = pow(2,0) # port 2 line 2
global ZDISABLE
ZDISABLE = pow(2,0) # port 2 line 4


# stage forwared backward digital value
global XFORWARD
XFORWARD = pow(2,1) # port 2 line 1
global YFORWARD
YFORWARD = pow(2,2) # port 2 line 3
global ZFORWARD
ZFORWARD = pow(2,3) # port 2 line 5

global XBACKWARD
XBACKWARD = 0
global YBACKWARD
YBACKWARD = 0
global ZBACKWARD
ZBACKWARD = 0 # port 2 line 5, but reverse
# backward = 0
# stage channel digital value
global XCH
XCH = pow(2,0) # port 0 line 0
global YCH
YCH = pow(2,1) # port 0 line 1
global ZCH
ZCH = pow(2,2) # port 0 line2

class DOThread(QThread):
    def __init__(self):
        super().__init__()
        self.DOtask = None
    
    def run(self):
        self.Init_all_termial()
        self.DOBackQueue.get()
        self.QueueOut()
        
    def QueueOut(self):
        self.item = self.queue.get()
        while self.item.action != 'exit':
            try:
                if self.item.action == 'Xmove2':
                    self.DirectMove(axis = 'X')
                elif self.item.action == 'Ymove2':
                    self.DirectMove(axis = 'Y')
                elif self.item.action == 'Zmove2':
                    self.DirectMove(axis = 'Z')
                elif self.item.action == 'ZMmove2':
                    self.DirectMicroMove()
                elif self.item.action == 'LightON':
                    self.Light_on()
                elif self.item.action == 'LightAON':
                    self.LightA_on()
                elif self.item.action == 'LightBON':
                    self.LightB_on()
                elif self.item.action == 'LightOFF':
                    self.Light_off()
                elif self.item.action == 'PumpON':
                    self.Pump_on()
                elif self.item.action == 'PumpAON':
                    self.PumpA_on()
                elif self.item.action == 'PumpBON':
                    self.PumpB_on()
                elif self.item.action == 'PumpOFF':
                    self.Pump_off()
                elif self.item.action == 'XUP':
                    self.StepMove(axis = 'X', Direction = 'UP')
                elif self.item.action == 'YUP':
                    self.StepMove(axis = 'Y', Direction = 'UP')
                elif self.item.action == 'ZUP':
                    self.StepMove(axis = 'Z', Direction = 'UP')
                elif self.item.action == 'ZMUP':
                     self.StepMicroMove(Direction = 'UP')
                elif self.item.action == 'XDOWN':
                    self.StepMove(axis = 'X', Direction = 'DOWN')
                elif self.item.action == 'YDOWN':
                    self.StepMove(axis = 'Y', Direction = 'DOWN')
                elif self.item.action == 'ZDOWN':
                    self.StepMove(axis = 'Z', Direction = 'DOWN')
                elif self.item.action == 'ZMDOWN':
                     self.StepMicroMove(Direction = 'DOWN')
                elif self.item.action == 'startVibratome':
                    self.startVibratome()
                elif self.item.action == 'stopVibratome':
                    self.stopVibratome()
                elif self.item.action == 'Init':
                    self.Init_all_termial()
                elif self.item.action == 'Uninit':
                    self.Uninit()
                
                elif self.item.action == 'ConfigZstack':
                    self.ConfigZstack()
                elif self.item.action == 'Zstack':
                    self.Zstack()
                elif self.item.action == 'StopCloseZstack':
                    self.StopCloseZstack()
                    
                    
                
                else:
                    message = 'DO thread is doing something undefined: '+self.item.action
                    self.ui.statusbar.showMessage(message)
                    print(message)
                    # self.ui.PrintOut.append(message)
                    self.log.write(message)
            except Exception as error:
                message = "An error occurred, skip the DO action"
                self.log.write(message)
                report_exception(self.ui, self.log, error, where=f"DOThread/{self.item.action}")
            self.item = self.queue.get()
        self.ui.statusbar.showMessage('DO thread successfully exited')
    def Init_all_termial(self):
        # piezo terminal
        self.PiezoAO = self.ui.AODOboard.toPlainText()+'/'+self.ui.PiezoAO.currentText()
        # Stage steps
        self.StageSteps = self.ui.AODOboard.toPlainText()+'/port0/line0:7'
        # stage direction and enables
        self.StageDnE = self.ui.AODOboard.toPlainText()+'/port2/line0:7'
        # Camera trigger termial
        self.CameraTrig = self.ui.AODOboard.toPlainText()+'/'+self.ui.CameraTrig.currentText()
        # print(self.CameraTrig)
        # vibratome enable terminal
        self.VibEnable = self.ui.AODOboard.toPlainText()+'/'+self.ui.VibEnable.currentText()
        # print(self.VibEnable)
        # LED enable terminal
        self.LEDEnable = self.ui.AODOboard.toPlainText()+'/'+self.ui.LEDEnable.currentText()
        # print(self.LEDEnable)
        # LED enable terminal
        self.PumpEnable = self.ui.AODOboard.toPlainText()+'/'+self.ui.PumpEnable.currentText()
        # print(self.PumpEnable)
        self.ui.Xcurrent.setValue(self.ui.XPosition.value())
        self.ui.Ycurrent.setValue(self.ui.YPosition.value())
        self.ui.Zcurrent.setValue(self.ui.ZPosition.value())
        self.ui.ZMcurrent.setValue(self.ui.ZMPosition.value())
        message = "Stage position updated..."
    
        self.ui.statusbar.showMessage(message)
        # self.ui.PrintOut.append(message)
        self.log.write(message)
        print(message)
        self.DOBackQueue.put(0)
        
    def Init_Stages(self):
        # self.Xpos = self.ui.XPosition.value()
        # self.Ypos = self.ui.YPosition.value()
        # self.Zpos = self.ui.ZPosition.value()
        self.ui.Xcurrent.setValue(self.ui.XPosition.value())
        self.ui.Ycurrent.setValue(self.ui.YPosition.value())
        self.ui.Zcurrent.setValue(self.ui.ZPosition.value())
        self.ui.ZMcurrent.setValue(self.ui.ZMPosition.value())
        
        message = "Stage position updated..."

        self.ui.statusbar.showMessage(message)
        # self.ui.PrintOut.append(message)
        self.log.write(message)
        print(message)
        self.DOBackQueue.put(0)
        # print('X pos: ',self.Xpos)
        # print('Y pos: ',self.Ypos)
        # print('Z pos: ',self.Zpos)
    
    def Uninit(self):
        if not (SIM or self.SIM):
            settingtask = daq.Task('setting')
            settingtask.do_channels.add_do_chan(lines='Robot/port2/line0:3',)
            tmp = np.uint32(YDISABLE + XDISABLE + ZDISABLE)
            settingtask.write(tmp, auto_start = True)
            settingtask.stop()
            settingtask.close()
        self.DOBackQueue.put(0)

    def stagewave_ramp(self, distance, DISTANCE):
        # generate stage movement that ramps up and down speed so that motor won't miss signal at beginning and end
        # how to do that: motor is driving by low->high digital transition
        # ramping up: make the interval between two highs with long time at the beginning, then gradually goes down.vice versa for ramping down
        if np.abs(distance) > 0.02:
            max_interval = 100
        elif np.abs(distance) > 0.01:
            max_interval = 40
        elif np.abs(distance) > 0.003:
            max_interval = 10
        else:
            max_interval = 0
        ramp_up_interval = np.arange(max_interval,0,-2)
        ramp_down_interval = np.arange(1,max_interval+1,2)
        ramping_highs = np.sum(len(ramp_down_interval)+len(ramp_up_interval)) # number steps used in ramping up and down process
        total_highs = np.uint32(STEPS//DISTANCE*np.abs(distance))
        
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
        DOwaveform = np.ones([total_highs - ramping_highs, 2],dtype = np.uint32)
        DOwaveform[:,1] = 0
        DOwaveform=DOwaveform.flatten()
        
        # append all arrays
        DOwaveform = np.append(ramp_up_waveform,DOwaveform)
        DOwaveform = np.append(DOwaveform,ramp_down_waveform)
        # print('total highs: ',np.sum(DOwaveform))
        # from matplotlib import pyplot as plt
        # plt.figure()
        # plt.plot(DOwaveform[0:5000])
        return DOwaveform
        
    def Move(self, axis = 'X'):
        ###########################
        # you can only move one axis at a time
        ###########################
        # X axis use port 2 line 0-1 for enable and direction, use port 0 line 0 for steps
        # Y axis use port 2 line 2-3 for enable and direction, use port 0 line 1 for steps
        # Z axis use port 2 line 4-5 for enable and direction, use port 0 line 2 for steps
        # enable low enables, enable high disables
        if axis == 'X':
            line = XCH
            DISTANCE = XDISTANCE
            speed = self.ui.XSpeed.value()
            pos = self.ui.XPosition.value()
            if pos>self.ui.Xmax.value()or pos<self.ui.Xmin.value():
                message = 'X target postion invalid, abort...'
                # self.ui.PrintOut.append(message)
                self.log.write(message)
                print(message)
                return message
            distance = self.ui.XPosition.value()-self.ui.Xcurrent.value()
            if distance > 0:
                direction = XFORWARD
                sign = 1
            else:
                direction = XBACKWARD
                sign = -1
            enable = 0#YDISABLE + ZDISABLE
        elif axis == 'Y':
            line = YCH
            DISTANCE = YDISTANCE
            speed = self.ui.YSpeed.value()
            pos = self.ui.YPosition.value()
            if pos>self.ui.Ymax.value() or pos<self.ui.Ymin.value():
                message = 'Y target postion invalid, abort...'
                # self.ui.PrintOut.append(message)
                self.log.write(message)
                print(message)
                return message
            distance = self.ui.YPosition.value()-self.ui.Ycurrent.value()
            if distance > 0:
                direction = YFORWARD
                sign = 1
            else:
                direction = YBACKWARD
                sign = -1
            enable = 0#XDISABLE + ZDISABLE
        elif axis == 'Z':
            line = ZCH
            DISTANCE = ZDISTANCE
            speed = self.ui.ZSpeed.value()
            pos = self.ui.ZPosition.value()
            if pos>self.ui.Zmax.value() or pos<self.ui.Zmin.value():
                message = 'Z target postion invalid, abort...'
                # self.ui.PrintOut.append(message)
                self.log.write(message)
                print(message)
                return message
            distance = self.ui.ZPosition.value()-self.ui.Zcurrent.value()
            if distance > 0:
                direction = ZFORWARD
                sign = 1
            else:
                direction = ZBACKWARD
                sign = -1
            enable = 0#XDISABLE + YDISABLE
            
        if np.abs(distance) < 0.003:
            message = axis + ' move2 action aborted'
            # self.ui.PrintOut.append(message)
            print(message)
            self.log.write(message)
            return 0
        if not (SIM or self.SIM):
            with daq.Task('Move_task') as DOtask, daq.Task('stageEnable') as stageEnabletask:
                # configure stage direction and enable
                stageEnabletask.do_channels.add_do_chan(lines='Robot/port2/line0:3')
                stageEnabletask.write(direction + enable, auto_start = True)
                stageEnabletask.wait_until_done(timeout = 1)
                stageEnabletask.stop()
                time.sleep(0.1)
                # configure DO task 
                DOwaveform = self.stagewave_ramp(distance, DISTANCE)
                DOwaveform = np.uint32(DOwaveform * line)
                message = axis+' moving: '+str(round(np.sum(DOwaveform)/line/25000*DISTANCE*sign,3))+'mm'+' target pos: '+str(pos)
                print(message)
                # self.ui.PrintOut.append(message)
                self.log.write(message)
                
                DOtask.do_channels.add_do_chan(lines='Robot/port0/line0:7')
                DOtask.timing.cfg_samp_clk_timing(rate=STEPS*2//DISTANCE*round(speed,2), \
                                                  active_edge= Edge.FALLING,\
                                                  sample_mode=Atype.FINITE,samps_per_chan=len(DOwaveform))
                DOtask.write(DOwaveform, auto_start = False)
                DOtask.start()
                DOtask.wait_until_done(timeout =300)
                DOtask.stop()
                # message = axis+' current pos: '+str(pos)
                # print(message)
                # # self.ui.PrintOut.append(message)
                # self.log.write(message)
                # settingtask.write(XDISABLE + YDISABLE + ZDISABLE, auto_start = True)
                
        if axis == 'X':
            self.ui.Xcurrent.setValue(self.ui.Xcurrent.value()+distance)
            # self.ui.XPosition.setValue(self.Xpos)
        elif axis == 'Y':
            self.ui.Ycurrent.setValue(self.ui.Ycurrent.value()+distance)
            # self.ui.YPosition.setValue(self.Ypos)
        elif axis == 'Z':
            self.ui.Zcurrent.setValue(self.ui.Zcurrent.value()+distance)
            # self.ui.ZPosition.setValue(self.Zpos)
        message = 'X :'+str(self.ui.Xcurrent.value())+' Y :'+str(round(self.ui.Ycurrent.value(),2))+' Z :'+str(self.ui.Zcurrent.value())
        print(message)
        self.log.write(message)
        
    def DirectMove(self, axis):
        self.Move(axis)
        self.DOBackQueue.put(0)
        
    def StepMove(self, axis, Direction):
        if axis == 'X':
            distance = self.ui.Xstagestepsize.value() if Direction == 'UP' else -self.ui.Xstagestepsize.value() 
            self.ui.XPosition.setValue(self.ui.Xcurrent.value()+distance)
            self.Move(axis)
            self.DOBackQueue.put(0)
        elif axis == 'Y':
            distance = self.ui.Ystagestepsize.value() if Direction == 'UP' else -self.ui.Ystagestepsize.value() 
            self.ui.YPosition.setValue(self.ui.Ycurrent.value()+distance)
            self.Move(axis)
            self.DOBackQueue.put(0)
        elif axis == 'Z':
            distance = self.ui.Zstagestepsize.value() if Direction == 'UP' else -self.ui.Zstagestepsize.value() 
            self.ui.ZPosition.setValue(self.ui.Zcurrent.value()+distance)
            self.Move(axis)
            self.DOBackQueue.put(0)
            

    def Light_off(self):
        if not (SIM or self.SIM):
            with daq.Task() as light_task:
                light_task.do_channels.add_do_chan(self.LEDEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                light_task.write([0, 0])
        
    def LightA_on(self):
        if not (SIM or self.SIM):
            with daq.Task() as light_task:
                light_task.do_channels.add_do_chan(self.LEDEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                light_task.write([1, 0])
        self.DOBackQueue.put('Light Turned On')
        
    def Light_on(self):
        if not (SIM or self.SIM):
            with daq.Task() as light_task:
                light_task.do_channels.add_do_chan(self.LEDEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                light_task.write([1, 1])
        self.DOBackQueue.put('Light Turned On')
    
    def LightB_on(self):
        if not (SIM or self.SIM):
            with daq.Task() as light_task:
                light_task.do_channels.add_do_chan(self.LEDEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                light_task.write([0, 1])
        self.DOBackQueue.put('Light Turned On')
            
    def DirectMicroMove(self):
        self.MoveMicro()
        self.DOBackQueue.put('ZM Moved')
         
    def StepMicroMove(self,Direction):
        if Direction == 'UP':
            self.ui.ZMPosition.setValue(self.ui.ZMPosition.value()+self.ui.ZMstagestepsize.value())
            self.MoveMicro()
        elif Direction == 'DOWN':
            self.ui.ZMPosition.setValue(self.ui.ZMPosition.value()-self.ui.ZMstagestepsize.value())
            self.MoveMicro()
        self.DOBackQueue.put(0)
        
    def MoveMicro(self):
        if not (SIM or self.SIM):
            pos = self.ui.ZMPosition.value()
            with daq.Task('AOtask') as AOtask:
                AOtask.ao_channels.add_ao_voltage_chan(physical_channel=self.PiezoAO, \
                                                      min_val=0, max_val=10.0, \
                                                      units=daq.constants.VoltageUnits.VOLTS)
                voltage = pos * 0.1
                voltage = max(0.0, min(10.0, voltage))
                AOtask.write(voltage, auto_start=True)
                AOtask.wait_until_done(timeout = 0.05)
                AOtask.stop()
                self.ui.ZMcurrent.setValue(pos)
                
    def Zstack(self):
        Steps = self.ui.Zstack.value()
        pos = self.ui.ZMstagestepsize.value()*(np.array(range(Steps))/1.0+0.5-Steps/2)+\
            self.ui.XStartHeight.value()# um
        # print(pos)
        for istep in range(Steps):
            self.ui.ZMPosition.setValue(pos[istep])
            self.AOtask.write(pos[istep] * 0.1, auto_start = True)
            self.AOtask.wait_until_done(timeout = 0.005)
            self.ui.ZMcurrent.setValue(pos[istep])
            self.DOtask.write(1, auto_start = True)
            self.DOtask.wait_until_done(timeout = 0.005)
            # time.sleep(0.5)
            self.DOtask.write(0, auto_start = True)
            # wait until last exposure finish
            time.sleep((self.ui.CurrentExpo.value()+15)/1000.0)
            
            
    def ConfigZstack(self):
        self.AOtask = daq.Task('ZstackAOtask') 
        self.DOtask = daq.Task('ZstackDOtask')
        self.AOtask.ao_channels.add_ao_voltage_chan(physical_channel=self.PiezoAO, \
                                              min_val=- 10.0, max_val=10.0, \
                                              units=daq.constants.VoltageUnits.VOLTS)

        self.DOtask.do_channels.add_do_chan(lines=self.CameraTrig,line_grouping=LineGrouping.CHAN_PER_LINE)
        # print(self.CameraTrig)

    def StopCloseZstack(self):
        # self.AOtask.wait_until_done(timeout = 5)
        self.AOtask.stop()
        self.DOtask.stop()
        self.AOtask.close()
        self.DOtask.close()             
            
                        
    def startVibratome(self):
        if not (SIM or self.SIM):
            settingtask = daq.Task('vibratome')
            # print(self.VibEnable)
            settingtask.do_channels.add_do_chan(lines=self.VibEnable,
            line_grouping=LineGrouping.CHAN_PER_LINE)
            settingtask.write(1, auto_start = True)
            settingtask.wait_until_done(timeout = 0.1)
            settingtask.stop()
            settingtask.close()
            # print('here')
            self.Pump_on()
        self.DOBackQueue.put(0)
        
    def stopVibratome(self):
        if not (SIM or self.SIM):
            settingtask = daq.Task('vibratome')
            settingtask.do_channels.add_do_chan(lines=self.VibEnable,
            line_grouping=LineGrouping.CHAN_PER_LINE)
            settingtask.write(0, auto_start = True)
            settingtask.wait_until_done(timeout = 0.1)
            settingtask.stop()
            settingtask.close()
            #self.Pump_off()
        self.DOBackQueue.put(0)

    
    #Pump line: P1.4-water out ; P1.3-water in

    def Pump_on(self):
        # print('herhe')
        if not (SIM or self.SIM):
            with daq.Task() as Pump_task:
                Pump_task.do_channels.add_do_chan(self.PumpEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                Pump_task.write([1, 1], auto_start = True)
        # self.DOBackQueue.put('Pump Turned On')
           
        
    def PumpA_on(self):
        if not (SIM or self.SIM):
            with daq.Task() as Pump_task:
                Pump_task.do_channels.add_do_chan(self.PumpEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                Pump_task.write([1, 0], auto_start = True)
        # self.DOBackQueue.put('Pump Turned On')
    
    def PumpB_on(self):
        if not (SIM or self.SIM):
            with daq.Task() as Pump_task:
                Pump_task.do_channels.add_do_chan(self.PumpEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                Pump_task.write([0, 1], auto_start = True)
        # self.DOBackQueue.put('Pump Turned On')
    
    def Pump_off(self):
        if not (SIM or self.SIM):
            with daq.Task() as Pump_task:
                Pump_task.do_channels.add_do_chan(self.PumpEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                Pump_task.write([0, 0], auto_start = True)