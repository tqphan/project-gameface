# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import tkinter
from functools import partial

import customtkinter
import numpy as np
from PIL import Image

from src.config_manager import ConfigManager
from src.controllers import MouseController
from src.gui.balloon import Balloon
from src.gui.frames.safe_disposable_frame import SafeDisposableFrame

logger = logging.getLogger("PageCursor")
MAX_ROWS = 3
HELP_ICON_SIZE = (18, 18)
MAX_HOLD_TRIG = 2000


class FrameSelectGesture(SafeDisposableFrame):

    def __init__(
        self,
        master,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.grid_rowconfigure(MAX_ROWS, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.slider_dragging = False
        self.help_icon = customtkinter.CTkImage(
            Image.open("assets/images/help.png").resize(HELP_ICON_SIZE),
            size=HELP_ICON_SIZE)

        self.shared_info_balloon = Balloon(
            self, image_path="assets/images/balloon.png")

        # Slider divs
        self.divs = self.create_divs({
            "Move up": ["spd_up", "", 0, 100],
            "Move down": ["spd_down", "", 0, 100],
            "Move right": ["spd_right", "", 0, 100],
            "Move left": ["spd_left", "", 0, 100],
            "(Advanced) Smooth pointer": [
                "pointer_smooth",
                "Controls the smoothness of the\nmouse cursor. Enables the user\nto reduce jitteriness",
                1, 100
            ],
            "(Advanced) Smooth blendshapes": [
                "shape_smooth", "Reduces the flickering of the action\ntrigger",
                1, 100
            ],
            "(Advanced) Hold trigger delay(ms)": [
                "hold_trigger_ms",
                "Controls how long the user should\nhold a gesture in milliseconds\nfor an action to trigger",
                1, MAX_HOLD_TRIG
            ]
        })

        self.load_initial_config()

    def load_initial_config(self):
        """Load default from config and set the UI
        """

        for cfg_name, div in self.divs.items():

            cfg_value = int(
                np.clip(ConfigManager().config[cfg_name],
                        a_min=1,
                        a_max=MAX_HOLD_TRIG))
            div["slider"].set(cfg_value)
            # Temporary remove trace, adjust the value and put it back
            div["entry_var"].trace_vdelete("w", div["entry_trace_id"])
            div["entry_var"].set(cfg_value)
            div["entry_trace_id"] = div["entry_var"].trace(
                "w", div["entry_trace_fn"])

    def create_divs(self, directions: dict):
        out_dict = {}

        for idx, (show_name, (cfg_name, balloon_text, slider_min,
                              slider_max)) in enumerate(directions.items()):

            help_image = self.help_icon if balloon_text != "" else None
            # Label
            label = customtkinter.CTkLabel(master=self,
                                           image=help_image,
                                           compound='right',
                                           text=show_name,
                                           justify=tkinter.LEFT)
            label.cget("font").configure(weight='bold')
            label.grid(row=idx, column=0, padx=20, pady=(10, 10), sticky="nw")
            self.shared_info_balloon.register_widget(label, balloon_text)

            # Slider
            slider = customtkinter.CTkSlider(master=self,
                                             from_=slider_min,
                                             to=slider_max,
                                             width=250,
                                             number_of_steps=99,
                                             command=partial(
                                                 self.slider_drag_callback,
                                                 cfg_name))
            slider.bind("<Button-1>",
                        partial(self.slider_mouse_down_callback, cfg_name))
            slider.bind("<ButtonRelease-1>",
                        partial(self.slider_mouse_up_callback, cfg_name))
            slider.grid(row=idx, column=0, padx=30, pady=(40, 10), sticky="nw")

            # Number entry
            entry_var = tkinter.StringVar()
            entry_trace_fn = partial(self.entry_changed_callback, cfg_name,
                                     slider_min, slider_max)
            entry_var_trace_id = entry_var.trace("w", entry_trace_fn)
            entry = customtkinter.CTkEntry(
                master=self,
                validate='all',
                textvariable=entry_var,
                #validatecommand=vcmd,
                width=62)
            entry.grid(row=idx,
                       column=0,
                       padx=(300, 5),
                       pady=(34, 10),
                       sticky="nw")

            out_dict[cfg_name] = {
                "label": label,
                "slider": slider,
                "entry": entry,
                "entry_var": entry_var,
                "entry_trace_id": entry_var_trace_id,
                "entry_trace_fn": entry_trace_fn
            }
        return out_dict

    def validate_entry_input(self, P, slider_min, slider_max):
        slider_min = int(slider_min)
        slider_max = int(slider_max)

        if str.isdigit(P):
            P = int(P)

            if P < slider_min:
                return False
            elif P > slider_max:
                return False

            return True
        else:
            return False

    def entry_changed_callback(self, div_name, slider_min, slider_max, var,
                               index, mode):
        """Update value with entery text 
        """
        is_valid_input = True
        div = self.divs[div_name]

        entry_value = div["entry_var"].get()

        # Check if valid input
        if not str.isdigit(entry_value):
            is_valid_input = False
        else:
            new_value = int(entry_value)
            if not new_value in range(slider_min, slider_max):
                is_valid_input = False

        # Update slider and config
        if is_valid_input:
            div["entry"].configure(fg_color="white")
            div["slider"].set(new_value)

            # Don't update config when dragging
            if not self.slider_dragging:
                ConfigManager().set_temp_config(field=div_name, value=new_value)
                ConfigManager().apply_config()
                MouseController().calc_smooth_kernel()
        else:
            div["entry"].configure(fg_color="#ee9e9d")

    def slider_drag_callback(self, div_name: str, new_value: str):
        """Update value when slider being drag
        """
        self.slider_dragging = True
        new_value = int(new_value)
        div = self.divs[div_name]
        div["entry_var"].set(new_value)

    def slider_mouse_down_callback(self, div_name: str, event):
        self.slider_dragging = True

    def slider_mouse_up_callback(self, div_name: str, event):
        self.slider_dragging = False
        div = self.divs[div_name]
        new_value = int(div["entry_var"].get())
        ConfigManager().set_temp_config(field=div_name, value=new_value)
        ConfigManager().apply_config()
        MouseController().calc_smooth_kernel()

    def inner_refresh_profile(self):
        self.load_initial_config()


class PageCursor(SafeDisposableFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.is_active = False
        self.task = {}

        # Top label.
        self.top_label = customtkinter.CTkLabel(master=self,
                                                text="Cursor speed")
        self.top_label.cget("font").configure(size=24)
        self.top_label.grid(row=0,
                            column=0,
                            padx=20,
                            pady=10,
                            sticky="nw",
                            columnspan=1)

        # Description.
        des_txt = "Mouse cursor moves with your head movement. Use this settings to adjust how fast your mouse moves in each direction."
        des_label = customtkinter.CTkLabel(master=self,
                                           text=des_txt,
                                           wraplength=300,
                                           justify=tkinter.LEFT)
        des_label.cget("font").configure(size=14)
        des_label.grid(row=1, column=0, padx=20, pady=5, sticky="nw")

        # Inner frame
        self.inner_frame = FrameSelectGesture(self)
        self.inner_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nw")

    def refresh_profile(self):
        self.inner_frame.inner_refresh_profile()
