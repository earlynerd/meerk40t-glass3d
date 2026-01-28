# MeerK40t Glass3D Plugin

Subsurface Laser Engraving (SSLE) plugin for [MeerK40t](https://github.com/meerk40t/meerk40t).

SSLE creates 3D images inside transparent materials (glass, crystal, acrylic) by focusing a laser at precise depths to create micro-fractures that scatter light.

## Features

- Load 3D models (STL, OBJ, PLY, 3MF)
- Generate point clouds from mesh surfaces
- Layer-by-layer Z-axis control for galvo lasers
- Automatic refractive index correction for accurate focus depth
- Thermal management with configurable pauses
- Full GUI integration with MeerK40t

## Requirements

- MeerK40t 0.9.0 or later
- Galvo laser with Z-axis support (e.g., BJJCZ/EZCAD2 compatible)
- Python 3.9+
- Dependencies: numpy, trimesh

## Installation

```bash
pip install meerk40t-glass3d
```

Or for development:

```bash
git clone https://github.com/<user>/meerk40t-glass3d.git
cd meerk40t-glass3d
pip install -e ".[dev]"
```

## User Workflow

### Step 1: Import 3D Model

**GUI Options:**
- `File → Import 3D Model...` - Opens file dialog
- `Tools → Glass3D: Import 3D Model...` - Opens file dialog
- Drag-and-drop STL/OBJ/PLY/3MF file onto MeerK40t window

**Console:**
```
glass3d load "C:\path\to\model.stl"
```

The model is converted to a point cloud and displayed in the scene with Z-depth coloring (blue = deep, red = surface).

### Step 2: Create SSLE Operation

**GUI Options:**
- `Laser → Add SSLE Operation`
- `Tools → Glass3D: Create SSLE Operation`

**Console:**
```
ssle
```

### Step 3: Add Point Cloud to Operation

Drag the point cloud element from the Elements tree onto the SSLE operation in the Operations tree.

Or select the point cloud and run:
```
pointcloud_to_ssle
```

### Step 4: Configure SSLE Settings

Click the SSLE operation to open the settings panel:

| Setting | Description | Default |
|---------|-------------|---------|
| Power | Laser power percentage | 50% |
| Dwell Time | Time laser fires at each point (ms) | 1.0 ms |
| Frequency | Laser pulse frequency (kHz) | 30 kHz |
| Refractive Index | Material refractive index for focus correction | 1.50 |
| Thermal Pause Interval | Points between thermal pauses | 10,000 |
| Thermal Pause Duration | Length of thermal pause (ms) | 500 ms |

**Material Presets:**
| Material | Refractive Index |
|----------|------------------|
| K9 Crystal | 1.50 |
| BK7 Glass | 1.52 |
| Fused Silica | 1.46 |
| Acrylic (PMMA) | 1.49 |

### Step 5: Run the Job

Click **Start** to begin engraving. The plugin will:

1. Sort points bottom-up (deepest layer first)
2. Move Z-axis to each layer depth (with refraction correction)
3. Fire laser at each point for the configured dwell time
4. Insert thermal pauses to prevent overheating
5. Move to next layer and repeat

## Console Commands

```
glass3d help              Show help
glass3d load <file>       Load 3D model file
glass3d load <file> -s <strategy> -p <spacing>
                          Load with options:
                            -s: strategy (surface, solid, contour)
                            -p: point spacing in mm (default: 0.1)
glass3d info              Show info about loaded models
glass3d preview_mesh <file>  Preview mesh without loading
glass3d debug             Debug element tree

ssle                      Create new SSLE operation
pointcloud_to_ssle        Create SSLE from selected point cloud
```

## How SSLE Works

### Refractive Index Correction

When focusing inside a transparent material, the focal point shifts due to refraction. The plugin automatically corrects for this:

```
corrected_depth = target_depth × refractive_index
```

For example, to engrave at 10mm depth in K9 crystal (n=1.50), the Z-axis moves to 15mm.

### Layer Processing

Points are processed bottom-up to avoid the laser passing through already-engraved areas:

1. Group points by Z-coordinate
2. Sort layers from deepest to shallowest
3. For each layer:
   - Move Z to corrected depth
   - Engrave all points in layer
   - Insert thermal pauses as needed

### Thermal Management

Continuous engraving can overheat the material, causing cracks. The plugin automatically pauses:

- After every N points (configurable, default 10,000)
- Pause duration is configurable (default 500ms)

## File Structure

```
meerk40t-glass3d/
├── setup.cfg                    # Package configuration
├── meerk40t_glass3d/
│   ├── plugin.py               # Main plugin entry point
│   ├── ssle/
│   │   ├── element.py          # PointCloud3DNode element
│   │   ├── operation.py        # SSLEOperationNode operation
│   │   └── cutobjects.py       # SSLECut driver commands
│   ├── mesh/
│   │   ├── loader.py           # STL/OBJ/PLY/3MF loading
│   │   └── pointcloud.py       # Point generation strategies
│   └── gui/
│       ├── gui.py              # Menu registration
│       ├── ssle_panel.py       # SSLE operation settings panel
│       └── pointcloud_panel.py # PointCloud properties panel
```

## Troubleshooting

### Point cloud not visible
- Ensure the model is within the galvo's work area
- Check `glass3d info` for model bounds
- Try repositioning by dragging in the scene

### Z-axis not moving
- Enable Z-axis in MeerK40t device settings
- Verify Z-axis hardware connection
- Check Z min/max bounds in device configuration

### Engraving too shallow/deep
- Verify refractive index matches your material
- Check that Z-axis steps/mm is correctly calibrated
- Ensure glass surface is at Z=0

## License

MIT

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.
