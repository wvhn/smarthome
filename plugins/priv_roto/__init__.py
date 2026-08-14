#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2013 KNX-User-Forum e.V.            http://knx-user-forum.de/
#  Copyright 2020- ivande
#  Rewrite 2026-      <AUTHOR>                                  <EMAIL>
#########################################################################
#  This file is part of SmartHomeNG.
#  https://www.smarthomeNG.de
#  https://knx-user-forum.de/forum/supportforen/smarthome-py
#
#  SmartHomeNG is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHomeNG is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHomeNG. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import datetime
from dataclasses import dataclass
from enum import Enum, IntEnum

from lib.model.smartplugin import SmartPlugin

# angle bounds (degrees)
ANGLE_OPEN = 0
ANGLE_CLOSED = 90


class Direction(Enum):
    OFF = 'off'
    UP = 'up'
    DOWN = 'down'


class ActorCommand(IntEnum):
    """values expected by a Tebis-TS style shutter actor without position feedback"""

    MOVEUP = 4
    STEPUP = 7
    MOVEDOWN = 8
    STEPDOWN = 11
    MOVEUP_RELEASE = 6
    MOVEDOWN_RELEASE = 10


# some actors drop the initial long-move telegram and only reliably send the
# button-release telegram; if the corresponding move command was not already
# seen, the release is used as a fallback trigger for it (see _handle_move_command)
_RELEASE_FALLBACK = {
    ActorCommand.MOVEUP_RELEASE: ActorCommand.MOVEUP,
    ActorCommand.MOVEDOWN_RELEASE: ActorCommand.MOVEDOWN,
}


@dataclass
class _Step:
    """one queued actor pulse for stepwise angle control"""

    command: ActorCommand
    angle_delta: int = 0
    hyst_delta: int = 0


class Roto(SmartPlugin):
    """
    Calculates and drives the position/blade-angle of a shutter that is
    connected through an actor with no position feedback (single group
    address, move/step telegrams only).
    """

    PLUGIN_VERSION = '2.0.0'
    ALLOW_MULTIINSTANCE = False

    def __init__(self, sh=None, **kwargs):
        super().__init__()

        self._shutters: dict[str, RotoShutter] = {}
        self._item_to_shutter: dict[str, RotoShutter] = {}
        self._pause_item_path = self.get_parameter_value('pause_item')

    def run(self):
        self.alive = True
        self.logger.info(f'{len(self._shutters)} shutter(s) configured')
        if self._pause_item:
            self._pause_item(False, self.get_fullname())

    def stop(self):
        self.alive = False
        if self._pause_item:
            self._pause_item(True, self.get_fullname())
        self.scheduler_remove_all()

    def parse_item(self, item):
        if item.property.path == self._pause_item_path:
            self.logger.debug(f'pause item {item.property.path} registered')
            self._pause_item = item
            self.add_item(item, updating=True)
            return self.update_item

        if not self.has_iattr(item.conf, 'roto_plugin'):
            return None
        if self.get_iattr_value(item.conf, 'roto_plugin') != 'active':
            return None

        # the config item itself never receives updates, it only carries the
        # per-shutter parameters and anchors the sibling lookup below
        self.add_item(item, config_data_dict={'role': 'config'})

        try:
            shutter = RotoShutter(self, item)
        except (AttributeError, KeyError, ValueError) as e:
            self.logger.error(f'{item.property.path}: could not set up shutter - {e}')
            return None

        self._shutters[item.property.path] = shutter
        for control_item in shutter.control_items:
            self.add_item(
                control_item, config_data_dict={'role': 'control', 'shutter': item.property.path}, updating=True
            )
            control_item.add_method_trigger(self.update_item)
            self._item_to_shutter[control_item.property.path] = shutter

        return None

    def update_item(self, item, caller=None, source=None, dest=None):
        if item is self._pause_item:
            if caller != self.get_shortname():
                self.logger.debug(f'pause item changed to {item()}')
                if item() and self.alive:
                    self.stop()
                elif not item() and not self.alive:
                    self.run()
            return

        if not self.alive or caller == self.get_fullname():
            return

        shutter = self._item_to_shutter.get(item.property.path)
        if shutter is None:
            return

        if item is shutter.item_move:
            self._handle_move_command(shutter, item)
        elif item in (shutter.item_position_set, shutter.item_angle_set):
            shutter.apply_setpoints()

    def _handle_move_command(self, shutter, item):
        value = item()
        replacement = _RELEASE_FALLBACK.get(value)
        if replacement is not None:
            if item.property.last_value == replacement:
                # long-move telegram already seen, ignore the release echo
                return
            value = replacement

        if value == ActorCommand.MOVEUP:
            shutter.move_up_manual()
        elif value == ActorCommand.MOVEDOWN:
            shutter.move_down_manual()
        elif value == ActorCommand.STEPUP:
            shutter.step_up_manual()
        elif value == ActorCommand.STEPDOWN:
            shutter.step_down_manual()


class RotoShutter:
    """Position/angle model and actor control for a single shutter."""

    def __init__(self, plugin: Roto, config_item):
        self.plugin = plugin
        self.logger = plugin.logger
        self.id = config_item.property.path

        parent = config_item.return_parent()
        if parent is None:
            raise ValueError('config item has no parent; expected siblings move/pos/winkel')
        try:
            self.item_move = parent['move']
            self.item_position = parent['pos']
            self.item_position_set = parent['pos']['soll']
            self.item_angle = parent['winkel']
            self.item_angle_set = parent['winkel']['soll']
        except KeyError as e:
            raise ValueError(f'required sibling item {e} not found under {parent.property.path}') from e

        conf = config_item.conf
        self._time_up = float(self.plugin.get_iattr_value(conf, 'roto_time_up', 60))
        self._time_down = float(self.plugin.get_iattr_value(conf, 'roto_time_down', 60))
        self._angle_step = float(self.plugin.get_iattr_value(conf, 'roto_angle_step', 10))
        self._angle_hyst = int(self.plugin.get_iattr_value(conf, 'roto_angle_hyst', 0))
        self._cycle_time = int(self.plugin.get_iattr_value(conf, 'roto_cycle_time', 5))

        self._direction = Direction.OFF
        self._move_started = self.plugin.now()
        self._loop_last_run = self._move_started
        self._pending_stop: dict | None = None
        self._pending_steps: list[_Step] = []

        self._position = self.item_position() or 0
        self._position_time = self._time_up / 100 * self._position
        self.item_position_set(self._position, caller=self.plugin.get_fullname())

        self._angle = self.item_angle() or 0
        self._hysteresis = self._angle_hyst
        self.item_angle_set(self._angle, caller=self.plugin.get_fullname())

        self.logger.debug(
            f'{self.id}: initialized time_up={self._time_up} time_down={self._time_down} '
            f'angle_step={self._angle_step} angle_hyst={self._angle_hyst} cycle_time={self._cycle_time}'
        )

    @property
    def control_items(self):
        return (self.item_move, self.item_position_set, self.item_angle_set)

    # -------------------------------------------------------------------
    # commands driven by pos.soll / winkel.soll (mode ACTIVE: plugin drives the actor)
    # -------------------------------------------------------------------

    def apply_setpoints(self):
        """
        Called for a write to *either* pos.soll or winkel.soll.
        """
        self.set_position(self.item_position_set())
        self.set_angle(self.item_angle_set())

    def set_position(self, position):
        if self._direction != Direction.OFF:
            self._stop(active=True)

        diff = position - self._position
        if abs(diff) < 1e-9:
            return
        if diff > 0:
            travel_time = self._time_down / 100 * diff
            if travel_time > 1:
                self._move(Direction.DOWN, travel_time, active=True)
        else:
            travel_time = self._time_up / 100 * -diff
            if travel_time > 1:
                self._move(Direction.UP, travel_time, active=True)

    def set_angle(self, angle):
        angle = max(ANGLE_OPEN, min(ANGLE_CLOSED, angle))

        if self._direction != Direction.OFF:
            # a full move is in progress; retry once it is expected to be done
            # instead of blocking the caller until then
            elapsed = (self.plugin.now() - self._move_started).total_seconds()
            remaining = (self._pending_stop['travel_time'] - elapsed) if self._pending_stop else 0
            next_try = self.plugin.now() + datetime.timedelta(seconds=max(1, remaining + 1))
            self.plugin.scheduler_add(f'{self.id}_angle', self._retry_set_angle, prio=5, next=next_try)
            return

        diff = angle - self._angle
        if diff == 0:
            return

        direction = -1 if diff < 0 else 1
        command = ActorCommand.STEPUP if direction == -1 else ActorCommand.STEPDOWN
        step_count = round(abs(diff) / self._angle_step)

        steps = []
        if direction == -1 and self._hysteresis > 0 and self._angle == ANGLE_CLOSED:
            steps.extend(_Step(ActorCommand.STEPUP, hyst_delta=-1) for _ in range(self._hysteresis))
        steps.extend(_Step(command, angle_delta=direction * self._angle_step) for _ in range(step_count))

        self._queue_steps(steps)

    def _retry_set_angle(self):
        # re-read the current setpoint rather than the value captured when the
        # retry was scheduled, in case it changed again in the meantime
        self.set_angle(self.item_angle_set())

    # -------------------------------------------------------------------
    # manual commands from a physical pushbutton or visu (mode LISTENING:
    # the actor already executed the command on its own, the plugin only
    # keeps its position/angle bookkeeping in sync)
    # -------------------------------------------------------------------

    def move_up_manual(self):
        self._move(Direction.UP, self._time_up, active=False)
        self.item_position_set(0, caller=self.plugin.get_fullname())

    def move_down_manual(self):
        self._move(Direction.DOWN, self._time_down, active=False)
        self.item_position_set(100, caller=self.plugin.get_fullname())

    def step_up_manual(self):
        increment = self._angle_step if self._direction == Direction.OFF else 0
        self._stop(active=False)
        if self._angle == ANGLE_CLOSED and self._hysteresis > 0:
            self._hysteresis -= 1
        else:
            self._angle = max(ANGLE_OPEN, self._angle - increment)
            self.item_angle(self._angle, caller=self.plugin.get_fullname())

    def step_down_manual(self):
        increment = self._angle_step if self._direction == Direction.OFF else 0
        self._stop(active=False)
        old_angle = self._angle
        self._angle = min(ANGLE_CLOSED, self._angle + increment)
        self.item_angle(self._angle, caller=self.plugin.get_fullname())
        if old_angle == ANGLE_CLOSED and self._hysteresis < self._angle_hyst:
            self._hysteresis += 1

    # -------------------------------------------------------------------
    # full-move control + position tracking, driven by a per-shutter scheduler
    # -------------------------------------------------------------------

    def _move(self, direction: Direction, travel_time: float, active: bool):
        if self._direction != Direction.OFF:
            self._stop(active)
        # a full move overrides any in-flight stepwise angle adjustment
        self._pending_steps.clear()

        if active:
            command = ActorCommand.MOVEDOWN if direction == Direction.DOWN else ActorCommand.MOVEUP
            self.item_move(command, caller=self.plugin.get_fullname())

        self._direction = direction
        self._move_started = self.plugin.now()
        self._loop_last_run = self._move_started
        self._pending_stop = {'travel_time': travel_time, 'active': active}

        self._angle = ANGLE_CLOSED if direction == Direction.DOWN else ANGLE_OPEN
        self.item_angle(self._angle, caller=self.plugin.get_fullname())
        if direction == Direction.DOWN:
            self._hysteresis = self._angle_hyst

        if self.id not in self.plugin.scheduler_get_all():
            self.plugin.scheduler_add(self.id, self._loop, prio=5, offset=2, cycle=self._cycle_time)

    def _stop(self, active: bool):
        if self._direction == Direction.OFF:
            return
        if active:
            self.item_move(ActorCommand.STEPUP, caller=self.plugin.get_fullname())
        else:
            self.item_position_set(self._position, caller=self.plugin.get_fullname())
        self._pending_stop = None
        self._direction = Direction.OFF

    def _loop(self):
        if self._pending_stop is None:
            self.plugin.scheduler_remove(self.id)
            self._direction = Direction.OFF
            return

        now = self.plugin.now()
        self._update_position(now)
        self._loop_last_run = now

        elapsed = (now - self._move_started).total_seconds()
        if elapsed >= self._pending_stop['travel_time']:
            self._stop(active=self._pending_stop['active'])
            self.item_angle(self._angle, caller=self.plugin.get_fullname())

    def _update_position(self, now):
        elapsed = (now - self._loop_last_run).total_seconds()
        if self._direction == Direction.DOWN:
            self._position_time = min(self._position_time + elapsed, self._time_down)
            self._position = self._position_time * 100 / self._time_down
        elif self._direction == Direction.UP:
            self._position_time = max(self._position_time - elapsed, 0)
            self._position = self._position_time * 100 / self._time_up
        else:
            return
        self.item_position(self._position, caller=self.plugin.get_fullname())

    # -------------------------------------------------------------------
    # stepwise angle control, driven by a per-shutter scheduler (one pulse/second)
    # -------------------------------------------------------------------

    def _queue_steps(self, steps: list[_Step]):
        if not steps:
            return
        already_running = bool(self._pending_steps)
        self._pending_steps.extend(steps)
        if not already_running:
            self.plugin.scheduler_add(f'{self.id}_step', self._step_tick, prio=5, offset=0, cycle=1)

    def _step_tick(self):
        if not self._pending_steps:
            self.plugin.scheduler_remove(f'{self.id}_step')
            return

        step = self._pending_steps.pop(0)
        self.item_move(step.command, caller=self.plugin.get_fullname())
        if step.angle_delta:
            self._angle += step.angle_delta
            self.item_angle(self._angle, caller=self.plugin.get_fullname())
        if step.hyst_delta:
            self._hysteresis = max(0, self._hysteresis + step.hyst_delta)

        if not self._pending_steps:
            self.plugin.scheduler_remove(f'{self.id}_step')
