"""
SSLE Operation Panel for MeerK40t Glass3D Plugin

Provides settings panel for SSLE operations.
"""

import wx


class SSLEOperationPanel(wx.Panel):
    """Settings panel for SSLE operations."""

    name = "SSLE"
    priority = 50

    def __init__(self, *args, context=None, node=None, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.node = node

        self.SetHelpText("ssle_panel")

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Title
        title = wx.StaticText(self, label="Subsurface Laser Engraving Settings")
        title.SetFont(title.GetFont().Bold())
        sizer.Add(title, 0, wx.ALL | wx.EXPAND, 10)

        # Laser Settings Box
        laser_box = wx.StaticBox(self, label="Laser Settings")
        laser_sizer = wx.StaticBoxSizer(laser_box, wx.VERTICAL)

        # Power
        power_sizer = wx.BoxSizer(wx.HORIZONTAL)
        power_sizer.Add(
            wx.StaticText(self, label="Power (%):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.power_ctrl = wx.SpinCtrlDouble(
            self, min=0, max=100, initial=50, inc=1
        )
        self.power_ctrl.SetDigits(1)
        power_sizer.Add(self.power_ctrl, 0, wx.LEFT, 5)
        laser_sizer.Add(power_sizer, 0, wx.ALL, 5)

        # Dwell time
        dwell_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dwell_sizer.Add(
            wx.StaticText(self, label="Dwell (ms):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.dwell_ctrl = wx.SpinCtrlDouble(
            self, min=0.1, max=100, initial=1.0, inc=0.1
        )
        self.dwell_ctrl.SetDigits(2)
        dwell_sizer.Add(self.dwell_ctrl, 0, wx.LEFT, 5)
        laser_sizer.Add(dwell_sizer, 0, wx.ALL, 5)

        # Frequency
        freq_sizer = wx.BoxSizer(wx.HORIZONTAL)
        freq_sizer.Add(
            wx.StaticText(self, label="Frequency (kHz):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.freq_ctrl = wx.SpinCtrlDouble(
            self, min=1, max=100, initial=30, inc=1
        )
        self.freq_ctrl.SetDigits(1)
        freq_sizer.Add(self.freq_ctrl, 0, wx.LEFT, 5)
        laser_sizer.Add(freq_sizer, 0, wx.ALL, 5)

        sizer.Add(laser_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Material Settings Box
        material_box = wx.StaticBox(self, label="Material Settings")
        material_sizer = wx.StaticBoxSizer(material_box, wx.VERTICAL)

        # Refractive index
        ri_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ri_sizer.Add(
            wx.StaticText(self, label="Refractive Index:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.ri_ctrl = wx.SpinCtrlDouble(
            self, min=1.0, max=3.0, initial=1.5, inc=0.01
        )
        self.ri_ctrl.SetDigits(2)
        ri_sizer.Add(self.ri_ctrl, 0, wx.LEFT, 5)
        material_sizer.Add(ri_sizer, 0, wx.ALL, 5)

        # Presets
        preset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        preset_sizer.Add(
            wx.StaticText(self, label="Preset:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.preset_choice = wx.Choice(
            self,
            choices=[
                "K9 Crystal (1.50)",
                "BK7 Glass (1.52)",
                "Fused Silica (1.46)",
                "Acrylic (1.49)",
                "Custom",
            ],
        )
        self.preset_choice.SetSelection(0)
        preset_sizer.Add(self.preset_choice, 0, wx.LEFT, 5)
        material_sizer.Add(preset_sizer, 0, wx.ALL, 5)

        sizer.Add(material_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Thermal Settings Box
        thermal_box = wx.StaticBox(self, label="Thermal Management")
        thermal_sizer = wx.StaticBoxSizer(thermal_box, wx.VERTICAL)

        # Pause interval
        pause_int_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pause_int_sizer.Add(
            wx.StaticText(self, label="Pause every:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.pause_interval_ctrl = wx.SpinCtrl(
            self, min=100, max=100000, initial=10000
        )
        pause_int_sizer.Add(self.pause_interval_ctrl, 0, wx.LEFT, 5)
        pause_int_sizer.Add(
            wx.StaticText(self, label="points"), 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5
        )
        thermal_sizer.Add(pause_int_sizer, 0, wx.ALL, 5)

        # Pause duration
        pause_dur_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pause_dur_sizer.Add(
            wx.StaticText(self, label="Pause duration:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.pause_duration_ctrl = wx.SpinCtrl(
            self, min=10, max=5000, initial=500
        )
        pause_dur_sizer.Add(self.pause_duration_ctrl, 0, wx.LEFT, 5)
        pause_dur_sizer.Add(
            wx.StaticText(self, label="ms"), 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5
        )
        thermal_sizer.Add(pause_dur_sizer, 0, wx.ALL, 5)

        sizer.Add(thermal_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)

        # Bind events
        self.preset_choice.Bind(wx.EVT_CHOICE, self.on_preset_change)
        self.power_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_power_change)
        self.dwell_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_dwell_change)
        self.freq_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_freq_change)
        self.ri_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_ri_change)
        self.pause_interval_ctrl.Bind(wx.EVT_SPINCTRL, self.on_pause_interval_change)
        self.pause_duration_ctrl.Bind(wx.EVT_SPINCTRL, self.on_pause_duration_change)

        # Load initial values
        self.load_values()

    def load_values(self):
        """Load values from the node."""
        if self.node is None:
            return

        # Power (stored as 0-1000, display as 0-100%)
        power = getattr(self.node, "power", 500)
        self.power_ctrl.SetValue(power / 10.0)

        # Dwell time
        dwell = getattr(self.node, "dwell_time", 1.0)
        self.dwell_ctrl.SetValue(dwell)

        # Frequency
        freq = getattr(self.node, "frequency", 30.0)
        self.freq_ctrl.SetValue(freq)

        # Refractive index
        ri = getattr(self.node, "refractive_index", 1.5)
        self.ri_ctrl.SetValue(ri)
        self.update_preset_from_ri(ri)

        # Thermal settings
        pause_pts = getattr(self.node, "thermal_pause_points", 10000)
        self.pause_interval_ctrl.SetValue(pause_pts)

        pause_ms = getattr(self.node, "thermal_pause_ms", 500)
        self.pause_duration_ctrl.SetValue(pause_ms)

    def update_preset_from_ri(self, ri):
        """Update preset choice based on refractive index."""
        presets = {1.50: 0, 1.52: 1, 1.46: 2, 1.49: 3}
        ri_rounded = round(ri, 2)
        if ri_rounded in presets:
            self.preset_choice.SetSelection(presets[ri_rounded])
        else:
            self.preset_choice.SetSelection(4)  # Custom

    def on_preset_change(self, event):
        """Update refractive index when preset changes."""
        presets = {0: 1.50, 1: 1.52, 2: 1.46, 3: 1.49}
        idx = self.preset_choice.GetSelection()
        if idx in presets:
            self.ri_ctrl.SetValue(presets[idx])
            self.on_ri_change(None)

    def on_power_change(self, event):
        """Handle power change."""
        if self.node is None:
            return
        self.node.power = int(self.power_ctrl.GetValue() * 10)
        self.node.updated()

    def on_dwell_change(self, event):
        """Handle dwell time change."""
        if self.node is None:
            return
        self.node.dwell_time = self.dwell_ctrl.GetValue()
        self.node.updated()

    def on_freq_change(self, event):
        """Handle frequency change."""
        if self.node is None:
            return
        self.node.frequency = self.freq_ctrl.GetValue()
        self.node.updated()

    def on_ri_change(self, event):
        """Handle refractive index change."""
        if self.node is None:
            return
        ri = self.ri_ctrl.GetValue()
        self.node.refractive_index = ri
        self.update_preset_from_ri(ri)
        self.node.updated()

    def on_pause_interval_change(self, event):
        """Handle thermal pause interval change."""
        if self.node is None:
            return
        self.node.thermal_pause_points = self.pause_interval_ctrl.GetValue()
        self.node.updated()

    def on_pause_duration_change(self, event):
        """Handle thermal pause duration change."""
        if self.node is None:
            return
        self.node.thermal_pause_ms = self.pause_duration_ctrl.GetValue()
        self.node.updated()

    def pane_show(self):
        """Called when panel is shown."""
        self.load_values()

    def pane_hide(self):
        """Called when panel is hidden."""
        pass
