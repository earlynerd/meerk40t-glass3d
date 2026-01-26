"""
Glass3D GUI Plugin for MeerK40t

Provides GUI panels and widgets for SSLE operations.
"""


def plugin(kernel, lifecycle):
    """GUI plugin entry point called by MeerK40t kernel."""

    if lifecycle == "invalidate":
        # Check if wxPython is available
        try:
            import wx
        except ImportError:
            # No GUI available, skip GUI registration
            return True
        return False

    elif lifecycle == "register":
        # Register property panels
        register_property_panels(kernel)

        # Register menu items
        register_menu_items(kernel)

    elif lifecycle == "boot":
        pass


def register_property_panels(kernel):
    """Register property panels for Glass3D elements and operations."""
    try:
        from meerk40t_glass3d.gui.ssle_panel import SSLEOperationPanel
        from meerk40t_glass3d.gui.pointcloud_panel import PointCloudPropertyPanel

        # Register SSLE operation panel
        kernel.register("property/SSLEOperationNode/SSLE", SSLEOperationPanel)

        # Register PointCloud3D property panel
        kernel.register("property/PointCloud3DNode/PointCloud", PointCloudPropertyPanel)

    except ImportError as e:
        print(f"Glass3D: Could not register property panels: {e}")


def register_menu_items(kernel):
    """Register menu items for Glass3D operations."""
    try:
        import wx

        _ = kernel.translation

        # Add Glass3D submenu to Tools menu
        @kernel.console_command(
            "glass3d_load_dialog",
            help=_("Open file dialog to load 3D model"),
            hidden=True,
        )
        def glass3d_load_dialog(command, channel, _, **kwgs):
            """Open a file dialog to load a 3D model."""
            # This will be called from menu
            gui = kernel.lookup("wxgui")
            if gui is None:
                channel(_("GUI not available"))
                return

            with wx.FileDialog(
                gui,
                _("Open 3D Model"),
                wildcard="3D Models (*.stl;*.obj;*.ply;*.3mf)|*.stl;*.obj;*.ply;*.3mf|"
                "STL files (*.stl)|*.stl|"
                "OBJ files (*.obj)|*.obj|"
                "PLY files (*.ply)|*.ply|"
                "3MF files (*.3mf)|*.3mf|"
                "All files (*.*)|*.*",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if dialog.ShowModal() == wx.ID_CANCEL:
                    return

                filepath = dialog.GetPath()
                kernel(f'glass3d load "{filepath}"')

    except ImportError:
        pass
