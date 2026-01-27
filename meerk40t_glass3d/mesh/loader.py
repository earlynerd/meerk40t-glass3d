"""
3D File Loaders for MeerK40t Glass3D Plugin

Supports STL, OBJ, PLY, and 3MF file formats using trimesh.
"""

from pathlib import Path


def load_mesh(filepath):
    """
    Load a 3D mesh file using trimesh.

    Args:
        filepath: Path to the mesh file

    Returns:
        trimesh.Trimesh object
    """
    import trimesh

    return trimesh.load(filepath)


def register_loaders(kernel):
    """Register file format loaders and console commands with MeerK40t."""

    _ = kernel.translation

    @kernel.console_argument("filepath", type=str)
    @kernel.console_option(
        "strategy",
        "s",
        type=str,
        default="surface",
        help=_("Point generation strategy: surface, solid, contour"),
    )
    @kernel.console_option(
        "spacing", "p", type=float, default=0.1, help=_("Point spacing in mm")
    )
    @kernel.console_command(
        "load",
        help=_("Load 3D model file"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def command_load(
        command, channel, _, filepath=None, strategy="surface", spacing=0.1, **kwgs
    ):
        if filepath is None:
            channel(_("Usage: glass3d load <filepath> [-s strategy] [-p spacing]"))
            return "glass3d", None

        path = Path(filepath)
        if not path.exists():
            channel(_(f"File not found: {filepath}"))
            return "glass3d", None

        ext = path.suffix.lower()
        if ext not in (".stl", ".obj", ".ply", ".3mf"):
            channel(_(f"Unsupported format: {ext}"))
            channel(_("Supported: .stl, .obj, .ply, .3mf"))
            return "glass3d", None

        channel(_(f"Loading {filepath}..."))

        try:
            mesh = load_mesh(filepath)
            channel(
                _(f"Loaded mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
            )

            # Generate point cloud
            from meerk40t_glass3d.mesh.pointcloud import generate_points

            points = generate_points(mesh, strategy=strategy, spacing=spacing)
            channel(_(f"Generated {len(points)} points using '{strategy}' strategy"))

            # Create element node
            from meerk40t_glass3d.ssle.element import PointCloud3DNode

            node = PointCloud3DNode(
                points=points,
                source_file=str(filepath),
                generation_strategy=strategy,
                point_spacing_mm=spacing,
            )
            node.sort_bottom_up()

            # Add to elements
            elements = kernel.root.elements
            elements.elem_branch.add_node(node)

            channel(_(f"Created PointCloud3D element with {len(node)} points"))
            if node.bounds_3d is not None:
                min_pt, max_pt = node.bounds_3d
                channel(
                    _(
                        f"Size: {max_pt[0] - min_pt[0]:.1f} x {max_pt[1] - min_pt[1]:.1f} x {max_pt[2] - min_pt[2]:.1f} mm"
                    )
                )
                channel(_(f"Layers: {node.num_layers}"))

            return "glass3d", node

        except Exception as e:
            channel(_(f"Error loading file: {e}"))
            import traceback

            traceback.print_exc()
            return "glass3d", None

    @kernel.console_argument("filepath", type=str)
    @kernel.console_command(
        "preview_mesh",
        help=_("Preview mesh info without loading"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def command_preview_mesh(command, channel, _, filepath=None, **kwgs):
        if filepath is None:
            channel(_("Usage: glass3d preview_mesh <filepath>"))
            return "glass3d", None

        path = Path(filepath)
        if not path.exists():
            channel(_(f"File not found: {filepath}"))
            return "glass3d", None

        try:
            mesh = load_mesh(filepath)
            channel(_(f"Mesh: {path.name}"))
            channel(_(f"  Vertices: {len(mesh.vertices)}"))
            channel(_(f"  Faces: {len(mesh.faces)}"))

            bounds = mesh.bounds
            size = bounds[1] - bounds[0]
            channel(_(f"  Size: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm"))
            channel(_(f"  Volume: {mesh.volume:.2f} mm^3"))
            channel(_(f"  Watertight: {mesh.is_watertight}"))

            return "glass3d", mesh

        except Exception as e:
            channel(_(f"Error reading mesh: {e}"))
            return "glass3d", None

    # Register file input handlers for drag-drop support
    def mesh_loader(pathname, **kwargs):
        """Load mesh file into elements."""
        kernel(f'glass3d load "{pathname}"')
        return True

    # Register loaders for supported formats
    kernel.register("load/stl", mesh_loader)
    kernel.register("load/obj", mesh_loader)
    kernel.register("load/ply", mesh_loader)
    kernel.register("load/3mf", mesh_loader)
