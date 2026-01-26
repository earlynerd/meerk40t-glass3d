"""
SSLE Operation Node for MeerK40t

Defines the subsurface laser engraving operation type.
"""

import numpy as np
from meerk40t.core.node.node import Node
from meerk40t.core.parameters import Parameters
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Color


class SSLEOperationNode(Node, Parameters):
    """
    Operation node for subsurface laser engraving.

    This operation takes PointCloud3D elements and generates
    layer-by-layer engraving commands with Z-axis control.
    """

    def __init__(self, settings=None, **kwargs):
        if settings is not None:
            settings = dict(settings)
        Parameters.__init__(self, settings, **kwargs)

        # Elements this operation can accept
        self._allowed_elements_dnd = ("elem pointcloud3d",)
        self._allowed_elements = ("elem pointcloud3d",)

        # Operation flags
        self.dangerous = False
        self.stopop = True
        self.label = "SSLE"
        self.output = True

        # Default color for this operation type
        self.color = Color("purple")

        # SSLE-specific settings with defaults
        if "dwell_time" not in self.settings:
            self.settings["dwell_time"] = 1.0  # ms
        if "power" not in self.settings:
            self.settings["power"] = 500  # 50% (stored as 0-1000)
        if "frequency" not in self.settings:
            self.settings["frequency"] = 30.0  # kHz

        # Thermal management defaults
        if "thermal_pause_points" not in self.settings:
            self.settings["thermal_pause_points"] = 10000
        if "thermal_pause_ms" not in self.settings:
            self.settings["thermal_pause_ms"] = 500

        # Material settings defaults
        if "refractive_index" not in self.settings:
            self.settings["refractive_index"] = 1.5  # K9 glass
        if "apply_refraction_correction" not in self.settings:
            self.settings["apply_refraction_correction"] = True

        # Path optimization
        if "optimize_path" not in self.settings:
            self.settings["optimize_path"] = True

        self.allowed_attributes = []

        super().__init__(type="op ssle", **kwargs)
        self._formatter = "{enabled}{element_type} {power_pct}% @{dwell}ms {frequency}kHz"

    def __repr__(self):
        return "SSLEOperationNode()"

    # Property accessors for common settings
    @property
    def dwell_time(self):
        return self.settings.get("dwell_time", 1.0)

    @dwell_time.setter
    def dwell_time(self, value):
        self.settings["dwell_time"] = value

    @property
    def power(self):
        return self.settings.get("power", 500)

    @power.setter
    def power(self, value):
        self.settings["power"] = value

    @property
    def frequency(self):
        return self.settings.get("frequency", 30.0)

    @frequency.setter
    def frequency(self, value):
        self.settings["frequency"] = value

    @property
    def refractive_index(self):
        return self.settings.get("refractive_index", 1.5)

    @refractive_index.setter
    def refractive_index(self, value):
        self.settings["refractive_index"] = value

    @property
    def thermal_pause_points(self):
        return self.settings.get("thermal_pause_points", 10000)

    @thermal_pause_points.setter
    def thermal_pause_points(self, value):
        self.settings["thermal_pause_points"] = value

    @property
    def thermal_pause_ms(self):
        return self.settings.get("thermal_pause_ms", 500)

    @thermal_pause_ms.setter
    def thermal_pause_ms(self, value):
        self.settings["thermal_pause_ms"] = value

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        default_map["element_type"] = "SSLE"
        default_map["power_pct"] = f"{self.power / 10.0:.0f}"
        default_map["dwell"] = f"{self.dwell_time:.1f}"
        default_map["frequency"] = f"{self.frequency:.0f}"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["danger"] = "!DANGER! " if self.dangerous else ""
        default_map["color"] = self.color.hexrgb if self.color is not None else ""
        default_map.update(self.settings)
        return default_map

    def can_drop(self, drag_node):
        """Check if a node can be dropped onto this operation."""
        from meerk40t.core.elements.element_types import op_nodes

        if drag_node.has_ancestor("branch reg"):
            return False
        if drag_node.type in self._allowed_elements_dnd:
            return True
        elif drag_node.type == "reference" and drag_node.node.type in self._allowed_elements_dnd:
            return True
        elif drag_node.type in op_nodes:
            return True
        elif drag_node.type in ("file", "group"):
            return True
        return False

    def drop(self, drag_node, modify=True, flag=False):
        """Handle dropping a node onto this operation."""
        from meerk40t.core.elements.element_types import op_nodes

        if drag_node.type in self._allowed_elements_dnd:
            if modify:
                self.add_reference(drag_node, pos=None if flag else 0)
            return True
        elif drag_node.type == "reference":
            if drag_node.node.type not in self._allowed_elements_dnd:
                return False
            if modify:
                self.append_child(drag_node)
            return True
        elif drag_node.type in op_nodes:
            if modify:
                self.insert_sibling(drag_node)
            return True
        elif drag_node.type in ("file", "group"):
            some_nodes = False
            for e in drag_node.flat(self._allowed_elements):
                if modify:
                    self.add_reference(e)
                some_nodes = True
            return some_nodes
        return False

    def is_referenced(self, node):
        """Check if a node is already referenced by this operation."""
        for e in self.children:
            if e is node:
                return True
            if hasattr(e, "node") and e.node is node:
                return True
        return False

    def valid_node_for_reference(self, node):
        """Check if a node type can be referenced by this operation."""
        return node.type in self._allowed_elements

    def classify(self, node, fuzzy=False, fuzzydistance=100, usedefault=False):
        """Classify whether a node belongs in this operation."""
        if self.is_referenced(node):
            return False, False, None

        if node.type in self._allowed_elements:
            if self.valid_node_for_reference(node):
                self.add_reference(node)
                return True, self.stopop, ["pointcloud3d"]

        return False, False, None

    def load(self, settings, section):
        """Load operation settings from config."""
        settings.read_persistent_attributes(section, self)
        hexa = self.settings.get("hex_color")
        if hexa is not None:
            self.color = Color(hexa)
        self.updated()

    def save(self, settings, section):
        """Save operation settings to config."""
        for attr in ("label", "lock", "id"):
            if hasattr(self, attr) and attr in self.settings:
                self.settings[attr] = getattr(self, attr)
        if "hex_color" in self.settings:
            self.settings["hex_color"] = self.color.hexa

        settings.write_persistent_attributes(section, self)
        settings.write_persistent(section, "hex_color", self.color.hexa)
        settings.write_persistent_dict(section, self.settings)

    def time_estimate(self):
        """Estimate the time to complete this operation."""
        estimate = 0
        for child in self.children:
            if child.type == "reference":
                child = child.node
            if child.type == "elem pointcloud3d":
                # Each point takes dwell_time + movement time
                # Rough estimate: dwell_time per point + 0.1ms per point for movement
                num_points = len(child) if hasattr(child, "__len__") else 0
                estimate += num_points * (self.dwell_time + 0.1) / 1000.0

        hours, remainder = divmod(estimate, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}:{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"

    def preprocess(self, context, matrix, plan):
        """Preprocess operation values before execution."""
        native_mm = abs(complex(*matrix.transform_vector([0, UNITS_PER_MM])))
        self.settings["native_mm"] = native_mm

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for this operation.

        For SSLE, we generate SSLECut objects that the driver
        will handle specially for Z-axis movement.
        """
        from meerk40t_glass3d.ssle.cutobjects import SSLECut

        settings = self.derive()

        for child in self.children:
            if child.type == "reference":
                child = child.node
            if child.type != "elem pointcloud3d":
                continue
            if child.point_data is None or len(child.point_data) == 0:
                continue

            # Ensure sorted bottom-up for proper SSLE
            child.sort_bottom_up()

            # Yield one SSLECut for the entire point cloud
            yield SSLECut(
                points=child.point_data,
                dwell_time=self.dwell_time,
                refractive_index=self.refractive_index,
                thermal_pause_points=self.thermal_pause_points,
                thermal_pause_ms=self.thermal_pause_ms,
                settings=settings,
                passes=passes,
            )

    @property
    def bounds(self):
        """Calculate the bounds of all referenced elements."""
        if not self._bounds_dirty:
            return self._bounds

        self._bounds = None
        if self.output:
            if self._children:
                self._bounds = Node.union_bounds(
                    self._children, bounds=self._bounds, ignore_locked=False, ignore_hidden=True
                )
            self._bounds_dirty = False
        return self._bounds


def register_operation_types(kernel):
    """Register SSLE operation type with kernel."""
    from meerk40t.core.node.bootstrap import bootstrap, defaults

    # Register the operation type in bootstrap
    bootstrap["op ssle"] = SSLEOperationNode
    defaults["op ssle"] = {
        "dwell_time": 1.0,
        "power": 500,
        "frequency": 30.0,
        "color": "purple",
    }

    # Register tree format string
    kernel.register(
        "format/op ssle",
        "{enabled}{danger}{element_type} {power_pct}% @{dwell}ms {frequency}kHz {color}",
    )
