"""
Glass3D Plugin for MeerK40t

Provides subsurface laser engraving (SSLE) capabilities for galvo lasers.
"""


def plugin(kernel, lifecycle):
    """Main plugin entry point called by MeerK40t kernel."""

    if lifecycle == "plugins":
        # Return sub-plugins to load
        from meerk40t_glass3d.gui import gui

        return [gui.plugin]

    elif lifecycle == "invalidate":
        # Check dependencies
        try:
            import numpy
            import trimesh
        except ImportError as e:
            print(f"Glass3D plugin requires numpy and trimesh: {e}")
            return True  # Invalidate plugin

        # Plugin works best with Z-enabled galvo
        return False

    elif lifecycle == "register":
        # Register element types
        from meerk40t_glass3d.ssle.element import register_element_types

        register_element_types(kernel)

        # Register operation types
        from meerk40t_glass3d.ssle.operation import register_operation_types

        register_operation_types(kernel)

        # Register file loaders
        from meerk40t_glass3d.mesh.loader import register_loaders

        register_loaders(kernel)

        # Register console commands
        register_console_commands(kernel)

    elif lifecycle == "boot":
        # Initialize any services
        pass

    elif lifecycle == "ready":
        # Plugin fully loaded
        kernel.channel("console")(
            "Glass3D SSLE plugin loaded. Use 'glass3d help' for commands."
        )


def register_console_commands(kernel):
    """Register glass3d console commands."""

    _ = kernel.translation

    @kernel.console_command(
        "glass3d",
        help=_("Glass3D subsurface engraving commands"),
        input_type=None,
        output_type="glass3d",
    )
    def glass3d_base(command, channel, _, remainder=None, **kwgs):
        if remainder is None:
            channel(_("Glass3D SSLE Plugin"))
            channel(_("Commands: glass3d help, glass3d load, glass3d preview"))
        return "glass3d", None

    @kernel.console_command(
        "help",
        help=_("Show Glass3D help"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def glass3d_help(command, channel, _, **kwgs):
        channel(_("Glass3D Subsurface Laser Engraving"))
        channel(_(""))
        channel(_("Commands:"))
        channel(_("  glass3d load <file.stl>  - Load 3D model"))
        channel(_("  glass3d preview          - Preview point cloud"))
        channel(_("  glass3d info             - Show model info"))
        channel(_("  glass3d generate         - Generate point cloud"))
        channel(_(""))
        channel(_("Supported formats: STL, OBJ, PLY, 3MF"))
        return "glass3d", None

    @kernel.console_command(
        "debug",
        help=_("Debug element tree"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def glass3d_debug(command, channel, _, **kwgs):
        """Debug command to inspect the element tree."""
        elements = kernel.root.elements
        channel(_("=== Element Tree Debug ==="))

        # Check elem_branch directly
        channel(_(f"elem_branch: {elements.elem_branch}"))
        channel(_(f"elem_branch children: {len(elements.elem_branch.children)}"))

        for i, child in enumerate(elements.elem_branch.children):
            channel(_(f"  [{i}] type={child.type}, class={child.__class__.__name__}"))

        # Check elems() method
        all_elems = list(elements.elems(emphasized=False))
        channel(_(f"elems() returned {len(all_elems)} elements"))
        for i, e in enumerate(all_elems[:10]):  # First 10
            channel(_(f"  [{i}] type={e.type}"))

        return "glass3d", None

    @kernel.console_command(
        "info",
        help=_("Show info about loaded models"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def glass3d_info(command, channel, _, **kwgs):
        # Find all PointCloud3D elements by searching elem_branch directly
        # (can't use elems() because it filters by elem_nodes tuple which doesn't include pointcloud3d)
        elements = kernel.root.elements

        def find_pointclouds(node):
            """Recursively find all pointcloud3d elements."""
            results = []
            if node.type == "elem pointcloud3d":
                results.append(node)
            for child in node.children:
                results.extend(find_pointclouds(child))
            return results

        pointclouds = find_pointclouds(elements.elem_branch)

        if not pointclouds:
            channel(_("No PointCloud3D elements loaded."))
            return "glass3d", None

        for i, pc in enumerate(pointclouds):
            channel(_(f"PointCloud {i + 1}: {len(pc)} points"))
            if pc.bounds_3d:
                min_pt, max_pt = pc.bounds_3d
                channel(
                    _(
                        f"  Size: {max_pt[0] - min_pt[0]:.1f} x {max_pt[1] - min_pt[1]:.1f} x {max_pt[2] - min_pt[2]:.1f} mm"
                    )
                )
            channel(_(f"  Layers: {pc.num_layers}"))
            channel(_(f"  Source: {pc.source_file or 'Unknown'}"))

        return "glass3d", None
