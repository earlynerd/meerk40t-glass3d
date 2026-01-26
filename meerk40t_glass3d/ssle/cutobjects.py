"""
SSLE Cut Objects for MeerK40t

Custom cut objects for subsurface laser engraving that handle
Z-axis movement and layer-by-layer processing.
"""

import numpy as np


class SSLECut:
    """
    Cut object representing an SSLE point cloud engraving operation.

    This cut object contains all the points to be engraved and handles
    the Z-axis movement between layers.
    """

    def __init__(
        self,
        points,
        dwell_time=1.0,
        refractive_index=1.5,
        thermal_pause_points=10000,
        thermal_pause_ms=500,
        settings=None,
        passes=1,
    ):
        """
        Initialize an SSLE cut object.

        Args:
            points: Nx3 numpy array of XYZ coordinates in mm
            dwell_time: Time to dwell at each point in ms
            refractive_index: Material refractive index for correction
            thermal_pause_points: Number of points between thermal pauses
            thermal_pause_ms: Duration of thermal pause in ms
            settings: Dictionary of additional settings
            passes: Number of passes to make
        """
        self.points = points
        self.dwell_time = dwell_time
        self.refractive_index = refractive_index
        self.thermal_pause_points = thermal_pause_points
        self.thermal_pause_ms = thermal_pause_ms
        self.settings = settings if settings is not None else {}
        self.passes = passes

        # Operation type identifier
        self.operation = "SSLE"

        # Calculate unique Z layers
        if self.points is not None and len(self.points) > 0:
            self.unique_z = np.unique(self.points[:, 2])
        else:
            self.unique_z = np.array([])

    def __len__(self):
        """Return the number of points."""
        if self.points is None:
            return 0
        return len(self.points)

    @property
    def num_layers(self):
        """Return the number of unique Z layers."""
        return len(self.unique_z)

    def points_in_layer(self, z_value):
        """Get all points at a specific Z value."""
        if self.points is None:
            return np.array([])
        mask = self.points[:, 2] == z_value
        return self.points[mask]

    def apply_refraction_correction(self, z_mm, surface_z=0.0):
        """
        Apply refraction correction to a Z depth.

        When focusing inside glass, the apparent focal point is
        different from the actual focal point due to refraction.

        Args:
            z_mm: Target Z depth in mm (from top surface)
            surface_z: Z position of the glass top surface

        Returns:
            Corrected Z position for the focus mechanism
        """
        depth = z_mm - surface_z
        if depth <= 0:
            return z_mm

        # Snell's law correction for apparent depth
        # apparent_depth = actual_depth / refractive_index
        # So to reach actual_depth, we need to move more
        corrected_depth = depth * self.refractive_index
        return surface_z + corrected_depth

    def generator(self):
        """
        Generate commands for SSLE engraving.

        Yields tuples of (command_type, *args) for the driver to process:
        - ("ssle_z_move", z_mm, corrected_z_mm): Move Z to layer
        - ("ssle_dwell", x_mm, y_mm, dwell_ms): Engrave point
        - ("ssle_thermal_pause", pause_ms): Thermal pause
        - ("ssle_layer_start", layer_idx, z_mm): Layer start marker
        - ("ssle_layer_end", layer_idx): Layer end marker
        """
        if self.points is None or len(self.points) == 0:
            return

        total_points = 0

        for layer_idx, z_value in enumerate(sorted(self.unique_z)):
            # Get points in this layer
            layer_points = self.points_in_layer(z_value)

            # Calculate corrected Z for refraction
            corrected_z = self.apply_refraction_correction(z_value)

            # Signal layer start
            yield ("ssle_layer_start", layer_idx, float(z_value))

            # Move Z to this layer
            yield ("ssle_z_move", float(z_value), float(corrected_z))

            # Engrave each point in the layer
            for point in layer_points:
                x_mm, y_mm = float(point[0]), float(point[1])

                # Yield dwell command
                yield ("ssle_dwell", x_mm, y_mm, self.dwell_time)

                total_points += 1

                # Check for thermal pause
                if total_points % self.thermal_pause_points == 0:
                    yield ("ssle_thermal_pause", self.thermal_pause_ms)

            # Signal layer end
            yield ("ssle_layer_end", layer_idx)

    def major_axis(self):
        """Return whether this cut is primarily vertical or horizontal."""
        return 0  # Horizontal (X-axis primary)

    def x(self):
        """Return starting X coordinate in native units."""
        if self.points is None or len(self.points) == 0:
            return 0
        from meerk40t.core.units import UNITS_PER_MM

        return self.points[0, 0] * UNITS_PER_MM

    def y(self):
        """Return starting Y coordinate in native units."""
        if self.points is None or len(self.points) == 0:
            return 0
        from meerk40t.core.units import UNITS_PER_MM

        return self.points[0, 1] * UNITS_PER_MM

    def start(self):
        """Return the starting point as complex number in native units."""
        return complex(self.x(), self.y())

    def end(self):
        """Return the ending point as complex number in native units."""
        if self.points is None or len(self.points) == 0:
            return complex(0, 0)
        from meerk40t.core.units import UNITS_PER_MM

        return complex(
            self.points[-1, 0] * UNITS_PER_MM, self.points[-1, 1] * UNITS_PER_MM
        )

    def reverse(self):
        """Reverse the point order (not typically used for SSLE)."""
        if self.points is not None:
            # For SSLE, we should maintain bottom-up order
            # So reversing is not recommended
            pass

    def generate(self):
        """
        Legacy generator interface for MeerK40t compatibility.

        Yields simplified cut commands.
        """
        for cmd in self.generator():
            yield cmd
