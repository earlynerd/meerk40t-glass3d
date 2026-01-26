"""
PointCloud3D Property Panel for MeerK40t Glass3D Plugin

Displays properties and info for PointCloud3D elements.
"""

import wx


class PointCloudPropertyPanel(wx.Panel):
    """Property panel for PointCloud3D elements."""

    name = "PointCloud"
    priority = 50

    def __init__(self, *args, context=None, node=None, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self.context = context
        self.node = node

        self.SetHelpText("pointcloud_panel")

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Title
        title = wx.StaticText(self, label="PointCloud3D Properties")
        title.SetFont(title.GetFont().Bold())
        sizer.Add(title, 0, wx.ALL | wx.EXPAND, 10)

        # Info Box
        info_box = wx.StaticBox(self, label="Point Cloud Info")
        info_sizer = wx.StaticBoxSizer(info_box, wx.VERTICAL)

        # Points count
        self.points_label = wx.StaticText(self, label="Points: -")
        info_sizer.Add(self.points_label, 0, wx.ALL, 5)

        # Layers count
        self.layers_label = wx.StaticText(self, label="Layers: -")
        info_sizer.Add(self.layers_label, 0, wx.ALL, 5)

        # Dimensions
        self.dims_label = wx.StaticText(self, label="Size: - x - x - mm")
        info_sizer.Add(self.dims_label, 0, wx.ALL, 5)

        # Source file
        self.source_label = wx.StaticText(self, label="Source: -")
        info_sizer.Add(self.source_label, 0, wx.ALL, 5)

        # Strategy
        self.strategy_label = wx.StaticText(self, label="Strategy: -")
        info_sizer.Add(self.strategy_label, 0, wx.ALL, 5)

        # Spacing
        self.spacing_label = wx.StaticText(self, label="Spacing: - mm")
        info_sizer.Add(self.spacing_label, 0, wx.ALL, 5)

        sizer.Add(info_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Actions Box
        actions_box = wx.StaticBox(self, label="Actions")
        actions_sizer = wx.StaticBoxSizer(actions_box, wx.VERTICAL)

        # Regenerate button
        self.regen_btn = wx.Button(self, label="Regenerate Points...")
        actions_sizer.Add(self.regen_btn, 0, wx.ALL | wx.EXPAND, 5)

        # Optimize path button
        self.optimize_btn = wx.Button(self, label="Optimize Path")
        actions_sizer.Add(self.optimize_btn, 0, wx.ALL | wx.EXPAND, 5)

        # Export button
        self.export_btn = wx.Button(self, label="Export Points...")
        actions_sizer.Add(self.export_btn, 0, wx.ALL | wx.EXPAND, 5)

        sizer.Add(actions_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Estimated time box
        time_box = wx.StaticBox(self, label="Time Estimate")
        time_sizer = wx.StaticBoxSizer(time_box, wx.VERTICAL)

        self.time_label = wx.StaticText(self, label="Estimated time: --:--:--")
        time_sizer.Add(self.time_label, 0, wx.ALL, 5)

        sizer.Add(time_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)

        # Bind events
        self.regen_btn.Bind(wx.EVT_BUTTON, self.on_regenerate)
        self.optimize_btn.Bind(wx.EVT_BUTTON, self.on_optimize)
        self.export_btn.Bind(wx.EVT_BUTTON, self.on_export)

        # Load initial values
        self.load_values()

    def load_values(self):
        """Load values from the node."""
        if self.node is None:
            return

        # Points count
        num_points = len(self.node) if hasattr(self.node, "__len__") else 0
        self.points_label.SetLabel(f"Points: {num_points:,}")

        # Layers count
        num_layers = getattr(self.node, "num_layers", 0)
        self.layers_label.SetLabel(f"Layers: {num_layers}")

        # Dimensions
        bounds = getattr(self.node, "bounds", None)
        if bounds is not None:
            min_pt, max_pt = bounds
            size = max_pt - min_pt
            self.dims_label.SetLabel(
                f"Size: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm"
            )
        else:
            self.dims_label.SetLabel("Size: - x - x - mm")

        # Source file
        source = getattr(self.node, "source_file", None)
        if source:
            # Show only filename, not full path
            import os

            filename = os.path.basename(source)
            self.source_label.SetLabel(f"Source: {filename}")
        else:
            self.source_label.SetLabel("Source: -")

        # Strategy
        strategy = getattr(self.node, "generation_strategy", "-")
        self.strategy_label.SetLabel(f"Strategy: {strategy}")

        # Spacing
        spacing = getattr(self.node, "point_spacing_mm", 0)
        self.spacing_label.SetLabel(f"Spacing: {spacing:.3f} mm")

        # Estimate time (rough: 1ms dwell + 0.1ms move per point)
        if num_points > 0:
            time_per_point_ms = 1.1  # Rough estimate
            total_ms = num_points * time_per_point_ms
            total_s = total_ms / 1000
            hours, remainder = divmod(total_s, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.time_label.SetLabel(
                f"Estimated time: {int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
            )
        else:
            self.time_label.SetLabel("Estimated time: --:--:--")

    def on_regenerate(self, event):
        """Open dialog to regenerate points with new parameters."""
        if self.node is None:
            return

        source = getattr(self.node, "source_file", None)
        if not source:
            wx.MessageBox(
                "No source file associated with this point cloud.",
                "Cannot Regenerate",
                wx.OK | wx.ICON_WARNING,
            )
            return

        # Create dialog for regeneration options
        dlg = RegenerateDialog(self, source_file=source)
        if dlg.ShowModal() == wx.ID_OK:
            strategy = dlg.get_strategy()
            spacing = dlg.get_spacing()

            # Regenerate via console command
            self.context(f'glass3d load "{source}" -s {strategy} -p {spacing}')

        dlg.Destroy()

    def on_optimize(self, event):
        """Optimize the point path."""
        if self.node is None:
            return

        from meerk40t_glass3d.mesh.pointcloud import optimize_path

        if self.node.point_data is not None:
            self.node.point_data = optimize_path(self.node.point_data, method="layer_snake")
            self.node.revalidate_points()
            self.node.updated()
            self.load_values()

            wx.MessageBox(
                "Path optimized using layer snake pattern.",
                "Optimization Complete",
                wx.OK | wx.ICON_INFORMATION,
            )

    def on_export(self, event):
        """Export points to file."""
        if self.node is None or self.node.point_data is None:
            return

        with wx.FileDialog(
            self,
            "Export Points",
            wildcard="CSV files (*.csv)|*.csv|NumPy files (*.npy)|*.npy",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return

            filepath = dialog.GetPath()

            try:
                import numpy as np

                if filepath.endswith(".npy"):
                    np.save(filepath, self.node.point_data)
                else:
                    np.savetxt(
                        filepath,
                        self.node.point_data,
                        delimiter=",",
                        header="x,y,z",
                        comments="",
                    )

                wx.MessageBox(
                    f"Exported {len(self.node.point_data)} points to {filepath}",
                    "Export Complete",
                    wx.OK | wx.ICON_INFORMATION,
                )

            except Exception as e:
                wx.MessageBox(
                    f"Export failed: {e}",
                    "Export Error",
                    wx.OK | wx.ICON_ERROR,
                )

    def pane_show(self):
        """Called when panel is shown."""
        self.load_values()

    def pane_hide(self):
        """Called when panel is hidden."""
        pass


class RegenerateDialog(wx.Dialog):
    """Dialog for regenerating point cloud with new parameters."""

    def __init__(self, parent, source_file=None):
        wx.Dialog.__init__(
            self, parent, title="Regenerate Point Cloud", size=(300, 200)
        )
        self.source_file = source_file

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Strategy choice
        strat_sizer = wx.BoxSizer(wx.HORIZONTAL)
        strat_sizer.Add(
            wx.StaticText(self, label="Strategy:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.strategy_choice = wx.Choice(
            self, choices=["surface", "solid", "contour", "layers"]
        )
        self.strategy_choice.SetSelection(0)
        strat_sizer.Add(self.strategy_choice, 1, wx.LEFT, 5)
        sizer.Add(strat_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # Spacing
        spacing_sizer = wx.BoxSizer(wx.HORIZONTAL)
        spacing_sizer.Add(
            wx.StaticText(self, label="Spacing (mm):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.spacing_ctrl = wx.SpinCtrlDouble(
            self, min=0.01, max=10.0, initial=0.1, inc=0.05
        )
        self.spacing_ctrl.SetDigits(3)
        spacing_sizer.Add(self.spacing_ctrl, 1, wx.LEFT, 5)
        sizer.Add(spacing_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(self, wx.ID_OK)
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(wx.Button(self, wx.ID_CANCEL))
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.SetSizer(sizer)

    def get_strategy(self):
        """Get selected strategy."""
        return self.strategy_choice.GetStringSelection()

    def get_spacing(self):
        """Get spacing value."""
        return self.spacing_ctrl.GetValue()
