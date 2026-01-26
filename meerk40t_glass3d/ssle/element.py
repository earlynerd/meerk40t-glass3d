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
        # Use point_data to avoid conflict with Node.points property
        self.point_data = kwargs.pop("points", None)
        self.intensities = kwargs.pop("intensities", None)
        self.layer_indices = kwargs.pop("layer_indices", None)
        self.source_file = kwargs.pop("source_file", None)
        self.generation_strategy = kwargs.pop("generation_strategy", "surface")
        self.point_spacing_mm = kwargs.pop("point_spacing_mm", 0.1)

        super().__init__(type="elem pointcloud3d", **kwargs)

        self._bounds_cache = None
        self._formatter = "{element_type} {desc}"

    def __len__(self):
        if self.point_data is None:
            return 0
        return len(self.point_data)

    def __repr__(self):
        return f"PointCloud3D({len(self)} points)"

    def __copy__(self):
        return PointCloud3DNode(
            points=self.point_data.copy() if self.point_data is not None else None,
            intensities=self.intensities.copy() if self.intensities is not None else None,
            layer_indices=self.layer_indices.copy() if self.layer_indices is not None else None,
            source_file=self.source_file,
            generation_strategy=self.generation_strategy,
            point_spacing_mm=self.point_spacing_mm,
        )

    @property
    def bounds(self):
        """Return (min_xyz, max_xyz) bounding box."""
        if self.point_data is None or len(self.point_data) == 0:
            return None
        if self._bounds_cache is None:
            self._bounds_cache = (
                self.point_data.min(axis=0),
                self.point_data.max(axis=0),
            )
        return self._bounds_cache

    @property
    def num_layers(self):
        """Number of unique Z layers."""
        if self.layer_indices is not None:
            return int(self.layer_indices.max()) + 1
        if self.point_data is None:
            return 0
        return len(np.unique(self.point_data[:, 2]))

    def bbox(self, transformed=True, with_stroke=False):
        """Return 2D bounding box for MeerK40t scene display."""
        if self.bounds is None:
            return None
        min_pt, max_pt = self.bounds
        # Return XY bounds (top-down view) in native units (1/1000 mm)
        # MeerK40t uses 1/1000 mm as native units
        from meerk40t.core.units import UNITS_PER_MM

        return (
            min_pt[0] * UNITS_PER_MM,
            min_pt[1] * UNITS_PER_MM,
            max_pt[0] * UNITS_PER_MM,
            max_pt[1] * UNITS_PER_MM,
        )

    def default_map(self, default_map=None):
        """Provide default mapping for node operations."""
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "PointCloud3D"
        default_map["points"] = len(self)
        default_map["layers"] = self.num_layers
        default_map["desc"] = f"{len(self)} pts, {self.num_layers} layers"
        if self.bounds is not None:
            min_pt, max_pt = self.bounds
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
        self._bounds_dirty = True
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
        return path


def register_element_types(kernel):
    """Register PointCloud3D element type with kernel."""
    from meerk40t.core.node.bootstrap import bootstrap, defaults

    # Register the node type in bootstrap
    bootstrap["elem pointcloud3d"] = PointCloud3DNode
    defaults["elem pointcloud3d"] = {}

    # Register tree format string
    kernel.register("format/elem pointcloud3d", "{element_type} {desc}")
