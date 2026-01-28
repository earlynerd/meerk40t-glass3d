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
        channel(_("Glass3D Subsurface Laser Engraving (SSLE)"))
        channel(_(""))
        channel(_("=== Quick Start Workflow ==="))
        channel(_("  1. glass3d load <file.stl>   - Load 3D model"))
        channel(_("  2. glass3d make_op           - Create SSLE operation"))
        channel(_("  3. glass3d run               - Execute the job"))
        channel(_(""))
        channel(_("=== All Commands ==="))
        channel(_("  glass3d load <file> [-s strategy] [-p spacing]"))
        channel(_("      Load 3D model and generate point cloud"))
        channel(_("      Strategies: surface, solid, contour, layers"))
        channel(_(""))
        channel(_("  glass3d make_op"))
        channel(_("      Create SSLE operation with all loaded pointclouds"))
        channel(_(""))
        channel(_("  glass3d run"))
        channel(_("      Execute all SSLE operations"))
        channel(_(""))
        channel(_("  glass3d status"))
        channel(_("      Show workflow status and next steps"))
        channel(_(""))
        channel(_("  glass3d info"))
        channel(_("      Show info about loaded pointclouds"))
        channel(_(""))
        channel(_("=== Supported Formats ==="))
        channel(_("  STL, OBJ, PLY, 3MF"))
        channel(_(""))
        channel(_("=== GUI Workflow ==="))
        channel(_("  1. File > Import 3D Model (or drag-drop STL/OBJ file)"))
        channel(_("  2. The pointcloud appears in Elements tree (left)"))
        channel(_("  3. Create SSLE operation: glass3d make_op"))
        channel(_("  4. Select SSLE operation in Operations tree (right)"))
        channel(_("  5. Adjust settings in the SSLE panel"))
        channel(_("  6. Click Start or use: glass3d run"))
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
        "make_op",
        help=_("Create SSLE operation from all loaded pointclouds"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def glass3d_make_op(command, channel, _, **kwgs):
        """Create an SSLE operation and add all pointclouds to it."""
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
            channel(_("No PointCloud3D elements found. Load a 3D model first:"))
            channel(_("  glass3d load <filepath.stl>"))
            return "glass3d", None

        # Create SSLE operation
        from meerk40t_glass3d.ssle.operation import SSLEOperationNode

        op = SSLEOperationNode()
        elements.op_branch.add_node(op)

        # Add all pointclouds as references
        for pc in pointclouds:
            op.add_reference(pc)
            channel(_(f"Added pointcloud ({len(pc)} points) to SSLE operation"))

        channel(_(""))
        channel(_(f"Created SSLE operation with {len(pointclouds)} pointcloud(s)"))
        channel(_(""))
        channel(_("To run the job:"))
        channel(_("  1. Select the SSLE operation in the Operations tree (right panel)"))
        channel(_("  2. Adjust settings in the SSLE panel (power, dwell, etc.)"))
        channel(_("  3. Click 'Start' or use: glass3d run"))

        return "glass3d", op

    @kernel.console_command(
        "run",
        help=_("Execute SSLE operations"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def glass3d_run(command, channel, _, **kwgs):
        """Execute all SSLE operations."""
        elements = kernel.root.elements

        # Find all SSLE operations
        ssle_ops = [op for op in elements.ops() if op.type == "op ssle"]

        if not ssle_ops:
            channel(_("No SSLE operations found."))
            channel(_("Create one with: glass3d make_op"))
            return "glass3d", None

        # Check if any have children
        ops_with_children = [op for op in ssle_ops if len(list(op.children)) > 0]
        if not ops_with_children:
            channel(_("SSLE operations have no pointclouds assigned."))
            channel(_("Use: glass3d make_op"))
            return "glass3d", None

        channel(_(f"Executing {len(ops_with_children)} SSLE operation(s)..."))

        # Use MeerK40t's execute command
        try:
            # Select the SSLE operations
            for op in ops_with_children:
                op.emphasized = True
                op.selected = True

            # Trigger execution via the plan system
            kernel("plan clear copy preprocess validate blob preopt optimize spool\n")
            channel(_("Job sent to laser."))
        except Exception as e:
            channel(_(f"Execution failed: {e}"))

        return "glass3d", None

    @kernel.console_command(
        "status",
        help=_("Show SSLE workflow status"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def glass3d_status(command, channel, _, **kwgs):
        """Show the current status of the SSLE workflow."""
        elements = kernel.root.elements

        def find_pointclouds(node):
            results = []
            if node.type == "elem pointcloud3d":
                results.append(node)
            for child in node.children:
                results.extend(find_pointclouds(child))
            return results

        pointclouds = find_pointclouds(elements.elem_branch)
        ssle_ops = [op for op in elements.ops() if op.type == "op ssle"]

        channel(_("=== Glass3D SSLE Status ==="))
        channel(_(""))

        # Step 1: Load model
        if pointclouds:
            channel(_("[OK] Step 1: PointClouds loaded"))
            for i, pc in enumerate(pointclouds):
                channel(_(f"     - PointCloud {i+1}: {len(pc):,} points"))
        else:
            channel(_("[  ] Step 1: Load a 3D model"))
            channel(_("     Command: glass3d load <filepath.stl>"))
            return "glass3d", None

        channel(_(""))

        # Step 2: Create operation
        if ssle_ops:
            channel(_("[OK] Step 2: SSLE Operation(s) created"))
            for i, op in enumerate(ssle_ops):
                children = list(op.children)
                channel(_(f"     - Operation {i+1}: {len(children)} reference(s)"))
        else:
            channel(_("[  ] Step 2: Create SSLE operation"))
            channel(_("     Command: glass3d make_op"))
            return "glass3d", None

        channel(_(""))

        # Step 3: Check if ops have children
        ops_with_children = [op for op in ssle_ops if len(list(op.children)) > 0]
        if ops_with_children:
            channel(_("[OK] Step 3: PointClouds assigned to operations"))
        else:
            channel(_("[  ] Step 3: Assign pointclouds to operation"))
            channel(_("     Command: glass3d make_op"))
            return "glass3d", None

        channel(_(""))
        channel(_("[READY] You can now run the job:"))
        channel(_("     Command: glass3d run"))
        channel(_("     Or click 'Start' in the GUI"))

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
