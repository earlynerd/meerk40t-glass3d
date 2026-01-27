# Glass3D Integration with MeerK40t - Implementation Plan

## Overview

This document provides a detailed implementation plan for integrating Glass3D's subsurface laser engraving (SSLE) capabilities into the MeerK40t open-source laser control software.

**Last Updated**: 2025-01-27

## Current Status Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Z-Axis Support in Balormk | **COMPLETE** |
| 2 | Plugin Structure | **COMPLETE** |
| 3 | PointCloud3D Element | **COMPLETE** |
| 4 | SSLE Operation | **COMPLETE** |
| 5 | File Loaders | **COMPLETE** |
| 6 | GUI Panels | **COMPLETE** |
| 7 | Scene Rendering | **COMPLETE** |
| 8 | Driver Integration | **NOT STARTED** |
| 9 | End-to-End Testing | **NOT STARTED** |

---

## Repository Strategy

### Two-Part Approach

1. **Fork meerk40t** → Add Z-axis jogging support to balormk (contribute upstream)
   - Repository: `github.com/<user>/meerk40t` (fork)
   - Branch: `feature/balor-z-axis`
   - Goal: Enable Z-axis controls for galvo devices

2. **New plugin repository** → Glass3D-specific SSLE features
   - Repository: `github.com/<user>/meerk40t-glass3d`
   - Standalone pip-installable plugin
   - Depends on meerk40t but doesn't modify it

### Why This Approach

- Z-axis support benefits all galvo users → good upstream contribution
- SSLE is specialized → better as optional plugin
- Clean separation of concerns
- Easier maintenance and updates

---

## Phase 1: Add Z-Axis Support to Balormk [COMPLETE]

**Location**: meerk40t fork, `meerk40t/balormk/`

### 1.1 Z-Axis Settings in Device [COMPLETE]

**File**: `meerk40t/balormk/device.py` (lines 431-552)

Implemented settings:
- `z_axis_enabled` (bool, default: False)
- `z_steps_per_mm` (float, default: 1000.0)
- `z_min_mm` (float, default: 0.0)
- `z_max_mm` (float, default: 100.0)
- `z_speed_min` (int, default: 100)
- `z_speed_max` (int, default: 1000)
- `z_acc_time` (int, default: 100ms)
- `z_jog_small`, `z_jog_medium`, `z_jog_large` (Length)

### 1.2 Z-Axis Console Commands [COMPLETE]

**File**: `meerk40t/balormk/galvo_commands.py` (lines 740-890)

Implemented commands:
- `z_home` - Home Z-axis to origin
- `z_move <distance>` - Relative movement (e.g., `z_move 1mm`)
- `z_move_to <position>` - Absolute positioning
- `z_pos` - Query current Z position
- `z_jog_up_small`, `z_jog_down_small` - Small jog
- `z_jog_up_medium`, `z_jog_down_medium` - Medium jog
- `z_jog_up_large`, `z_jog_down_large` - Large jog

### 1.3 Z-Axis Driver Methods [COMPLETE]

**File**: `meerk40t/balormk/driver.py` (lines 688-777)

Implemented methods:
- `z_home()` - Home axis, set position to 0.0mm
- `z_move_relative(distance_mm)` - Relative movement
- `z_move_absolute(position_mm)` - Absolute movement with bounds checking
- `z_get_position()` - Returns current position in mm
- `_wait_for_axis_idle(timeout_s)` - Wait for movement completion

### 1.4 Unit Tests [COMPLETE]

**File**: `test/test_balor_z_axis.py`

Test coverage:
- `test_z_axis_settings_exist`
- `test_z_axis_settings_can_be_changed`
- `test_z_driver_methods_exist`
- `test_z_commands_disabled_by_default`
- `test_z_position_bounds_clamping`
- `test_z_console_commands_registered`

---

## Phase 2: Plugin Structure [COMPLETE]

**Location**: `meerk40t-glass3d/`

### 2.1 Repository Structure [COMPLETE]

```
meerk40t-glass3d/
├── README.md
├── LICENSE
├── setup.cfg                  # Entry point: meerk40t.extension
├── meerk40t_glass3d/
│   ├── __init__.py
│   ├── plugin.py              # Main plugin entry point
│   ├── ssle/
│   │   ├── __init__.py
│   │   ├── operation.py       # SSLE operation node
│   │   ├── element.py         # PointCloud3D element node
│   │   └── cutobjects.py      # SSLECut class
│   ├── mesh/
│   │   ├── __init__.py
│   │   ├── loader.py          # STL/OBJ/3MF import + console commands
│   │   └── pointcloud.py      # Point cloud generation strategies
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── gui.py             # GUI plugin registration
│   │   ├── ssle_panel.py      # SSLE operation settings panel
│   │   └── pointcloud_panel.py # PointCloud properties panel
│   └── core/
│       └── __init__.py
└── tests/
    └── __init__.py
```

### 2.2 Setup Configuration [COMPLETE]

**File**: `setup.cfg`

**NOTE**: Entry point group must be `meerk40t.extension` (not `meerk40t.plugins`):

```ini
[options.entry_points]
meerk40t.extension =
    glass3d = meerk40t_glass3d.plugin:plugin
```

### 2.3 Plugin Entry Point [COMPLETE]

**File**: `meerk40t_glass3d/plugin.py`

Implemented:
- Plugin lifecycle handling (plugins, invalidate, register, boot, ready)
- Dependency checking (numpy, trimesh)
- Console commands: `glass3d`, `glass3d help`, `glass3d info`

---

## Phase 3: PointCloud3D Element [COMPLETE]

**File**: `meerk40t_glass3d/ssle/element.py`

### Implemented Features

- `PointCloud3DNode` class inheriting from `Node`
- `point_data` - Nx3 numpy array of XYZ coordinates in mm
- `intensities` - Optional Nx1 array
- `layer_indices` - Optional Nx1 array
- `source_file` - Path to original mesh
- `generation_strategy` - Strategy identifier
- `point_spacing_mm` - Point spacing parameter
- `bounds` property - Returns (min_xyz, max_xyz)
- `num_layers` property - Number of unique Z layers
- `bbox()` - 2D bounding box for scene display
- `sort_bottom_up()` - Sort points by Z ascending
- `as_geometry()` - Returns Geomstr with all points
- `register_element_types()` - Kernel registration

---

## Phase 4: SSLE Operation [COMPLETE]

**File**: `meerk40t_glass3d/ssle/operation.py`

### Implemented Features

- `SSLEOperationNode` class inheriting from `Node` and `Parameters`
- Operation type: `"op ssle"`
- Settings with defaults:
  - `dwell_time` (ms, default: 1.0)
  - `power` (0-1000, default: 500)
  - `frequency` (kHz, default: 30.0)
  - `thermal_pause_points` (default: 10000)
  - `thermal_pause_ms` (default: 500)
  - `refractive_index` (default: 1.5 for K9)
  - `apply_refraction_correction` (bool, default: True)
  - `optimize_path` (bool, default: True)
- `can_drop()` / `drop()` - Drag-drop support
- `classify()` - Accept PointCloud3D elements
- `as_cutobjects()` - Generate SSLECut objects
- `time_estimate()` - Execution time estimation

### SSLECut Class [COMPLETE]

**File**: `meerk40t_glass3d/ssle/cutobjects.py`

- Stores point cloud data with SSLE settings
- `generator()` yields command tuples:
  - `("ssle_layer_start", layer_idx, z_mm)`
  - `("ssle_z_move", z_mm, corrected_z_mm)`
  - `("ssle_dwell", x_mm, y_mm, dwell_ms)`
  - `("ssle_thermal_pause", pause_ms)`
  - `("ssle_layer_end", layer_idx)`
- Refraction correction via `apply_refraction_correction()`
- CutCode interface methods: `start()`, `end()`, `x()`, `y()`

---

## Phase 5: File Loaders [COMPLETE]

**File**: `meerk40t_glass3d/mesh/loader.py`

### Implemented Features

- `load_mesh(filepath)` - Uses trimesh
- Console command `glass3d load <file>`:
  - Supports .stl, .obj, .ply, .3mf
  - Options: `-s strategy`, `-p spacing`
  - Auto-generates point cloud
- Console command `glass3d preview_mesh <file>` - Preview without loading
- Drag-drop handlers for all formats

### Point Cloud Generation [COMPLETE]

**File**: `meerk40t_glass3d/mesh/pointcloud.py`

Strategies:
- `generate_surface_points()` - Surface sampling
- `generate_solid_points()` - Volumetric sampling
- `generate_contour_points()` - Contour generation
- `generate_layer_points()` - Layer-based generation

---

## Phase 6: GUI Panels [COMPLETE]

### SSLE Operation Panel [COMPLETE]

**File**: `meerk40t_glass3d/gui/ssle_panel.py`

- Laser Settings: Power, Dwell time, Frequency
- Material Settings: Refractive index, Presets (K9, BK7, Fused Silica, Acrylic)
- Thermal Management: Pause interval, Pause duration

### PointCloud Property Panel [COMPLETE]

**File**: `meerk40t_glass3d/gui/pointcloud_panel.py`

- Point Cloud Info: Points count, Layers, Size, Source file
- Actions: Regenerate, Optimize, Export
- Time estimate display

---

## Phase 7: Scene Rendering [COMPLETE]

**Problem**: PointCloud3D elements load successfully but are **not visible** in the GUI scene.

### 7.1 Why It Doesn't Render

MeerK40t's rendering system (`meerk40t/gui/laserrender.py`) uses a type-based dispatch in `render_node()`. It checks element types and assigns draw functions:

```python
if node.type in ("elem path", "elem ellipse", ...):
    node.draw = self.draw_vector
elif node.type == "elem point":
    node.draw = self.draw_point_node
# ... no case for "elem pointcloud3d"
```

The `elem pointcloud3d` type is not recognized, so it returns `False` (cannot render).

### 7.2 Implementation Options

**Option A: Add draw method to PointCloud3DNode**

Add a `draw()` method directly to the element class that uses wxPython graphics context:

```python
def draw(self, gc, draw_mode, alpha=255):
    """Draw point cloud as dots in the scene."""
    if self.point_data is None:
        return

    from meerk40t.core.units import UNITS_PER_MM

    # Set point style
    gc.SetPen(wx.Pen(wx.Colour(128, 0, 255, alpha), 1))
    gc.SetBrush(wx.Brush(wx.Colour(128, 0, 255, alpha)))

    # Draw each point as a small circle
    for pt in self.point_data:
        x = pt[0] * UNITS_PER_MM
        y = pt[1] * UNITS_PER_MM
        gc.DrawEllipse(x - 50, y - 50, 100, 100)
```

**Option B: Register renderer in GUI plugin**

In `gui/gui.py`, extend the LaserRender class or register a custom renderer:

```python
def plugin(kernel, lifecycle):
    if lifecycle == "register":
        # Register custom renderer for pointcloud3d
        kernel.register("render/elem pointcloud3d", draw_pointcloud3d)
```

**Option C: Use as_geometry() with existing point renderer**

The element already has `as_geometry()` that returns points. Need to ensure the renderer recognizes and draws these.

### 7.3 Tasks

- [x] **7.3.1**: Determine best rendering approach (A, B, or C) - **Used Option A: draw method on node**
- [x] **7.3.2**: Implement draw method or renderer registration
- [x] **7.3.3**: Add color/style controls (color by Z-depth, layer highlighting) - **Rainbow gradient blue->red**
- [x] **7.3.4**: Add selection/highlighting support - **Bounding box when emphasized**
- [x] **7.3.5**: Test rendering performance with large point clouds (>100k points) - **Subsampled to 10k for display**

### 7.4 Implementation Notes

**Key discoveries:**
1. Must register element type in `elem_nodes`, `elem_group_nodes` tuples AND patch all modules that imported them
2. Don't override Node's `bounds` property - implement `bbox()` instead
3. Elements need `matrix` attribute and `preprocess()` method for drag/move support
4. Subsampling to ~10k points with small rectangles gives good performance

---

## Phase 8: Driver Integration [NOT STARTED]

**Problem**: SSLECut generates custom command tuples, but the balormk driver doesn't understand them.

### 8.1 Current State

The SSLECut `generator()` yields tuples like:
- `("ssle_z_move", z_mm, corrected_z_mm)`
- `("ssle_dwell", x_mm, y_mm, dwell_ms)`

But the balormk driver's `geometry()` method only processes standard Geomstr segments and doesn't recognize SSLE commands.

### 8.2 Integration Strategy

**Option A: Extend balormk driver (in meerk40t fork)**

Add SSLE command handling to the driver's main processing loop:

```python
# In driver.py geometry() or a new ssle_process() method
def process_ssle_cut(self, ssle_cut):
    """Process an SSLECut object with Z-axis control."""
    for cmd in ssle_cut.generator():
        cmd_type = cmd[0]

        if cmd_type == "ssle_z_move":
            z_mm, corrected_z = cmd[1], cmd[2]
            self.z_move_absolute(corrected_z)

        elif cmd_type == "ssle_dwell":
            x_mm, y_mm, dwell_ms = cmd[1], cmd[2], cmd[3]
            # Convert to galvo coordinates and fire
            self._dwell_at_point(x_mm, y_mm, dwell_ms)

        elif cmd_type == "ssle_thermal_pause":
            pause_ms = cmd[1]
            time.sleep(pause_ms / 1000.0)
```

**Option B: Convert SSLECut to standard CutCode**

Modify `as_cutobjects()` to yield standard DwellCut objects with Z metadata:

```python
from meerk40t.core.cutcode.dwellcut import DwellCut

def as_cutobjects(self, closed_distance=15, passes=1):
    for child in self.children:
        # ... get point cloud ...
        for z_value in unique_z:
            # Yield a marker for Z movement (custom handling needed)
            yield ZMoveCut(z_value, self.refractive_index)

            for point in layer_points:
                yield DwellCut(
                    start=complex(x * UNITS_PER_MM, y * UNITS_PER_MM),
                    settings=self.derive(),
                    dwell_time=self.dwell_time,
                )
```

**Option C: Register SSLE as special operation type**

Register a custom spooler/executor for "op ssle" that handles SSLECut specially.

### 8.3 Tasks

- [ ] **8.3.1**: Choose integration strategy (A, B, or C)
- [ ] **8.3.2**: Implement Z-axis movement during cut execution
- [ ] **8.3.3**: Implement point dwelling (galvo positioning + laser fire)
- [ ] **8.3.4**: Implement thermal pause handling
- [ ] **8.3.5**: Add progress reporting (layer X of Y, point N of M)
- [ ] **8.3.6**: Add abort/pause support during SSLE execution
- [ ] **8.3.7**: Test with mock driver (no hardware)
- [ ] **8.3.8**: Test with real hardware

### 8.4 Required Changes to Balormk (meerk40t fork)

The following additions to the balormk driver are needed:

```python
# In driver.py

def _dwell_at_point(self, x_mm, y_mm, dwell_ms):
    """Position galvo and fire laser for specified dwell time."""
    con = self.connection

    # Convert mm to galvo units
    x_galvo = self._mm_to_galvo(x_mm)
    y_galvo = self._mm_to_galvo(y_mm)

    # Move to position
    con.goto_xy(x_galvo, y_galvo)

    # Calculate dwell in timing units
    dwell_ticks = int(dwell_ms * 1000)  # Convert to microseconds

    # Fire laser
    con.laser_control(True)
    con.wait(dwell_ticks)
    con.laser_control(False)

def execute_ssle_cut(self, ssle_cut):
    """Execute an SSLE cut object with full Z-axis control."""
    from meerk40t_glass3d.ssle.cutobjects import SSLECut

    if not isinstance(ssle_cut, SSLECut):
        return

    for cmd in ssle_cut.generator():
        # Check for abort
        if self._abort_requested:
            break

        cmd_type = cmd[0]

        if cmd_type == "ssle_layer_start":
            layer_idx, z_mm = cmd[1], cmd[2]
            self.signal("ssle_layer", layer_idx, ssle_cut.num_layers)

        elif cmd_type == "ssle_z_move":
            z_mm, corrected_z = cmd[1], cmd[2]
            if self.service.z_axis_enabled:
                self.z_move_absolute(corrected_z)

        elif cmd_type == "ssle_dwell":
            x_mm, y_mm, dwell_ms = cmd[1], cmd[2], cmd[3]
            self._dwell_at_point(x_mm, y_mm, dwell_ms)

        elif cmd_type == "ssle_thermal_pause":
            pause_ms = cmd[1]
            self.signal("ssle_thermal_pause", pause_ms)
            time.sleep(pause_ms / 1000.0)

        elif cmd_type == "ssle_layer_end":
            layer_idx = cmd[1]
            self.signal("ssle_layer_complete", layer_idx)
```

---

## Phase 9: End-to-End Testing [NOT STARTED]

### 9.1 Test Scenarios

- [ ] **9.1.1**: Load STL → See point cloud in scene → Verify bounds match
- [ ] **9.1.2**: Create SSLE operation → Add point cloud → Verify settings
- [ ] **9.1.3**: Dry-run execution (mock driver) → Verify command sequence
- [ ] **9.1.4**: Real hardware test → Single layer → Verify point placement
- [ ] **9.1.5**: Real hardware test → Multi-layer → Verify Z movement
- [ ] **9.1.6**: Real hardware test → Full model → Verify thermal pauses

### 9.2 Known Issues to Address

- [ ] 3MF loading fails (trimesh issue?)
- [ ] Console commands `glass3d preview` and `glass3d generate` documented but not implemented
- [ ] No visual feedback during SSLE execution

---

## Implementation Priority

### Minimum Viable Product (MVP)

To get basic end-to-end functionality working:

1. **Phase 7.3.2**: Implement basic rendering (see points in scene)
2. **Phase 8.3.2-8.3.4**: Implement driver execution (Z move + dwell + pause)
3. **Phase 9.1.3**: Verify with mock driver

### Full Integration

After MVP:

1. Phase 7.3.3-7.3.5: Enhanced rendering (colors, selection, performance)
2. Phase 8.3.5-8.3.6: Progress reporting and abort support
3. Phase 9.1.4-9.1.6: Hardware testing
4. Fix 3MF loading
5. Implement missing console commands

---

## Testing Checklist

### Phase 1 Tests (Balormk Z-Axis) [ALL PASSING]
- [x] Z-axis settings appear in device config when enabled
- [x] `z_home` command homes the axis
- [x] `z_move 1mm` moves up 1mm
- [x] `z_move -1mm` moves down 1mm
- [x] `z_move_to 10mm` moves to absolute position
- [x] `z_pos` returns current position
- [x] Bounds checking prevents out-of-range moves
- [ ] Z jog panel buttons appear and work (needs GUI testing)
- [ ] Mock mode works without hardware (needs testing)

### Phase 2-6 Tests (Glass3D Plugin)
- [x] Plugin loads without errors
- [x] `glass3d help` shows help text
- [x] `glass3d load test.stl` loads STL file
- [x] PointCloud3D element appears in tree
- [ ] Element shows correct bounds in properties (needs verification)
- [ ] SSLE operation can be created (needs testing)
- [ ] PointCloud3D can be added to SSLE operation (needs testing)
- [ ] SSLE settings panel shows and saves values (needs testing)
- [ ] Preview shows 2D projection of points (NOT IMPLEMENTED)
- [ ] Dry-run executes without errors (NOT IMPLEMENTED)

### Phase 7 Tests (Rendering)
- [ ] Point cloud visible in scene view
- [ ] Points colored by Z-depth
- [ ] Selection highlighting works
- [ ] Performance acceptable with 100k+ points

### Phase 8 Tests (Driver Integration)
- [ ] Z-axis moves between layers
- [ ] Laser dwells at each point
- [ ] Thermal pauses execute
- [ ] Progress reported correctly
- [ ] Abort stops execution cleanly

---

## Getting Started Commands

```bash
# 1. Clone meerk40t fork with Z-axis support
git clone https://github.com/<user>/meerk40t.git
cd meerk40t
git checkout feature/balor-z-axis

# 2. Clone plugin repository
cd ..
git clone https://github.com/<user>/meerk40t-glass3d.git

# 3. Set up development environment
py -3.10 -m pip install -e ./meerk40t[gui]
py -3.10 -m pip install -e ./meerk40t-glass3d
py -3.10 -m pip install numpy trimesh pytest

# 4. Run meerk40t to test
py -3.10 -m meerk40t
```

---

## Notes

1. **Entry point fix**: Plugin must use `meerk40t.extension` not `meerk40t.plugins`
2. **Test incrementally**: Each phase should be testable before moving to the next
3. **Use mock mode**: Development can be done with `mock=True`, no hardware needed
4. **Follow meerk40t patterns**: Look at existing code (GRBL, balormk) for conventions
