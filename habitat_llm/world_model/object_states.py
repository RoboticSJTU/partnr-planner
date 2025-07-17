#!/usr/bin/env python3

# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree

from habitat.sims.habitat_simulator.object_state_machine import BooleanObjectState


class ObjectIsFilled(BooleanObjectState):
    """
    ObjectIsFilled state specifies whether an object is filled or empty.
    Following the pattern from habitat-lab/habitat/sims/habitat_simulator/object_state_machine.py
    """

    def __init__(self):
        super().__init__()
        self.name = "is_filled"
        self.display_name = "Is Full"
        self.display_name_true = "Full"
        self.display_name_false = "Empty"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return False


class ObjectIsClean(BooleanObjectState):
    """
    ObjectIsClean state specifies whether an object is clean or dirty.
    """

    def __init__(self):
        super().__init__()
        self.name = "is_clean"
        self.display_name = "Is Clean"
        self.display_name_true = "Clean"
        self.display_name_false = "Dirty"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return False


class ObjectIsOpened(BooleanObjectState):
    """
    ObjectIsOpen state specifies whether an object is opened or not.
    """

    def __init__(self):
        super().__init__()
        self.name = "is_opened"
        self.display_name = "Is Opened"
        self.display_name_true = "Opened"
        self.display_name_false = "Not Opened"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return False


class ObjectIsHeated(BooleanObjectState):
    """
    ObjectIsHeated state specifies whether an object is cold or heated.
    """

    def __init__(self):
        super().__init__()
        self.name = "is_heated"
        self.display_name = "Is Heated"
        self.display_name_true = "Heated"
        self.display_name_false = "Not Heated"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return False


class ObjectIsLightOn(BooleanObjectState):
    """
    ObjectIsLightOn state specifies whether an object is light on or off.
    """

    def __init__(self):
        super().__init__()
        self.name = "is_light_on"
        self.display_name = "Is Light On"
        self.display_name_true = "Light On"
        self.display_name_false = "Light Off"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return False


class ObjectIsTimerSet(BooleanObjectState):
    """
    ObjectIsTimerSet state specifies whether a timer for the object is setted or not.
    """

    def __init__(self):
        super().__init__()
        self.name = "is_timer_setted"
        self.display_name = "Is Timer Setted"
        self.display_name_true = "Timer Setted"
        self.display_name_false = "Timer Not Setted"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return False


class ObjectRequireWaterToClean(BooleanObjectState):
    """
    ObjectRequireWaterToClean state specifies whether an object require water to clean.
    """

    def __init__(self):
        super().__init__()
        self.name = "requires_water_to_clean"
        self.display_name = "Require Water To Clean"
        self.display_name_true = "Require Water To Clean"
        self.display_name_false = "Not Require Water To Clean"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return True
    

class ObjectIsCleaningTool(BooleanObjectState):
    """
    ObjectIsCleaningTool state specifies whether an object is a cleaning tool or not.
    """

    def __init__(self):
        super().__init__()
        self.name = "is_cleaning_tool"
        self.display_name = "Is A Cleaning Tool"
        self.display_name_true = "A Cleaning Tool"
        self.display_name_false = "Not A Cleaning Tool"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return True
    


class ObjectIsHeatingDevice(BooleanObjectState):
    """
    ObjectIsHeatingDevice state specifies whether an object is a heating device or not.
    """

    def __init__(self):
        super().__init__()
        self.name = "is_heating_device"
        self.display_name = "Is A Heating Device"
        self.display_name_true = "a heating device"
        self.display_name_false = "not a heating device"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return True
    

class ObjectHasFaucet(BooleanObjectState):
    """
    ObjectHasFaucet state specifies whether an object have faucet or not.
    """

    def __init__(self):
        super().__init__()
        self.name = "has_faucet"
        self.display_name = "Has Faucet"
        self.display_name_true = "has faucet"
        self.display_name_false = "not have any faucet"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return True
    

class ObjectCanBeOpened(BooleanObjectState):
    """
    ObjectCanBeOpened state specifies whether an object can be opened or not.
    """

    def __init__(self):
        super().__init__()
        self.name = "can_be_opened"
        self.display_name = "Can Be Opened"
        self.display_name_true = "can be opened"
        self.display_name_false = "cannot be opened"
        self.accepted_semantic_classes = []

    def default_value(self) -> bool:
        return True