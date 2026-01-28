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
        from meerk40t.gui.icons import (
            icons8_opened_folder,
            icons8_info,
            icons8_laser_beam,
        )

        _ = kernel.translation

        # Console command for file dialog (called by menu)
        @kernel.console_command(
            "glass3d_load_dialog",
            help=_("Open file dialog to load 3D model"),
            hidden=True,
        )
        def glass3d_load_dialog(command, channel, _, **kwgs):
            """Open a file dialog to load a 3D model."""
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

        # Register menu items
        # File menu - Import 3D Model
        kernel.register(
            "button/file/Import3DModel",
            {
                "label": _("Import 3D Model..."),
                "icon": icons8_opened_folder,
                "tip": _("Import STL, OBJ, PLY, or 3MF file for subsurface engraving"),
                "action": lambda e: kernel("glass3d_load_dialog\n"),
                "priority": 15,  # After other import options
            },
        )

        # Laser menu - Add SSLE Operation
        kernel.register(
            "button/laser/SSLEOperation",
            {
                "label": _("Add SSLE Operation"),
                "icon": icons8_laser_beam,
                "tip": _("Add Subsurface Laser Engraving operation"),
                "action": lambda e: kernel("ssle\n"),
                "priority": 90,  # Near end of laser menu
            },
        )

        # Tools menu - Glass3D submenu
        kernel.register(
            "button/tools/Glass3D_Load",
            {
                "label": _("Glass3D: Import 3D Model..."),
                "icon": icons8_opened_folder,
                "tip": _("Import 3D model for subsurface engraving"),
                "action": lambda e: kernel("glass3d_load_dialog\n"),
                "priority": 200,
            },
        )

        kernel.register(
            "button/tools/Glass3D_SSLE",
            {
                "label": _("Glass3D: Create SSLE Operation"),
                "icon": icons8_laser_beam,
                "tip": _("Create subsurface laser engraving operation"),
                "action": lambda e: kernel("ssle\n"),
                "priority": 201,
            },
        )

        kernel.register(
            "button/tools/Glass3D_Info",
            {
                "label": _("Glass3D: Show Model Info"),
                "icon": icons8_info,
                "tip": _("Show information about loaded 3D models"),
                "action": lambda e: kernel("glass3d info\n"),
                "priority": 202,
            },
        )

        # Context menu for PointCloud3D elements
        @kernel.console_command(
            "pointcloud_to_ssle",
            help=_("Create SSLE operation from selected point cloud"),
            hidden=True,
        )
        def pointcloud_to_ssle(command, channel, _, **kwgs):
            """Create SSLE operation from selected point cloud."""
            elements = kernel.root.elements

            # Find selected pointcloud3d elements
            selected = [n for n in elements.elems(emphasized=True)
                       if n.type == "elem pointcloud3d"]

            if not selected:
                channel(_("No point cloud selected"))
                return

            # Create SSLE operation
            from meerk40t_glass3d.ssle.operation import SSLEOperationNode
            op = SSLEOperationNode()
            elements.op_branch.add_node(op)

            # Add selected pointclouds as references
            for pc in selected:
                op.add_reference(pc)
                channel(_(f"Added {pc} to SSLE operation"))

            channel(_("Created SSLE operation with selected point clouds"))

    except ImportError:
        pass
