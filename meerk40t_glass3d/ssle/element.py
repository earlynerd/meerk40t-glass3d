"""
PointCloud3D Element Node for MeerK40t

Represents a 3D point cloud that can be engraved using SSLE.
"""

import numpy as np
from meerk40t.core.node.node import Node


class PointCloud3DNode(Node):
    """
    Node representing a 3D point cloud for subsurface engraving.

    Attributes:
        point_data: Nx3 numpy array of XYZ coordinates in mm
        intensities: Optional Nx1 array of point intensities (0-1)
        layer_indices: Optional Nx1 array of layer assignments
        source_file: Path to original mesh file
        generation_strategy: Strategy used to generate points
    """

    def __init__(self, **kwargs):
        from meerk40t.svgelements import Matrix

        # Use point_data to avoid conflict with Node.points property
        self.point_data = kwargs.pop("points", None)
        self.intensities = kwargs.pop("intensities", None)
        self.layer_indices = kwargs.pop("layer_indices", None)
        self.source_file = kwargs.pop("source_file", None)
        self.generation_strategy = kwargs.pop("generation_strategy", "surface")
        self.point_spacing_mm = kwargs.pop("point_spacing_mm", 0.1)

        # Standard element attributes for transformations
        self.matrix = kwargs.pop("matrix", None)
        self.fill = kwargs.pop("fill", None)
        self.stroke = kwargs.pop("stroke", None)
        self.stroke_width = kwargs.pop("stroke_width", 1000.0)

        super().__init__(type="elem pointcloud3d", **kwargs)

        # Initialize matrix if not provided
        if self.matrix is None:
            self.matrix = Matrix()

        self._bounds_cache = None
        self._formatter = "{element_type} {desc}"

    def __len__(self):
        if self.point_data is None:
            return 0
        return len(self.point_data)

    def __repr__(self):
        return f"PointCloud3D({len(self)} points)"

    def __copy__(self):
        from copy import copy
        return PointCloud3DNode(
            points=self.point_data.copy() if self.point_data is not None else None,
            intensities=self.intensities.copy() if self.intensities is not None else None,
            layer_indices=self.layer_indices.copy() if self.layer_indices is not None else None,
            source_file=self.source_file,
            generation_strategy=self.generation_strategy,
            point_spacing_mm=self.point_spacing_mm,
            matrix=copy(self.matrix),
            fill=copy(self.fill) if self.fill else None,
            stroke=copy(self.stroke) if self.stroke else None,
            stroke_width=self.stroke_width,
        )

    def preprocess(self, context, matrix, plan):
        """Apply matrix transformation during preprocessing."""
        self.matrix *= matrix
        self._bounds_cache = None
        self.set_dirty_bounds()

    @property
    def bounds_3d(self):
        """Return (min_xyz, max_xyz) 3D bounding box in mm."""
        if self.point_data is None or len(self.point_data) == 0:
            return None
        if self._bounds_cache is None:
            self._bounds_cache = (
                self.point_data.min(axis=0),
                self.point_data.max(axis=0),
            )
        return self._bounds_cache

    # Note: Don't override 'bounds' or 'paint_bounds' properties -
    # the Node base class handles caching and calls bbox() for us.

    @property
    def num_layers(self):
        """Number of unique Z layers."""
        if self.layer_indices is not None:
            return int(self.layer_indices.max()) + 1
        if self.point_data is None:
            return 0
        return len(np.unique(self.point_data[:, 2]))

    def bbox(self, transformed=True, with_stroke=False):
        """Return 2D bounding box (x1, y1, x2, y2) in native units for MeerK40t."""
        if self.point_data is None or len(self.point_data) == 0:
            return None
        bounds_3d = self.bounds_3d
        if bounds_3d is None:
            return None
        min_pt, max_pt = bounds_3d
        from meerk40t.core.units import UNITS_PER_MM

        # Convert to native units
        x1 = float(min_pt[0]) * UNITS_PER_MM
        y1 = float(min_pt[1]) * UNITS_PER_MM
        x2 = float(max_pt[0]) * UNITS_PER_MM
        y2 = float(max_pt[1]) * UNITS_PER_MM

        # Apply matrix transformation to all four corners if requested
        if transformed and self.matrix is not None:
            corners = [
                self.matrix.point_in_matrix_space((x1, y1)),
                self.matrix.point_in_matrix_space((x2, y1)),
                self.matrix.point_in_matrix_space((x1, y2)),
                self.matrix.point_in_matrix_space((x2, y2)),
            ]
            xs = [c[0] for c in corners]
            ys = [c[1] for c in corners]
            return (min(xs), min(ys), max(xs), max(ys))

        return (x1, y1, x2, y2)

    def default_map(self, default_map=None):
        """Provide default mapping for node operations."""
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "PointCloud3D"
        default_map["points"] = len(self)
        default_map["layers"] = self.num_layers
        default_map["desc"] = f"{len(self)} pts, {self.num_layers} layers"
        if self.bounds_3d is not None:
            min_pt, max_pt = self.bounds_3d
            default_map["width"] = f"{max_pt[0] - min_pt[0]:.1f}mm"
            default_map["height"] = f"{max_pt[1] - min_pt[1]:.1f}mm"
            default_map["depth"] = f"{max_pt[2] - min_pt[2]:.1f}mm"
        return default_map

    def can_drop(self, drag_node):
        """Determine if another node can be dropped onto this one."""
        if self.is_a_child_of(drag_node):
            return False
        # Allow dropping into SSLE operations
        if drag_node.type == "op ssle":
            return True
        return False

    def drop(self, drag_node, modify=True, flag=False):
        """Handle drag-drop onto this node."""
        # If dropped on an SSLE op, add self to that op
        if drag_node.type == "op ssle":
            if modify:
                drag_node.add_reference(self)
            return True
        return False

    def revalidate_points(self):
        """Recalculate layer indices and clear caches."""
        self._bounds_cache = None
        self.set_dirty_bounds()
        if self.point_data is not None and len(self.point_data) > 0:
            # Assign layer indices based on Z values
            unique_z = np.unique(self.point_data[:, 2])
            z_to_layer = {z: i for i, z in enumerate(sorted(unique_z))}
            self.layer_indices = np.array([z_to_layer[z] for z in self.point_data[:, 2]])

    def sort_bottom_up(self):
        """Sort points by Z ascending (required for SSLE)."""
        if self.point_data is None:
            return
        order = np.argsort(self.point_data[:, 2])
        self.point_data = self.point_data[order]
        if self.intensities is not None:
            self.intensities = self.intensities[order]
        self.revalidate_points()

    def length(self):
        """Return the length of this element (for compatibility)."""
        return 0

    def as_geometry(self, **kws):
        """
        Return geometry representation for MeerK40t.

        For point clouds, we return a Geomstr with all points.
        """
        from meerk40t.core.geomstr import Geomstr
        from meerk40t.core.units import UNITS_PER_MM

        path = Geomstr()
        if self.point_data is not None:
            for pt in self.point_data:
                # Convert mm to native units
                x = pt[0] * UNITS_PER_MM
                y = pt[1] * UNITS_PER_MM
                path.point(complex(x, y))
        # Apply matrix transformation
        if self.matrix is not None:
            path.transform(self.matrix)
        return path

    def draw(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
        """
        Draw point cloud in the scene view.

        This method is called by MeerK40t's renderer to display
        the point cloud as colored dots based on Z-depth.

        Args:
            node: The node being drawn (self)
            gc: wxPython GraphicsContext
            draw_mode: Drawing mode flags
            zoomscale: Current zoom level
            alpha: Transparency (0-255)
        """
        import wx
        from meerk40t.core.units import UNITS_PER_MM

        if self.point_data is None or len(self.point_data) == 0:
            return

        # Get 3D bounds for Z-depth coloring
        bounds_3d = self.bounds_3d
        if bounds_3d is None:
            return

        min_pt, max_pt = bounds_3d
        z_min, z_max = float(min_pt[2]), float(max_pt[2])
        z_range = z_max - z_min if z_max > z_min else 1.0

        gc.PushState()

        # For large point clouds, subsample for performance
        max_display_points = 10000
        points = self.point_data
        if len(points) > max_display_points:
            step = len(points) // max_display_points
            points = points[::step]

        # Minimal point size - 1 pixel in scene coordinates
        # Use a small fixed size that looks like a dot
        dot_size = 200  # 0.2mm in native units - tiny but visible

        # Pre-calculate Z-normalized values for all points
        z_values = points[:, 2]
        z_normalized = (z_values - z_min) / z_range if z_range > 0 else np.full_like(z_values, 0.5)

        # Draw points colored by Z-depth
        # Blue (bottom/deep) -> Cyan -> Green -> Yellow -> Red (top/surface)
        gc.SetPen(wx.TRANSPARENT_PEN)

        for i, pt in enumerate(points):
            x = float(pt[0]) * UNITS_PER_MM
            y = float(pt[1]) * UNITS_PER_MM

            # Apply matrix transformation
            if self.matrix is not None:
                x, y = self.matrix.point_in_matrix_space((x, y))

            z_norm = z_normalized[i]

            # Create a gradient: blue -> cyan -> green -> yellow -> red
            if z_norm < 0.25:
                t = z_norm / 0.25
                r, g, b = 0, int(255 * t), 255
            elif z_norm < 0.5:
                t = (z_norm - 0.25) / 0.25
                r, g, b = 0, 255, int(255 * (1 - t))
            elif z_norm < 0.75:
                t = (z_norm - 0.5) / 0.25
                r, g, b = int(255 * t), 255, 0
            else:
                t = (z_norm - 0.75) / 0.25
                r, g, b = 255, int(255 * (1 - t)), 0

            gc.SetBrush(wx.Brush(wx.Colour(r, g, b, alpha)))
            gc.DrawRectangle(x, y, dot_size, dot_size)

        # Draw selection highlight (bounding box) if emphasized
        if getattr(self, "emphasized", False) or getattr(self, "selected", False):
            bbox = self.bbox()
            if bbox is not None:
                # Draw bounding box
                pen = wx.Pen(wx.Colour(0, 128, 255, alpha), max(1, int(2000 * zoomscale)))
                gc.SetPen(pen)
                gc.SetBrush(wx.TRANSPARENT_BRUSH)

                x1, y1, x2, y2 = bbox
                gc.DrawRectangle(x1, y1, x2 - x1, y2 - y1)

        gc.PopState()


def register_element_types(kernel):
    """Register PointCloud3D element type with kernel."""
    from meerk40t.core.node.bootstrap import bootstrap, defaults

    # Register the node type in bootstrap
    bootstrap["elem pointcloud3d"] = PointCloud3DNode
    defaults["elem pointcloud3d"] = {}

    # Register tree format string
    kernel.register("format/elem pointcloud3d", "{element_type} {desc}")

    # Add our element type to the element type lists so the scene renders it
    # These are module-level tuples that are imported by other modules,
    # so we need to update both the source module AND any modules that imported them
    import meerk40t.core.elements.element_types as et
    import meerk40t.core.elements.elements as elems_module

    our_type = "elem pointcloud3d"

    # Update element_types module
    if our_type not in et.elem_nodes:
        et.elem_nodes = et.elem_nodes + (our_type,)
    if our_type not in et.elem_group_nodes:
        et.elem_group_nodes = et.elem_group_nodes + (our_type,)
    if our_type not in et.elem_ref_nodes:
        et.elem_ref_nodes = et.elem_ref_nodes + (our_type,)

    # Update elements module's imported references
    if our_type not in elems_module.elem_nodes:
        elems_module.elem_nodes = elems_module.elem_nodes + (our_type,)
    if our_type not in elems_module.elem_group_nodes:
        elems_module.elem_group_nodes = elems_module.elem_group_nodes + (our_type,)

    # Update selectionwidget module's imported references (for drag/move support)
    try:
        import meerk40t.gui.scenewidgets.selectionwidget as selwidget
        if our_type not in selwidget.elem_nodes:
            selwidget.elem_nodes = selwidget.elem_nodes + (our_type,)
        if our_type not in selwidget.elem_group_nodes:
            selwidget.elem_group_nodes = selwidget.elem_group_nodes + (our_type,)
    except (ImportError, AttributeError):
        pass  # GUI might not be loaded

    print(f"[Glass3D] Registered {our_type} in element type lists")
