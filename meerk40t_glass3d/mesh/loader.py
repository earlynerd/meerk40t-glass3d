"""
3D File Loaders for MeerK40t Glass3D Plugin

Supports STL, OBJ, PLY, and 3MF file formats using trimesh.
Includes anchor detection and filtering for 3MF files from slicers.
"""

from pathlib import Path


def is_anchor_name(name):
    """Check if a model name indicates it's an anchor (to be skipped).

    Anchor models are used in slicers to hold floating parts at Z=0
    but should be excluded from point cloud generation.

    A model is considered an anchor if "anchor" appears anywhere in the
    name (case-insensitive). This handles various naming conventions:
    - "anchor"
    - "anchor.stl"
    - "MyAssembly_anchor"
    - "anchor_plate"

    Args:
        name: Model name to check

    Returns:
        True if this is an anchor model
    """
    return "anchor" in name.lower()


def is_anchor_geometry(mesh, z_tolerance=0.5, max_height=2.0):
    """Check if a mesh looks like an anchor based on its geometry.

    A mesh is considered an anchor if:
    - Its minimum Z is close to 0 (touching the bed)
    - Its total height (Z extent) is small

    This is a fallback for when anchors aren't properly named.

    Args:
        mesh: The trimesh mesh to check
        z_tolerance: How close to Z=0 the bottom must be (default 0.5mm)
        max_height: Maximum height to be considered an anchor (default 2.0mm)

    Returns:
        True if this mesh appears to be an anchor
    """
    bounds = mesh.bounds  # [[min_x, min_y, min_z], [max_x, max_y, max_z]]
    min_z = bounds[0][2]
    max_z = bounds[1][2]
    height = max_z - min_z

    return bool(min_z <= z_tolerance and height <= max_height)


def extract_3mf_names(filepath):
    """Extract model names from slicer-specific metadata in 3MF file.

    Supports PrusaSlicer/Slic3r and BambuStudio metadata formats.

    Args:
        filepath: Path to the 3MF file

    Returns:
        Dict mapping geometry names/IDs to display names from slicer
    """
    import zipfile
    import xml.etree.ElementTree as ET

    path = Path(filepath)
    name_map = {}

    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()

            # Try PrusaSlicer/Slic3r format
            if "Metadata/Slic3r_PE_model.config" in names:
                content = zf.read("Metadata/Slic3r_PE_model.config").decode("utf-8")
                root = ET.fromstring(content)

                for obj in root.findall("object"):
                    obj_id = obj.get("id")
                    if not obj_id:
                        continue

                    # Get object-level name
                    for meta in obj.findall("metadata"):
                        if meta.get("key") == "name":
                            name_map[obj_id] = meta.get("value", obj_id)
                            break

                    # Get volume-level names (for multi-part objects)
                    for vol in obj.findall("volume"):
                        for meta in vol.findall("metadata"):
                            if meta.get("key") == "name":
                                vol_name = meta.get("value")
                                if vol_name:
                                    # Store with object_id prefix for matching
                                    firstid = vol.get("firstid")
                                    lastid = vol.get("lastid")
                                    if firstid and lastid:
                                        name_map[f"{obj_id}_{firstid}_{lastid}"] = vol_name
                                    else:
                                        name_map[vol_name] = vol_name

            # Try BambuStudio format
            if "Metadata/model_settings.config" in names:
                content = zf.read("Metadata/model_settings.config").decode("utf-8")
                root = ET.fromstring(content)

                for part in root.findall(".//part"):
                    part_id = part.get("id")
                    if not part_id:
                        continue

                    for meta in part.findall("metadata"):
                        if meta.get("key") == "name":
                            name_map[part_id] = meta.get("value", part_id)
                            break

    except Exception:
        pass

    return name_map


def filter_anchor_components(mesh):
    """Filter out anchor components from a mesh.

    For meshes that contain multiple disconnected components (assemblies),
    this filters out components that look like anchors based on geometry.

    Args:
        mesh: trimesh.Trimesh object

    Returns:
        Filtered mesh with anchor components removed, or original if no anchors found
    """
    import trimesh

    # Try to split into components
    if not hasattr(mesh, "split"):
        return mesh

    components = mesh.split()
    if len(components) <= 1:
        return mesh

    # Filter out anchor-like components
    non_anchor_components = [c for c in components if not is_anchor_geometry(c)]

    if len(non_anchor_components) == 0:
        # All components are anchors - return empty or original
        return mesh
    elif len(non_anchor_components) < len(components):
        # Some components were anchors, recombine the rest
        return trimesh.util.concatenate(non_anchor_components)
    else:
        # No anchors found
        return mesh


def load_mesh(filepath, skip_anchors=False, channel=None):
    """
    Load a 3D mesh file using trimesh.

    Args:
        filepath: Path to the mesh file
        skip_anchors: If True, filter out anchor models/components (for 3MF files)
        channel: Optional channel for debug output

    Returns:
        trimesh.Trimesh object
    """
    import trimesh

    path = Path(filepath)
    ext = path.suffix.lower()

    # For 3MF with anchor filtering, use special handling
    if ext == ".3mf" and skip_anchors:
        return _load_3mf_skip_anchors(filepath, channel=channel)

    # 3MF files need special handling - they're ZIP archives
    if ext == ".3mf":
        result = trimesh.load(filepath, file_type="3mf", force="mesh")
    else:
        result = trimesh.load(filepath)

    # trimesh.load() can return a Scene (multiple meshes) or a Trimesh (single mesh)
    # We need to handle both cases
    if isinstance(result, trimesh.Scene):
        # Combine all meshes in the scene into one
        meshes = []
        for name, geom in result.geometry.items():
            if isinstance(geom, trimesh.Trimesh):
                meshes.append(geom)
            elif hasattr(geom, "to_mesh"):
                # Some geometry types can be converted to mesh
                try:
                    meshes.append(geom.to_mesh())
                except Exception:
                    pass
        if not meshes:
            # Provide more debug info about what was found
            geom_types = [type(g).__name__ for g in result.geometry.values()]
            raise ValueError(
                f"No valid meshes found in file. Found geometry types: {geom_types}"
            )
        if len(meshes) == 1:
            return meshes[0]
        # Concatenate multiple meshes into one
        return trimesh.util.concatenate(meshes)

    if result is None or (hasattr(result, "is_empty") and result.is_empty):
        raise ValueError("File loaded but contains no geometry")

    return result


def _load_3mf_skip_anchors(filepath, channel=None):
    """Load a 3MF file with anchor filtering.

    This extracts model names from slicer metadata and filters out:
    - Models with "anchor" in the name
    - Geometry that looks like an anchor (flat at Z=0)
    - Anchor components within assemblies

    Args:
        filepath: Path to the 3MF file
        channel: Optional channel for debug output

    Returns:
        trimesh.Trimesh with anchors filtered out
    """
    import trimesh

    path = Path(filepath)

    # Extract names from slicer metadata
    name_map = extract_3mf_names(filepath)

    # Also build a reverse map of display names for matching
    display_names_to_skip = {name for name in name_map.values() if is_anchor_name(name)}

    # Load the 3MF file
    result = trimesh.load(str(filepath), file_type="3mf", force="mesh")

    if isinstance(result, trimesh.Trimesh):
        # Single mesh - check if entire thing is an anchor
        if is_anchor_geometry(result):
            raise ValueError("File contains only anchor geometry")
        # Filter anchor components
        return filter_anchor_components(result)

    if not isinstance(result, trimesh.Scene):
        if result is None or (hasattr(result, "is_empty") and result.is_empty):
            raise ValueError("File loaded but contains no geometry")
        return result

    # Process scene with multiple meshes
    meshes = []
    skipped_by_name = []
    skipped_by_geometry = []

    if channel:
        channel(f"  Name map: {name_map}")
        channel(f"  Geometry names in scene: {list(result.geometry.keys())}")

    for geom_name, geom in result.geometry.items():
        # Convert to mesh if needed
        mesh = None
        if isinstance(geom, trimesh.Trimesh):
            mesh = geom
        elif hasattr(geom, "to_mesh"):
            try:
                mesh = geom.to_mesh()
            except Exception:
                continue

        if mesh is None:
            continue

        # Check if name indicates anchor - try multiple matching strategies
        display_name = name_map.get(geom_name, geom_name)

        # Strategy 1: Direct name check
        skip_this = is_anchor_name(display_name) or is_anchor_name(geom_name)

        # Strategy 2: Check if geometry name contains any known anchor name
        if not skip_this:
            for anchor_name in display_names_to_skip:
                # Remove extension for matching
                anchor_base = anchor_name.rsplit(".", 1)[0] if "." in anchor_name else anchor_name
                if anchor_base.lower() in geom_name.lower():
                    skip_this = True
                    display_name = anchor_name
                    break

        if skip_this:
            skipped_by_name.append(display_name)
            if channel:
                channel(f"  Skipping '{geom_name}' by name (display: {display_name})")
            continue

        # Check if geometry looks like an anchor (flat at Z=0)
        if is_anchor_geometry(mesh):
            skipped_by_geometry.append(display_name)
            if channel:
                bounds = mesh.bounds
                channel(f"  Skipping '{geom_name}' by geometry (Z: {bounds[0][2]:.2f} to {bounds[1][2]:.2f})")
            continue

        # Filter anchor components from assemblies
        filtered_mesh = filter_anchor_components(mesh)
        if channel:
            channel(f"  Keeping '{geom_name}' ({len(filtered_mesh.vertices)} verts)")
        meshes.append(filtered_mesh)

    if not meshes:
        details = []
        if skipped_by_name:
            details.append(f"skipped by name: {skipped_by_name}")
        if skipped_by_geometry:
            details.append(f"skipped by geometry: {skipped_by_geometry}")
        raise ValueError(
            f"No valid meshes after anchor filtering. {'; '.join(details)}"
        )

    if len(meshes) == 1:
        return meshes[0]

    return trimesh.util.concatenate(meshes)


class Glass3DMeshLoader:
    """Loader class for 3D mesh files (STL, OBJ, PLY, 3MF)."""

    @staticmethod
    def load_types():
        """Yield supported file types for MeerK40t's file dialog."""
        yield "3D Mesh - STL", ("stl",), "model/stl"
        yield "3D Mesh - OBJ", ("obj",), "model/obj"
        yield "3D Mesh - PLY", ("ply",), "model/ply"
        yield "3D Mesh - 3MF", ("3mf",), "model/3mf"

    @staticmethod
    def load(kernel, elements_service, pathname, **kwargs):
        """Load a 3D mesh file and create a PointCloud3D element."""
        kernel(f'glass3d load "{pathname}"')
        return True


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
    @kernel.console_option(
        "include_anchors",
        "a",
        type=bool,
        action="store_true",
        help=_("Include anchor models (by default, models with 'anchor' in name or flat at Z=0 are skipped)"),
    )
    @kernel.console_command(
        "load",
        help=_("Load 3D model file"),
        input_type="glass3d",
        output_type="glass3d",
    )
    def command_load(
        command, channel, _, filepath=None, strategy="surface", spacing=0.1, include_anchors=False, **kwgs
    ):
        if filepath is None:
            channel(_("Usage: glass3d load <filepath> [-s strategy] [-p spacing] [-a to include anchors]"))
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

        # Skip anchors by default for 3MF files (use -a to include them)
        skip_anchors = not include_anchors and ext == ".3mf"

        channel(_(f"Loading {filepath}..."))
        if skip_anchors:
            channel(_("Anchor filtering enabled (use -a to include anchors)"))

        try:
            mesh = load_mesh(filepath, skip_anchors=skip_anchors, channel=channel)
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
            # For 3MF files, provide additional troubleshooting info
            if ext == ".3mf":
                channel(_("3MF troubleshooting:"))
                channel(_("  - Ensure the file is a valid 3MF (ZIP) archive"))
                channel(_("  - Try opening in another slicer to verify it's not corrupt"))
                try:
                    import zipfile

                    with zipfile.ZipFile(filepath, "r") as zf:
                        channel(_(f"  - Archive contents: {zf.namelist()}"))
                        # Show extracted names if available
                        names = extract_3mf_names(filepath)
                        if names:
                            channel(_(f"  - Model names found: {list(names.values())}"))
                except Exception as ze:
                    channel(_(f"  - Could not read as ZIP: {ze}"))
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

            # For 3MF files, show model names and anchor status
            ext = path.suffix.lower()
            if ext == ".3mf":
                names = extract_3mf_names(filepath)
                if names:
                    channel(_("  Model names from slicer:"))
                    for key, name in names.items():
                        anchor_status = " [ANCHOR]" if is_anchor_name(name) else ""
                        channel(_(f"    - {name}{anchor_status}"))

            return "glass3d", mesh

        except Exception as e:
            channel(_(f"Error reading mesh: {e}"))
            return "glass3d", None

    # Register file loader class for supported 3D formats
    kernel.register("load/Glass3DMeshLoader", Glass3DMeshLoader)
