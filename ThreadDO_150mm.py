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
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot

try:
    import artdaq as daq
    from artdaq.constants import AcquisitionType as Atype
    from artdaq.constants import Edge
    from artdaq.constants import (LineGrouping)
except:
    SIM = True
import time
import numpy as np
from Generaic_functions import report_exception, parse_debug_flag, write_breadcrumb

DEBUG_DISABLE_DO = parse_debug_flag('DEBUG_DISABLE_DO', False)

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
    request_set_value = pyqtSignal(str, float)
    request_status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.DOtask = None
        self.request_set_value.connect(self._apply_set_value)
        self.request_status.connect(self._apply_status_message)

    @pyqtSlot(str, float)
    def _apply_set_value(self, widget_name, value):
        widget = getattr(self.ui, widget_name, None)
        if widget is not None:
            widget.setValue(float(value))

    def _set_ui_value(self, widget_name, value):
        self.request_set_value.emit(widget_name, float(value))

    @pyqtSlot(str)
    def _apply_status_message(self, message):
        try:
            self.ui.statusbar.showMessage(str(message))
        except Exception:
            pass

    def _set_status_message(self, message):
        self.request_status.emit(str(message))

    def _validate_move_params(self, axis, speed, distance_per_revolve, waveform_len):
        if speed is None or speed <= 0:
            msg = f'{axis} move aborted: invalid speed={speed}, speed must be > 0'
            self.log.write(msg)
            write_breadcrumb('DO_PARAM_INVALID', log=self.log, detail=msg)
            return None
        if distance_per_revolve is None or distance_per_revolve <= 0:
            msg = f'{axis} move aborted: invalid DISTANCE={distance_per_revolve}'
            self.log.write(msg)
            write_breadcrumb('DO_PARAM_INVALID', log=self.log, detail=msg)
            return None
        if waveform_len is None or waveform_len <= 0:
            msg = f'{axis} move aborted: invalid samps_per_chan={waveform_len}'
            self.log.write(msg)
            write_breadcrumb('DO_PARAM_INVALID', log=self.log, detail=msg)
            return None

        rate = int(STEPS * 2 / distance_per_revolve * round(float(speed), 2))
        if rate <= 0 or rate > 1_000_000:
            msg = f'{axis} move aborted: invalid sample rate={rate}, expected [1,1000000]'
            self.log.write(msg)
            write_breadcrumb('DO_PARAM_INVALID', log=self.log, detail=msg)
            return None
        return rate
    
    def run(self):
        if DEBUG_DISABLE_DO:
            self.SIM = True
            self.log.write('DEBUG_DISABLE_DO=1, DO hardware path disabled')
            write_breadcrumb('DO_DISABLED_BY_FLAG', log=self.log)
        self.Init_all_termial()
        self.DOBackQueue.get()
        self.QueueOut()
        
    def QueueOut(self):
        self.item = self.queue.get()
        while self.item.action != 'exit':
            try:
                if self.item.action == 'Xmove2':
                    target = self.item.args[0] if isinstance(self.item.args, (list, tuple)) and len(self.item.args) > 0 else None
                    self.DirectMove(axis='X', target_pos=target)
                elif self.item.action == 'Ymove2':
                    target = self.item.args[0] if isinstance(self.item.args, (list, tuple)) and len(self.item.args) > 0 else None
                    self.DirectMove(axis='Y', target_pos=target)
                elif self.item.action == 'Zmove2':
                    target = self.item.args[0] if isinstance(self.item.args, (list, tuple)) and len(self.item.args) > 0 else None
                    self.DirectMove(axis='Z', target_pos=target)
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
                    write_breadcrumb('DO_VIBRATOME_START_DISPATCH', log=self.log)
                    self.startVibratome()
                elif self.item.action == 'stopVibratome':
                    write_breadcrumb('DO_VIBRATOME_STOP_DISPATCH', log=self.log)
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
                    self._set_status_message(message)
                    print(message)
                    # self.ui.PrintOut.append(message)
                    self.log.write(message)
            except Exception as error:
                message = "An error occurred, skip the DO action"
                self.log.write(message)
                report_exception(self.ui, self.log, error, where=f"DOThread/{self.item.action}")
            self.item = self.queue.get()
        self._set_status_message('DO thread successfully exited')
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
        self._set_ui_value('Xcurrent', self.ui.XPosition.value())
        self._set_ui_value('Ycurrent', self.ui.YPosition.value())
        self._set_ui_value('Zcurrent', self.ui.ZPosition.value())
        self._set_ui_value('ZMcurrent', self.ui.ZMPosition.value())
        message = "Stage position updated..."
    
        self._set_status_message(message)
        # self.ui.PrintOut.append(message)
        self.log.write(message)
        print(message)
        self.DOBackQueue.put(0)
        
    def Init_Stages(self):
        # self.Xpos = self.ui.XPosition.value()
        # self.Ypos = self.ui.YPosition.value()
        # self.Zpos = self.ui.ZPosition.value()
        self._set_ui_value('Xcurrent', self.ui.XPosition.value())
        self._set_ui_value('Ycurrent', self.ui.YPosition.value())
        self._set_ui_value('Zcurrent', self.ui.ZPosition.value())
        self._set_ui_value('ZMcurrent', self.ui.ZMPosition.value())
        
        message = "Stage position updated..."

        self._set_status_message(message)
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
        
    def Move(self, axis = 'X', target_pos=None):
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
            pos = self.ui.XPosition.value() if target_pos is None else target_pos
            if pos>self.ui.Xmax.value()or pos<self.ui.Xmin.value():
                message = f'X move2 action aborted: target position out of range (target={pos}, range=[{self.ui.Xmin.value()}, {self.ui.Xmax.value()}])'
                # self.ui.PrintOut.append(message)
                self.log.write(message)
                print(message)
                write_breadcrumb('DO_MOVE_ABORTED', log=self.log, detail=message)
                return {
                    'axis': axis,
                    'status': 'aborted',
                    'reason': 'out_of_range',
                    'detail': message,
                    'target': pos,
                }
            distance = pos-self.ui.Xcurrent.value()
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
            pos = self.ui.YPosition.value() if target_pos is None else target_pos
            if pos>self.ui.Ymax.value() or pos<self.ui.Ymin.value():
                message = f'Y move2 action aborted: target position out of range (target={pos}, range=[{self.ui.Ymin.value()}, {self.ui.Ymax.value()}])'
                # self.ui.PrintOut.append(message)
                self.log.write(message)
                print(message)
                write_breadcrumb('DO_MOVE_ABORTED', log=self.log, detail=message)
                return {
                    'axis': axis,
                    'status': 'aborted',
                    'reason': 'out_of_range',
                    'detail': message,
                    'target': pos,
                }
            distance = pos-self.ui.Ycurrent.value()
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
            pos = self.ui.ZPosition.value() if target_pos is None else target_pos
            if pos>self.ui.Zmax.value() or pos<self.ui.Zmin.value():
                message = f'Z move2 action aborted: target position out of range (target={pos}, range=[{self.ui.Zmin.value()}, {self.ui.Zmax.value()}])'
                # self.ui.PrintOut.append(message)
                self.log.write(message)
                print(message)
                write_breadcrumb('DO_MOVE_ABORTED', log=self.log, detail=message)
                return {
                    'axis': axis,
                    'status': 'aborted',
                    'reason': 'out_of_range',
                    'detail': message,
                    'target': pos,
                }
            distance = pos-self.ui.Zcurrent.value()
            if distance > 0:
                direction = ZFORWARD
                sign = 1
            else:
                direction = ZBACKWARD
                sign = -1
            enable = 0#XDISABLE + YDISABLE
            
        if np.abs(distance) < 0.003:
            message = (
                f'{axis} move2 action aborted: |delta|<{0.003} mm '
                f'(delta={distance:.6f}, current={getattr(self.ui, axis + "current").value()}, target={pos})'
            )
            # self.ui.PrintOut.append(message)
            print(message)
            self.log.write(message)
            write_breadcrumb('DO_MOVE_ABORTED', log=self.log, detail=message)
            return {
                'axis': axis,
                'status': 'aborted',
                'reason': 'tiny_delta',
                'detail': message,
                'delta': float(distance),
                'target': pos,
            }
        if not (SIM or self.SIM):
            write_breadcrumb('DO_MOVE_BEGIN', log=self.log, detail=f'axis={axis}, distance={distance}, speed={speed}')
            with daq.Task('Move_task') as DOtask, daq.Task('stageEnable') as stageEnabletask:
                # configure stage direction and enable
                write_breadcrumb('DO_STAGE_ENABLE_ADD_CHAN_BEFORE', log=self.log)
                stageEnabletask.do_channels.add_do_chan(lines='Robot/port2/line0:3')
                write_breadcrumb('DO_STAGE_ENABLE_ADD_CHAN_AFTER', log=self.log)

                write_breadcrumb('DO_STAGE_ENABLE_WRITE_BEFORE', log=self.log, detail=f'value={direction + enable}')
                stageEnabletask.write(direction + enable, auto_start = True)
                write_breadcrumb('DO_STAGE_ENABLE_WRITE_AFTER', log=self.log)

                write_breadcrumb('DO_STAGE_ENABLE_WAIT_BEFORE', log=self.log)
                stageEnabletask.wait_until_done(timeout = 1)
                write_breadcrumb('DO_STAGE_ENABLE_WAIT_AFTER', log=self.log)

                write_breadcrumb('DO_STAGE_ENABLE_STOP_BEFORE', log=self.log)
                stageEnabletask.stop()
                write_breadcrumb('DO_STAGE_ENABLE_STOP_AFTER', log=self.log)
                time.sleep(0.1)
                # configure DO task 
                DOwaveform = self.stagewave_ramp(distance, DISTANCE)
                DOwaveform = np.uint32(DOwaveform * line)
                rate = self._validate_move_params(axis, speed, DISTANCE, len(DOwaveform))
                if rate is None:
                    message = f'{axis} move2 action aborted: invalid move parameters (see DO_PARAM_INVALID)'
                    write_breadcrumb('DO_MOVE_ABORTED', log=self.log, detail=message)
                    return {
                        'axis': axis,
                        'status': 'aborted',
                        'reason': 'invalid_params',
                        'detail': message,
                    }
                message = axis+' moving: '+str(round(np.sum(DOwaveform)/line/25000*DISTANCE*sign,3))+'mm'+' target pos: '+str(pos)
                print(message)
                # self.ui.PrintOut.append(message)
                self.log.write(message)
                
                write_breadcrumb('DO_MOVE_ADD_CHAN_BEFORE', log=self.log)
                DOtask.do_channels.add_do_chan(lines='Robot/port0/line0:7')
                write_breadcrumb('DO_MOVE_ADD_CHAN_AFTER', log=self.log)

                write_breadcrumb('DO_MOVE_CFG_TIMING_BEFORE', log=self.log, detail=f'rate={rate}, samps={len(DOwaveform)}')
                DOtask.timing.cfg_samp_clk_timing(rate=rate, \
                                                  active_edge= Edge.FALLING,\
                                                  sample_mode=Atype.FINITE,samps_per_chan=len(DOwaveform))
                write_breadcrumb('DO_MOVE_CFG_TIMING_AFTER', log=self.log)

                write_breadcrumb('DO_MOVE_WRITE_BEFORE', log=self.log)
                DOtask.write(DOwaveform, auto_start = False)
                write_breadcrumb('DO_MOVE_WRITE_AFTER', log=self.log)

                write_breadcrumb('DO_MOVE_START_BEFORE', log=self.log)
                DOtask.start()
                write_breadcrumb('DO_MOVE_START_AFTER', log=self.log)

                write_breadcrumb('DO_MOVE_WAIT_BEFORE', log=self.log)
                DOtask.wait_until_done(timeout =300)
                write_breadcrumb('DO_MOVE_WAIT_AFTER', log=self.log)

                write_breadcrumb('DO_MOVE_STOP_BEFORE', log=self.log)
                DOtask.stop()
                write_breadcrumb('DO_MOVE_STOP_AFTER', log=self.log)
                # message = axis+' current pos: '+str(pos)
                # print(message)
                # # self.ui.PrintOut.append(message)
                # self.log.write(message)
                # settingtask.write(XDISABLE + YDISABLE + ZDISABLE, auto_start = True)
            write_breadcrumb('DO_MOVE_DONE', log=self.log, detail=f'axis={axis}')
                
        if axis == 'X':
            self._set_ui_value('Xcurrent', pos)
            self._set_ui_value('XPosition', pos)
        elif axis == 'Y':
            self._set_ui_value('Ycurrent', pos)
            self._set_ui_value('YPosition', pos)
        elif axis == 'Z':
            self._set_ui_value('Zcurrent', pos)
            self._set_ui_value('ZPosition', pos)
        message = 'X :'+str(self.ui.Xcurrent.value())+' Y :'+str(round(self.ui.Ycurrent.value(),2))+' Z :'+str(self.ui.Zcurrent.value())
        print(message)
        self.log.write(message)
        return {
            'axis': axis,
            'status': 'moved',
            'reason': 'ok',
            'target': pos,
            'delta': float(distance),
        }
        
    def DirectMove(self, axis, target_pos=None):
        result = self.Move(axis, target_pos=target_pos)
        if result is None:
            result = {'axis': axis, 'status': 'unknown', 'reason': 'none'}
        self.DOBackQueue.put(result)
        
    def StepMove(self, axis, Direction):
        write_breadcrumb('DO_STEP_MOVE_BEGIN', log=self.log, detail=f'axis={axis}, direction={Direction}')
        if axis == 'X':
            distance = self.ui.Xstagestepsize.value() if Direction == 'UP' else -self.ui.Xstagestepsize.value() 
            target = self.ui.Xcurrent.value()+distance
            self._set_ui_value('XPosition', target)
            write_breadcrumb('DO_STEP_MOVE_CALL_MOVE', log=self.log, detail=f'axis={axis}, distance={distance}')
            self.Move(axis, target_pos=target)
            self.DOBackQueue.put(0)
        elif axis == 'Y':
            distance = self.ui.Ystagestepsize.value() if Direction == 'UP' else -self.ui.Ystagestepsize.value() 
            target = self.ui.Ycurrent.value()+distance
            self._set_ui_value('YPosition', target)
            write_breadcrumb('DO_STEP_MOVE_CALL_MOVE', log=self.log, detail=f'axis={axis}, distance={distance}')
            self.Move(axis, target_pos=target)
            self.DOBackQueue.put(0)
        elif axis == 'Z':
            distance = self.ui.Zstagestepsize.value() if Direction == 'UP' else -self.ui.Zstagestepsize.value() 
            target = self.ui.Zcurrent.value()+distance
            self._set_ui_value('ZPosition', target)
            write_breadcrumb('DO_STEP_MOVE_CALL_MOVE', log=self.log, detail=f'axis={axis}, distance={distance}')
            self.Move(axis, target_pos=target)
            self.DOBackQueue.put(0)
        write_breadcrumb('DO_STEP_MOVE_DONE', log=self.log, detail=f'axis={axis}, direction={Direction}')
            

    def Light_off(self):
        write_breadcrumb('DO_LIGHT_OFF_BEGIN', log=self.log)
        if not (SIM or self.SIM):
            with daq.Task() as light_task:
                write_breadcrumb('DO_LIGHT_ADD_CHAN_BEFORE', log=self.log, detail=f'line={self.LEDEnable}')
                light_task.do_channels.add_do_chan(self.LEDEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                write_breadcrumb('DO_LIGHT_ADD_CHAN_AFTER', log=self.log)
                write_breadcrumb('DO_LIGHT_WRITE_BEFORE', log=self.log, detail='value=[0,0]')
                light_task.write([0, 0])
                write_breadcrumb('DO_LIGHT_WRITE_AFTER', log=self.log)
        write_breadcrumb('DO_LIGHT_OFF_DONE', log=self.log)
        
    def LightA_on(self):
        write_breadcrumb('DO_LIGHT_A_ON_BEGIN', log=self.log)
        if not (SIM or self.SIM):
            with daq.Task() as light_task:
                write_breadcrumb('DO_LIGHT_ADD_CHAN_BEFORE', log=self.log, detail=f'line={self.LEDEnable}')
                light_task.do_channels.add_do_chan(self.LEDEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                write_breadcrumb('DO_LIGHT_ADD_CHAN_AFTER', log=self.log)
                write_breadcrumb('DO_LIGHT_WRITE_BEFORE', log=self.log, detail='value=[1,0]')
                light_task.write([1, 0])
                write_breadcrumb('DO_LIGHT_WRITE_AFTER', log=self.log)
        self.DOBackQueue.put('Light Turned On')
        write_breadcrumb('DO_LIGHT_A_ON_DONE', log=self.log)
        
    def Light_on(self):
        write_breadcrumb('DO_LIGHT_ON_BEGIN', log=self.log)
        if not (SIM or self.SIM):
            with daq.Task() as light_task:
                write_breadcrumb('DO_LIGHT_ADD_CHAN_BEFORE', log=self.log, detail=f'line={self.LEDEnable}')
                light_task.do_channels.add_do_chan(self.LEDEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                write_breadcrumb('DO_LIGHT_ADD_CHAN_AFTER', log=self.log)
                write_breadcrumb('DO_LIGHT_WRITE_BEFORE', log=self.log, detail='value=[1,1]')
                light_task.write([1, 1])
                write_breadcrumb('DO_LIGHT_WRITE_AFTER', log=self.log)
        self.DOBackQueue.put('Light Turned On')
        write_breadcrumb('DO_LIGHT_ON_DONE', log=self.log)
    
    def LightB_on(self):
        write_breadcrumb('DO_LIGHT_B_ON_BEGIN', log=self.log)
        if not (SIM or self.SIM):
            with daq.Task() as light_task:
                write_breadcrumb('DO_LIGHT_ADD_CHAN_BEFORE', log=self.log, detail=f'line={self.LEDEnable}')
                light_task.do_channels.add_do_chan(self.LEDEnable, line_grouping=LineGrouping.CHAN_PER_LINE)
                write_breadcrumb('DO_LIGHT_ADD_CHAN_AFTER', log=self.log)
                write_breadcrumb('DO_LIGHT_WRITE_BEFORE', log=self.log, detail='value=[0,1]')
                light_task.write([0, 1])
                write_breadcrumb('DO_LIGHT_WRITE_AFTER', log=self.log)
        self.DOBackQueue.put('Light Turned On')
        write_breadcrumb('DO_LIGHT_B_ON_DONE', log=self.log)
            
    def DirectMicroMove(self):
        self.MoveMicro()
        self.DOBackQueue.put('ZM Moved')
         
    def StepMicroMove(self,Direction):
        if Direction == 'UP':
            self._set_ui_value('ZMPosition', self.ui.ZMPosition.value()+self.ui.ZMstagestepsize.value())
            self.MoveMicro()
        elif Direction == 'DOWN':
            self._set_ui_value('ZMPosition', self.ui.ZMPosition.value()-self.ui.ZMstagestepsize.value())
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
                self._set_ui_value('ZMcurrent', pos)
                
    def Zstack(self):
        Steps = self.ui.Zstack.value()
        pos = self.ui.ZMstagestepsize.value()*(np.array(range(Steps))/1.0+0.5-Steps/2)+\
            self.ui.XStartHeight.value()# um
        # print(pos)
        for istep in range(Steps):
            self._set_ui_value('ZMPosition', pos[istep])
            self.AOtask.write(pos[istep] * 0.1, auto_start = True)
            self.AOtask.wait_until_done(timeout = 0.005)
            self._set_ui_value('ZMcurrent', pos[istep])
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
        write_breadcrumb('DO_VIBRATOME_START_BEGIN', log=self.log)
        if not (SIM or self.SIM):
            settingtask = daq.Task('vibratome')
            # print(self.VibEnable)
            write_breadcrumb('DO_VIBRATOME_ADD_CHAN_BEFORE', log=self.log, detail=f'line={self.VibEnable}')
            settingtask.do_channels.add_do_chan(lines=self.VibEnable,
            line_grouping=LineGrouping.CHAN_PER_LINE)
            write_breadcrumb('DO_VIBRATOME_ADD_CHAN_AFTER', log=self.log)
            write_breadcrumb('DO_VIBRATOME_WRITE_BEFORE', log=self.log, detail='value=1')
            settingtask.write(1, auto_start = True)
            write_breadcrumb('DO_VIBRATOME_WRITE_AFTER', log=self.log)
            write_breadcrumb('DO_VIBRATOME_WAIT_BEFORE', log=self.log)
            settingtask.wait_until_done(timeout = 0.1)
            write_breadcrumb('DO_VIBRATOME_WAIT_AFTER', log=self.log)
            settingtask.stop()
            settingtask.close()
            # print('here')
            write_breadcrumb('DO_VIBRATOME_PUMP_ON_BEFORE', log=self.log)
            self.Pump_on()
            write_breadcrumb('DO_VIBRATOME_PUMP_ON_AFTER', log=self.log)
        self.DOBackQueue.put(0)
        write_breadcrumb('DO_VIBRATOME_START_DONE', log=self.log)
        
    def stopVibratome(self):
        write_breadcrumb('DO_VIBRATOME_STOP_BEGIN', log=self.log)
        if not (SIM or self.SIM):
            settingtask = daq.Task('vibratome')
            write_breadcrumb('DO_VIBRATOME_ADD_CHAN_BEFORE', log=self.log, detail=f'line={self.VibEnable}')
            settingtask.do_channels.add_do_chan(lines=self.VibEnable,
            line_grouping=LineGrouping.CHAN_PER_LINE)
            write_breadcrumb('DO_VIBRATOME_ADD_CHAN_AFTER', log=self.log)
            write_breadcrumb('DO_VIBRATOME_WRITE_BEFORE', log=self.log, detail='value=0')
            settingtask.write(0, auto_start = True)
            write_breadcrumb('DO_VIBRATOME_WRITE_AFTER', log=self.log)
            write_breadcrumb('DO_VIBRATOME_WAIT_BEFORE', log=self.log)
            settingtask.wait_until_done(timeout = 0.1)
            write_breadcrumb('DO_VIBRATOME_WAIT_AFTER', log=self.log)
            settingtask.stop()
            settingtask.close()
            #self.Pump_off()
        self.DOBackQueue.put(0)
        write_breadcrumb('DO_VIBRATOME_STOP_DONE', log=self.log)

    
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