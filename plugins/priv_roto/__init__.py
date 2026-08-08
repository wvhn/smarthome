#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2013 KNX-User-Forum e.V.            http://knx-user-forum.de/
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging
import time
from lib.model.smartplugin import *
from lib.item import Items
from datetime import datetime, timedelta
from lib.shtime import Shtime

PLUGIN_ID = 'Roto'
# Direction
UP = 0
DOWN = 1
OFF = 2
# values for Tebis TS actor
MOVEUP = 4
MOVEDOWN = 8
STEPUP = 7
STEPDOWN = 11
MOVEUP_RELEASE = 6
MOVEDOWN_RELEASE = 10
# roto mode: 
# LISTENING if shutter gets controlled manually then compute positions but do not send actor commands
# ACTIVE: send actor commands (used for positioning via item_pos ore item_angle)
LISTENING = 0
ACTIVE = 1
# angle values
OPEN = 0
CLOSED = 90

class Roto(SmartPlugin):

    ALLOW_MULTIINSTANCE = False
    PLUGIN_VERSION = "1.6.2"

    def __init__(self, smarthome):
        self.logger.info('Init roto plugin')

        self.logger.debug(f"init {__name__}")

        self.alive = False
        self._sh = smarthome
        self.itemsApi = Items.get_instance()
        self.__roto_items = {}

    def run(self):
        self.alive = True
        count_items = 0
        # register all items <item.tree>.Roto using the plugin
        for item in self.itemsApi.find_items("roto_plugin"):
            if item.conf["roto_plugin"] == "active":
                try:
                    roto_item = RotoItem(self._sh, item)
                    self.__roto_items[roto_item.id] = roto_item
                    count_items += 1
                except ValueError as ex:
                    self.logger.error("Item: {0}: {1}".format(item.id(), str(ex)))

        self.logger.info("Found {0} Items using the roto plugin".format(count_items))
        self.logger.info("--------------------   Roto Plugin initialization finished   --------------------")

    def stop(self):
        self.alive = False
        
    # get the plugin attributes from the Roto item
    def parse_item(self, item):
        if 'roto_plugin' in item.conf and item.conf["roto_plugin"] == "active":
            item.expand_relativepathes('roto_move', '', '')
            item.expand_relativepathes('roto_position', '', '')
            item.expand_relativepathes('roto_position_set', '', '')
            item.expand_relativepathes('roto_angle', '', '')
            item.expand_relativepathes('roto_angle_set', '', '')
            item.expand_relativepathes('roto_actor_move', '', '')
            self.logger.debug("parse item: {0}".format(item))
            return self.update_item
        else:
            return None

    def parse_logic(self, logic):
        if 'xxx' in logic.conf:
            # self.function(logic['name'])
            pass

    def update_item(self, item, caller=None, source=None, dest=None):
        orig_caller, orig_source, orig_item = self.get_original_caller(self._sh, caller, source, item)
        # ignore internal item changes in order to avoid infinite loops
        if orig_caller == PLUGIN_ID or caller == PLUGIN_ID:
          self.logger.debug("Skipping self-induced changes")
          return

        item_source = self._sh.return_item(source)
        self.logger.info("update roto_item: {0} orig_caller: {1} source: {2} item_source: {3}".format(item.id(), orig_caller, source, item_source))
        if item.id() in self.__roto_items:
            roto_item = self.__roto_items[item.id()]
        else:
            return

        item_value = item_source()
        item_last_value = item_source.property.last_value
        
        # listen to manual control by physical pushbuttons or visu control buttons
        # some long move commands seem to get lost. So make sure they are recognized at least by button release
        if (source == item.conf['roto_move']):
            self.logger.debug("{0}: new value: {1} lastvalue: {2} ".format(item_source, item_value, item_last_value))
            if item_value == MOVEUP_RELEASE:
                if item_last_value != MOVEUP:
                    item_value = MOVEUP
                    self.logger.debug("{0}: move up command changed to {1}". format(item_source, item_value))
                else:
                    # item value already correct
                    return
            elif item_value == MOVEDOWN_RELEASE:
                if item_last_value != MOVEDOWN:
                    item_value = MOVEDOWN
                    self.logger.debug("{0}: move down command changed to {1}". format(item_source, item_value))
                else:
                    # item value already correct
                    return
                
            # self.logger.debug("{0}: updated with value {1} from last value {2} ".format(item_source, item_value, item_last_value))
            if (item_value == MOVEUP):
                roto_item.roto_up_manual()
            elif (item_value == STEPUP):
                roto_item.roto_step_up_manual()
            elif (item_value == MOVEDOWN):
                roto_item.roto_down_manual()
            elif (item_value == STEPDOWN):
                roto_item.roto_step_down_manual()
                
        # control via position item
        if (source == item.conf['roto_position_set']):
            # self.logger.debug("roto position set item updated with value {0} ".format(item_value))
            position = 0
            if caller != 'Eval':
                position = item_value
            else:
                position = orig_item()
            self.logger.debug("{0} set position: {1} ".format(item_source, position))
            #self.logger.info("roto set position orig_caller: {0}".format(orig_caller))
            roto_item.roto_position(position)

        # control via angle item
        if (source == item.conf['roto_angle_set']):
            #self.logger.debug("{0} updated with value {1} ".format(item_source, item_value))
            angle = 0
            if caller != 'Eval':
                angle = item_value
            else:
                angle = orig_item()
            self.logger.debug("{0} set angle: {1}".format(item_source, angle))
            #self.logger.info("roto set position orig_caller: {0}".format(orig_caller))
            roto_item.roto_angle(angle)

    # determine original caller/source
    # smarthome: instance of smarthome.py
    # caller: caller
    # source: source
    def get_original_caller(self, smarthome, caller, source, item=None):
        original_caller = caller
        original_source = source
        original_item = item
        while original_caller == "Eval":
            original_item = smarthome.return_item(original_source)
            if original_item is None:
                break
            original_changed_by = original_item.changed_by()
            if ":" not in original_changed_by:
                break
            original_caller, __, original_source = original_changed_by.partition(":")
        if item is None:
            return original_caller, original_source
        else:
            return original_caller, original_source, original_item


# Class
class RotoItem:
    # return item id
    @property
    def id(self):
        return self.__id

    # time counter
    @property
    def time_on(self):
        return self.__time_on

    @time_on.setter
    def time_on(self, value):
        self.__time_on = value

    # time counter
    @property
    def time_off(self):
        return self.__time_off

    @time_off.setter
    def time_off(self, value):
        self.__time_off = value

    @property
    def time_up(self):
        return self.__time_up

    @property
    def time_down(self):
        return self.__time_down

    @property
    def item_move(self):
        return self.__item_move

    # position counter
    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, value):
        self.__position = value

    # angle counter
    @property
    def angle(self):
        return self.__angle

    @angle.setter
    def angle(self, value):
        self.__angle = value
        
    @property
    def hysteresis(self):
        return self.__hysteresis

    # return instance of smarthome.py class
    @property
    def sh(self):
        return self.__sh

    # Constructor
    # smarthome: instance of smarthome.py
    # item: item to use
    def __init__(self, smarthome, item):
        self.logger = logging.getLogger(__name__)
        self.__sh = smarthome
        self.__item = item
        self.__id = self.__item.id()
        self.__name = str(self.__item)
        self.__timezone = Shtime.get_instance().tzinfo()
        self.__time_on = datetime.now(self.__timezone)
        self.__time_off = datetime.now(self.__timezone)
        self.__time_last_loop = datetime.now(self.__timezone)

        self.__time_up = 60
        if 'roto_time_up' in item.conf:
            self.__time_up = int(item.conf['roto_time_up'])

        self.__time_down = 60
        if 'roto_time_down' in item.conf:
            self.__time_down = int(item.conf['roto_time_down'])

        self.__angle_step = 10
        if 'roto_angle_step' in item.conf:
            self.__angle_step = int(item.conf['roto_angle_step'])

        self.__angle_hyst = 0
        if 'roto_angle_hyst' in item.conf:
            self.__angle_hyst = int(item.conf['roto_angle_hyst'])

        self.__cycle_time = 5
        if 'roto_cycle_time' in item.conf:
            self.__cycle_time = int(item.conf['roto_cycle_time'])

        if 'roto_actor_move' in item.conf:
            self.__item_move = self.__sh.return_item(item.conf['roto_actor_move'])
        else:
            self.logger.error("{0}: roto actor_move item missing or faulty".format(self.__id))

        # items for actual and set values of the shutter position
        if 'roto_position' in item.conf:
            self.__item_position = self.__sh.return_item(item.conf['roto_position'])
        else:
            self.logger.error("{0}: roto position item missing or faulty".format(self.__id))

        if 'roto_position_set' in item.conf:
            self.__item_position_set = self.__sh.return_item(item.conf['roto_position_set'])
        else:
            self.logger.error("{0}: roto position_set item missing or faulty".format(self.__id))

        # items for actual and set value of the shutter angle
        if 'roto_angle' in item.conf:
            self.__item_angle = self.__sh.return_item(item.conf['roto_angle'])
        else:
            self.logger.error("{0}: roto angle item missing or faulty".format(self.__id))

        if 'roto_angle_set' in item.conf:
            self.__item_angle_set = self.__sh.return_item(item.conf['roto_angle_set'])
        else:
            self.logger.error("{0}: roto angle set item missing or faulty".format(self.__id))

        self.__delays = []
        self.__direction = OFF
        self.__position = self.__item_position()
        self.__item_position_set(self.__position)
        self.__position_time = self.__time_up / 100 * self.__position
        self.__direction = OFF
        self.__angle = self.__item_angle()
        self.__item_angle_set(self.__angle)
        self.__hysteresis = self.__angle_hyst
        self.logger.debug("item {0} initialized with parameters time_up: {1}, time_down: {2}, angle_Step: {3}, angle_hyst: {4}, cycle_time: {5}".format(self.__id, self.__time_up, self.__time_down, self.__angle_step, self.__angle_hyst, self.__cycle_time))

    def roto_position(self, position):
        if self.__direction != OFF:
            self.roto_stop(ACTIVE)
            time.sleep(2)
            if self.__direction != OFF:
                self.logger.info("{0}: roto position can not be set since shutter is already running: {1}".format(self.__id, self.__position))
                return

        new_pos = position
        old_pos = self.__position

        self.logger.debug("{0}: roto_position old:{1} new:{2}".format(self.__id, old_pos, new_pos))  

        # Downward travel
        if new_pos > old_pos:
            diff_pos = new_pos - old_pos
            diff_time = self.__time_down / 100 * diff_pos
            # ignore small changes below minimum cycle time
            if diff_time > 1:
                self.roto_down(diff_time, ACTIVE)

        # Upward travel:
        elif new_pos < old_pos:
            diff_pos = old_pos - new_pos
            diff_time = self.__time_up / 100 * diff_pos
            # ignore small changes below minimum cycle time
            if diff_time > 1:
                self.roto_up(diff_time, ACTIVE)

    def roto_up(self, travel_time, mode):
        if self.__direction != OFF:
            self.roto_stop(mode)
            #time.sleep(2)

        if mode == ACTIVE:
            self.__item_move(MOVEUP, caller = PLUGIN_ID)
        self.__direction = UP
        self.__time_on = datetime.now(self.__timezone)
        self.__time_last_loop = datetime.now(self.__timezone)
        self.roto_add_delay(UP, travel_time, mode)
        self.__angle = OPEN
        self.__item_angle(self.__angle, caller = PLUGIN_ID)

    def roto_down(self, travel_time, mode):
        if self.__direction != OFF:
            self.roto_stop(mode)
 
        if mode == ACTIVE:
            self.__item_move(MOVEDOWN, caller = PLUGIN_ID)
        self.__direction = DOWN
        self.__time_on = datetime.now(self.__timezone)
        self.__time_last_loop = datetime.now(self.__timezone)
        self.roto_add_delay(DOWN, travel_time, mode)
        self.__angle = CLOSED
        self.__item_angle(self.__angle, caller = PLUGIN_ID)
        self.__hysteresis = self.__angle_hyst

    # stop movement
    # mode = ACTIVE: stop movement actively
    # mode = LISTENING: clear variables after manual stop
    def roto_stop(self, mode):
        if self.__direction != OFF:
            if mode == ACTIVE:
                 self.__item_move(STEPUP, caller = PLUGIN_ID)
            self.logger.debug("{0}: Stop in position: {1}".format(self.__id, self.__position))
            self.__delays = []
            self.__direction = OFF
            
    # -------------------------------------------------------------------------------------------
    # Handling of manual commands (physical pushbutton or visu) received via item_move
    # -------------------------------------------------------------------------------------------
    # mode = LISTENING: do not actively control but keep status information up to date
    def roto_up_manual(self):
        self.roto_up(self.__time_up, LISTENING)

    def roto_down_manual(self):
        self.roto_down(self.__time_down, LISTENING)

    def roto_step_up_manual(self):
        increment = 0
        if self.__direction == OFF:
            increment = self.__angle_step
        self.roto_stop(LISTENING)
        old_angle = self.__angle
        if old_angle == CLOSED and self.__hysteresis > 0:
            self.__hysteresis -= 1
        else:
            self.__angle = max(OPEN, old_angle - increment)
            self.__item_angle(self.__angle, caller = PLUGIN_ID)

    def roto_step_down_manual(self):
        increment = 0
        if self.__direction == OFF:
            increment = self.__angle_step
        self.roto_stop(LISTENING)
        old_angle = self.__angle
        self.__angle = min(CLOSED, old_angle + increment)
        self.__item_angle(self.__angle, caller = PLUGIN_ID)
        if old_angle == CLOSED and self.__hysteresis < self.__angle_hyst:
            self.__hysteresis += 1

    # -------------------------------------------------------------------------------------------
    # Position and angle calculation and control functions
    # -------------------------------------------------------------------------------------------
    def roto_add_delay(self, direction, travel_time, mode):
        new_delay = {}
        new_delay.update({'delay': travel_time})
        new_delay.update({'direction': direction})
        new_delay.update({'mode': mode})
        self.__delays.append(new_delay)
        self.logger.debug("{0}: roto added new delay: {1}".format(self.__id, new_delay))

        if self.__id not in self.__sh.scheduler:
            s = self.__sh.scheduler.add(self.__id, self.roto_loop, prio=5, offset = 2, cycle=int(self.__cycle_time))

    # sort array of delays and return the specified element in the sorted sequence
    # e.g. 0 = first, -1 = last ... 
    def roto_get_delay(self, element):
        # sort delays list
        from operator import itemgetter
        x_delays = [x for x in self.__delays]
        x_delays.sort(key=itemgetter('delay'), reverse=False)
        if len(x_delays) == 0: 
            return {}
        else:
            return x_delays[element]

    # Control loop to be called by the scheduler
    def roto_loop(self):
        #self.logger.debug("roto_loop: {0} entries registered in delays array".format(len(self.__delays)))
        # deactivate scheduler if no entries available
        if (len(self.__delays)) == 0:
            if self.__id in self.__sh.scheduler:
                self.logger.debug("{0}: roto_loop STOP scheduler".format(self.__id))
                self.__sh.scheduler.remove(self.__id)
                self.__direction = OFF
            else:
                self.logger.debug("{0}: roto_loop: scheduler found to remove".format(self.__id))
        else:
            time_on_sec = (datetime.now(self.__timezone) - self.__time_on).total_seconds()
            # get first delay
            x_delay = self.roto_get_delay(0)
            if x_delay == {}:
                self.logger.debug("{0} roto_loop: no entries in array x_delays".format(self.__id))
                return

            # Calculate shutter position by the travel time
            self.roto_calc_pos()
            self.__time_last_loop = datetime.now(self.__timezone)
            self.logger.debug("{0}: roto_loop Position: {1}".format(self.__id, self.__position))

            # stop movement if time reaches / exeeds the calculated delay
            # mode = ACTIVE: stop movement actively
            # mode = LISTENING: clear variables at the end of manually started full move (roto_up_manual / roto_down_manual)
            if self.__direction != OFF and time_on_sec >= x_delay['delay']:
                if x_delay['mode'] == ACTIVE:
                    self.__item_move(STEPUP, caller = PLUGIN_ID)
                self.__time_off = datetime.now(self.__timezone)
                self.__direction = OFF
                self.__delays.remove(x_delay)
                self.logger.debug("{0}: roto_loop finished at position: {1} ".format(self.__id, self.__position))
                # update angle_item 
                self.__item_angle(self.__angle, caller = PLUGIN_ID)
            #self.logger.info("roto_loop END")

    def roto_calc_pos(self):
        time_loop_sec = (datetime.now(self.__timezone) - self.__time_last_loop).total_seconds()
        if self.__time_on > self.__time_off:
            if self.__direction == DOWN:
                self.__position_time += time_loop_sec
                if self.__position_time > self.__time_down:
                    self.__position_time = self.__time_down
                self.__position = self.__position_time * 100 / self.__time_down

            elif self.__direction == UP:
                self.__position_time -= time_loop_sec
                if self.__position_time < 0:
                    self.__position_time = 0
                self.__position = self.__position_time * 100 / self.__time_up
            self.__item_position(self.__position, caller=PLUGIN_ID) # aktualisiere das Item
            return self.__position
        else:
            self.logger.error("{0}: Shutter position can not be calculated. time_on [1} <= time_off {2} ".format(self.__id, self.__time_on, self.__time_off))

    def roto_angle(self, angle):
        if self.__direction != OFF:
            # get last delay
            x_delay = self.roto_get_delay(-1)
            time_left = x_delay['delay'] - (datetime.now(self.__timezone) - self.__time_on).total_seconds() + 1
            if time_left > 1:
                _next= datetime.now(self.__timezone) + timedelta(seconds=time_left)
                self.logger.debug("roto_angle: time left for movement: {0}. Scheduler loaded with: {1} - now = {2}".format(time_left, _next, datetime.now(self.__timezone)))
                s = self.__sh.scheduler.add(self.__id + '_angle', self.roto_angle_delayed, prio=5, offset = 2, next=_next)
                return
            else: 
                # self.roto_stop(ACTIVE)
                self.logger.debug("roto_angle: waiting 2 seconds for last movement to stop")
                time.sleep(2)
                if self.__direction != OFF:
                    self.logger.info("{0}: roto position can not be set since shutter is already running: {1}".format(self.__id, self.__angle))
                    return

        new_pos = angle
        if new_pos > CLOSED:
            new_pos = CLOSED
        elif new_pos < OPEN:
            new_pos = OPEN
        old_pos = self.__angle

        self.logger.debug("{0}: roto_angle calculated angles: old:{1} new:{2}".format(self.__id, old_pos, new_pos))

        diff_pos = new_pos - old_pos
        direction = 1
        if diff_pos > 0:
            command = STEPDOWN
        elif diff_pos < 0:
            command = STEPUP
            direction = -1
        else:
            return
        
        # some shutters have an angle hysteresis in stepping up mode
        if direction == -1 and self.__hysteresis > 0 and self.__angle == CLOSED:
            count = 0
            while self.__hysteresis > 0:
                self.__item_move(STEPUP, caller = PLUGIN_ID)
                time.sleep(1)
                self.__hysteresis -= 1
                count += 1
            self.logger.debug("{0}: roto_angle moved through hysteresis {1} steps".format(self.__id, count))

        diff_steps = abs(round(diff_pos / self.__angle_step, 0))
        self.logger.debug("{0}: roto_angle executing {1} steps to set angle".format(self.__id, diff_steps))
        count = 1
        while count <= diff_steps:
            self.__item_move(command, caller = PLUGIN_ID)
            self.__angle =  self.__angle + direction * self.__angle_step
            self.logger.debug("{0}: roto_angle moved angle to {1}".format(self.__id, self.__angle))        
            self.__item_angle(self.__angle, caller = PLUGIN_ID)
            time.sleep(1)
            count += 1
            
    def roto_angle_delayed(self):
        # get latest set value
        angle = self.__item_angle_set()
        self.logger.debug("{0} roto_angle_delayed: got angle set value: {1}".format(self.__id, angle))
        self.roto_angle(angle)

