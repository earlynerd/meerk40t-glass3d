# MeerK40t Glass3D Plugin

Subsurface Laser Engraving (SSLE) plugin for [MeerK40t](https://github.com/meerk40t/meerk40t).

## Features

- Load 3D models (STL, OBJ, PLY, 3MF)
- Generate point clouds using multiple strategies
- Layer-by-layer Z-axis control for galvo lasers
- Glass refractive index correction
- Thermal management with automatic pauses
- Resume interrupted jobs with checkpointing

## Requirements

- MeerK40t 0.9.0 or later
- Galvo laser with Z-axis (e.g., BJJCZ/EZCAD2 compatible)
- Python 3.9+

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

## Usage

1. Enable Z-axis in your Balor device settings
2. Load a 3D model: `glass3d load model.stl`
3. Create an SSLE operation
4. Add the point cloud to the operation
5. Run the job

## Commands

```
glass3d help              - Show help
glass3d load <file>       - Load 3D model
glass3d info              - Show model info
glass3d preview           - Preview point cloud
```

## License

MIT
