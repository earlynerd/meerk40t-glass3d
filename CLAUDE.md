# Claude Session Notes - MeerK40t Glass3D Plugin

## Project Overview

This project consists of two repositories:
1. **meerk40t fork** (`C:\Users\msylvester\Documents\meerk40t`) - Z-axis support for balormk galvo devices
2. **meerk40t-glass3d plugin** (`C:\Users\msylvester\Documents\meerk40t-glass3d`) - SSLE (Subsurface Laser Engraving) plugin

## Current Status (2025-01-27)

### Completed
- **Phase 1-6**: Z-axis support, plugin structure, PointCloud3D element, SSLE operation, file loaders, GUI panels
- **Phase 7**: Scene rendering - points now visible with Z-depth coloring (blue=deep, red=surface)
- Point clouds can be loaded, displayed, selected, and repositioned via drag
- **Phase 8**: Driver integration - SSLECut commands now processed by balormk driver
  - Added `_execute_ssle_cut()` method to `BalorDriver` class
  - Handles all SSLECut generator commands: `ssle_z_move`, `ssle_dwell`, `ssle_thermal_pause`, `ssle_layer_start/end`
  - Uses existing Z-axis methods (`z_move_absolute`) for layer positioning
  - Refraction correction applied automatically
  - Thermal pause support for heat management

### In Progress
- **Phase 9**: End-to-end testing
  - Mock driver testing: COMPLETE (11/11 tests passing)
  - Real hardware testing: PENDING (requires physical access to laser)

## Key Learnings & Gotchas

### 1. Plugin Entry Point
The plugin must register under `meerk40t.extension`, NOT `meerk40t.plugins`:
```ini
# setup.cfg
[options.entry_points]
meerk40t.extension =
    glass3d = meerk40t_glass3d.plugin:plugin
```

### 2. Element Type Registration - CRITICAL
MeerK40t uses hardcoded tuples in `meerk40t/core/elements/element_types.py` to filter elements. These are imported at module load time by many modules. To add a new element type, you must patch ALL modules that imported these tuples:

```python
def register_element_types(kernel):
    import meerk40t.core.elements.element_types as et
    import meerk40t.core.elements.elements as elems_module
    import meerk40t.gui.scenewidgets.selectionwidget as selwidget

    our_type = "elem pointcloud3d"

    # Update source module
    et.elem_nodes = et.elem_nodes + (our_type,)
    et.elem_group_nodes = et.elem_group_nodes + (our_type,)
    et.elem_ref_nodes = et.elem_ref_nodes + (our_type,)

    # Update ALL modules that imported these at load time
    elems_module.elem_nodes = elems_module.elem_nodes + (our_type,)
    elems_module.elem_group_nodes = elems_module.elem_group_nodes + (our_type,)
    selwidget.elem_nodes = selwidget.elem_nodes + (our_type,)
    selwidget.elem_group_nodes = selwidget.elem_group_nodes + (our_type,)
```

Without this, elements won't render or be draggable.

### 3. Bounds vs bbox() - Don't Override `bounds` Property
The Node base class has its own `bounds` property with caching via `_bounds`. Do NOT override it. Instead:
- Implement `bbox(transformed=True, with_stroke=False)` returning `(x1, y1, x2, y2)` in native units
- The Node's `bounds` property will call `bbox()` and handle caching
- Call `self.set_dirty_bounds()` when data changes

### 4. Matrix Transformations
Elements need these for drag/move support:
```python
def __init__(self, **kwargs):
    from meerk40t.svgelements import Matrix
    self.matrix = kwargs.pop("matrix", None)
    # ... other init ...
    if self.matrix is None:
        self.matrix = Matrix()

def preprocess(self, context, matrix, plan):
    self.matrix *= matrix
    self.set_dirty_bounds()

def bbox(self, transformed=True, with_stroke=False):
    # Calculate raw bounds...
    if transformed and self.matrix is not None:
        # Apply matrix to corners and return transformed bounds
```

### 5. Draw Method Signature
```python
def draw(self, node, gc, draw_mode, zoomscale=1.0, alpha=255):
    # node is passed but self is the same object
    # gc is wxPython GraphicsContext
    # Apply self.matrix when drawing coordinates
```

### 6. Native Units
MeerK40t uses native units (1/1000 mm). Convert with:
```python
from meerk40t.core.units import UNITS_PER_MM
x_native = x_mm * UNITS_PER_MM
```

### 7. Rendering Performance
For large point clouds:
- Subsample to ~10,000 points for display
- Use simple shapes (small rectangles) instead of circles
- Set pen to TRANSPARENT_PEN when only filling

## File Structure

```
meerk40t-glass3d/
├── setup.cfg                    # Entry point: meerk40t.extension
├── meerk40t_glass3d/
│   ├── plugin.py               # Main entry, console commands
│   ├── ssle/
│   │   ├── element.py          # PointCloud3DNode
│   │   ├── operation.py        # SSLEOperationNode
│   │   └── cutobjects.py       # SSLECut
│   ├── mesh/
│   │   ├── loader.py           # STL/OBJ loading, glass3d load command
│   │   └── pointcloud.py       # Point generation strategies
│   └── gui/
│       ├── gui.py              # GUI plugin registration
│       ├── ssle_panel.py       # SSLE operation settings
│       └── pointcloud_panel.py # PointCloud properties (uses bounds_3d)
```

## Useful Commands

```bash
# Install in dev mode
py -3.10 -m pip install -e ./meerk40t
py -3.10 -m pip install -e ./meerk40t-glass3d

# Run
py -3.10 -m meerk40t

# Console commands
glass3d help
glass3d load "path/to/file.stl"
glass3d info
glass3d debug
```

## Phase 9 Testing Results

### Mock Driver Tests (All Passing)

Test files in `tests/`:
- `test_phase9_integration.py` - 6 tests
- `test_mock_driver_execution.py` - 2 tests
- `test_z_axis_commands.py` - 3 tests

**Total: 11/11 tests passing**

Key verifications:
- SSLECut command generation with correct layer ordering
- Refraction correction (n=1.5: 5mm target -> 7.5mm corrected)
- Operation -> cutobject pipeline
- Driver command flow simulation
- Z-axis command sequence (SetAxisMotionParam, MoveAxisTo)
- Z-axis bounds clamping
- Abort handling during execution

### Remaining Hardware Tests

When you have access to the laser:
1. **Single layer test** - Fixed Z, verify laser fires at correct XY positions
2. **Multi-layer test** - Verify Z movement between layers
3. **Refraction verification** - Check focus depth matches material
4. **Thermal pause timing** - Ensure pauses prevent overheating

## Next Steps

1. **Hardware Testing** (when available)
   - Run single-layer engraving test
   - Verify Z-axis moves to correct depths
   - Test full 3D point cloud engraving

2. **Future Enhancements**
   - Point ordering optimization (minimize travel distance)
   - Progress reporting during SSLE execution
   - Power/frequency per-layer settings
   - Support for intensity-based dwell time variation

## Driver Integration Details (Phase 8)

The SSLECut handler was added to `meerk40t/balormk/driver.py`:

```python
# Import (with fallback if plugin not installed)
try:
    from meerk40t_glass3d.ssle.cutobjects import SSLECut
    SSLE_AVAILABLE = True
except ImportError:
    SSLECut = None
    SSLE_AVAILABLE = False

# In plot_start() method, added:
elif SSLE_AVAILABLE and isinstance(q, SSLECut):
    self._execute_ssle_cut(q, con)

# New method _execute_ssle_cut() handles:
# - ssle_layer_start: Log layer info
# - ssle_z_move: Call z_move_absolute(corrected_z)
# - ssle_dwell: Convert mm to galvo units, goto, fire laser
# - ssle_thermal_pause: Insert delay for heat management
# - ssle_layer_end: Log completion
```

See `meerk40t-integration-plan.md` for detailed task breakdown.
