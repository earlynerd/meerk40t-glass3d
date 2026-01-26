"""
Point Cloud Generation for SSLE

Generates point clouds from 3D meshes using various strategies.
"""

import numpy as np


def generate_points(mesh, strategy="surface", spacing=0.1, **kwargs):
    """
    Generate a point cloud from a mesh.

    Args:
        mesh: trimesh.Trimesh object
        strategy: Generation strategy - "surface", "solid", "contour", "layers"
        spacing: Point spacing in mm

    Returns:
        Nx3 numpy array of XYZ coordinates in mm
    """
    strategies = {
        "surface": generate_surface_points,
        "solid": generate_solid_points,
        "contour": generate_contour_points,
        "layers": generate_layer_points,
    }

    if strategy not in strategies:
        raise ValueError(f"Unknown strategy: {strategy}. Use: {list(strategies.keys())}")

    return strategies[strategy](mesh, spacing, **kwargs)


def generate_surface_points(mesh, spacing, **kwargs):
    """
    Generate points on the mesh surface.

    Samples points uniformly on the surface of the mesh.
    """
    # Calculate number of points based on surface area and spacing
    area = mesh.area
    num_points = int(area / (spacing**2))
    num_points = max(100, min(num_points, 1000000))  # Clamp between 100 and 1M

    # Sample points on surface
    points, _ = mesh.sample(num_points, return_index=True)

    return np.array(points)


def generate_solid_points(mesh, spacing, **kwargs):
    """
    Generate points filling the interior of the mesh.

    Creates a 3D grid of points and keeps only those inside the mesh.
    """
    bounds = mesh.bounds
    min_pt, max_pt = bounds

    # Create a 3D grid
    x = np.arange(min_pt[0], max_pt[0], spacing)
    y = np.arange(min_pt[1], max_pt[1], spacing)
    z = np.arange(min_pt[2], max_pt[2], spacing)

    # Generate all grid points
    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
    grid_points = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])

    # Filter to only points inside the mesh
    inside = mesh.contains(grid_points)
    interior_points = grid_points[inside]

    return interior_points


def generate_contour_points(mesh, spacing, layer_spacing=None, **kwargs):
    """
    Generate points along contour slices of the mesh.

    Creates horizontal slices and samples points along the contour edges.
    """
    if layer_spacing is None:
        layer_spacing = spacing

    bounds = mesh.bounds
    min_z, max_z = bounds[0][2], bounds[1][2]

    all_points = []

    # Slice at regular Z intervals
    z_levels = np.arange(min_z + layer_spacing / 2, max_z, layer_spacing)

    for z in z_levels:
        try:
            # Get cross-section at this Z level
            slice_2d = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])

            if slice_2d is None:
                continue

            # Get the path in 2D
            path_2d, transform = slice_2d.to_planar()

            # Sample points along the path
            for entity in path_2d.entities:
                # Get vertices for this entity
                vertices = path_2d.vertices[entity.points]

                # Sample along each edge
                for i in range(len(vertices) - 1):
                    start = vertices[i]
                    end = vertices[(i + 1) % len(vertices)]

                    # Calculate distance and number of points
                    dist = np.linalg.norm(end - start)
                    num_pts = max(1, int(dist / spacing))

                    # Interpolate points
                    for t in np.linspace(0, 1, num_pts, endpoint=False):
                        pt_2d = start + t * (end - start)
                        all_points.append([pt_2d[0], pt_2d[1], z])

        except Exception:
            # Skip slices that fail
            continue

    if len(all_points) == 0:
        # Fallback to surface sampling if contouring fails
        return generate_surface_points(mesh, spacing, **kwargs)

    return np.array(all_points)


def generate_layer_points(mesh, spacing, layer_spacing=None, **kwargs):
    """
    Generate points in horizontal layers filling each slice.

    Creates horizontal slices and fills each with a grid of points.
    """
    if layer_spacing is None:
        layer_spacing = spacing

    bounds = mesh.bounds
    min_z, max_z = bounds[0][2], bounds[1][2]

    all_points = []

    # Slice at regular Z intervals
    z_levels = np.arange(min_z + layer_spacing / 2, max_z, layer_spacing)

    for z in z_levels:
        try:
            # Get cross-section at this Z level
            slice_2d = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])

            if slice_2d is None:
                continue

            # Get the path in 2D
            path_2d, transform = slice_2d.to_planar()

            # Get bounding box of the slice
            if len(path_2d.vertices) == 0:
                continue

            min_xy = path_2d.vertices.min(axis=0)
            max_xy = path_2d.vertices.max(axis=0)

            # Create grid points in the slice
            x_pts = np.arange(min_xy[0], max_xy[0], spacing)
            y_pts = np.arange(min_xy[1], max_xy[1], spacing)

            for x in x_pts:
                for y in y_pts:
                    # Check if point is inside the slice polygon
                    if path_2d.contains_points([[x, y]])[0]:
                        all_points.append([x, y, z])

        except Exception:
            # Skip slices that fail
            continue

    if len(all_points) == 0:
        # Fallback to solid fill if layer approach fails
        return generate_solid_points(mesh, spacing, **kwargs)

    return np.array(all_points)


def optimize_path(points, method="nearest_neighbor"):
    """
    Optimize the point order for minimal travel time.

    Args:
        points: Nx3 array of XYZ coordinates
        method: Optimization method - "nearest_neighbor", "layer_snake", "none"

    Returns:
        Reordered Nx3 array
    """
    if method == "none" or len(points) < 2:
        return points

    if method == "layer_snake":
        return optimize_layer_snake(points)
    else:
        return optimize_nearest_neighbor(points)


def optimize_nearest_neighbor(points):
    """
    Simple nearest-neighbor path optimization within each Z layer.
    """
    if len(points) < 2:
        return points

    # Group by Z
    unique_z = np.unique(points[:, 2])
    optimized = []

    for z in sorted(unique_z):
        layer_mask = points[:, 2] == z
        layer_points = points[layer_mask].copy()

        if len(layer_points) < 2:
            optimized.extend(layer_points.tolist())
            continue

        # Nearest neighbor within layer
        remaining = set(range(len(layer_points)))
        current = 0
        remaining.remove(current)
        order = [current]

        while remaining:
            current_pt = layer_points[current, :2]
            best_dist = float("inf")
            best_idx = None

            for idx in remaining:
                dist = np.linalg.norm(layer_points[idx, :2] - current_pt)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            current = best_idx
            remaining.remove(current)
            order.append(current)

        optimized.extend(layer_points[order].tolist())

    return np.array(optimized)


def optimize_layer_snake(points):
    """
    Snake/zigzag path within each layer for efficient scanning.
    """
    if len(points) < 2:
        return points

    # Group by Z
    unique_z = np.unique(points[:, 2])
    optimized = []

    for layer_idx, z in enumerate(sorted(unique_z)):
        layer_mask = points[:, 2] == z
        layer_points = points[layer_mask].copy()

        if len(layer_points) < 2:
            optimized.extend(layer_points.tolist())
            continue

        # Sort by Y, then alternate X direction for snake pattern
        unique_y = np.unique(layer_points[:, 1])

        for y_idx, y in enumerate(sorted(unique_y)):
            y_mask = layer_points[:, 1] == y
            row_points = layer_points[y_mask].copy()

            # Sort by X, reverse every other row
            x_order = np.argsort(row_points[:, 0])
            if y_idx % 2 == 1:
                x_order = x_order[::-1]

            optimized.extend(row_points[x_order].tolist())

    return np.array(optimized)
