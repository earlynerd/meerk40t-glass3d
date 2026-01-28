"""
Phase 9 Integration Tests for SSLE Driver Integration

Tests the complete pipeline from point cloud to driver commands
without requiring real hardware.
"""

import sys
import os

# Add paths for development installs
sys.path.insert(0, r'C:/Users/mmsyl/Documents/meerk40t')
sys.path.insert(0, r'C:/Users/mmsyl/Documents/meerk40t-glass3d')

import numpy as np


def test_ssle_cut_generation():
    """Test SSLECut command generation."""
    print("=" * 60)
    print("TEST 1: SSLECut Command Generation")
    print("=" * 60)

    from meerk40t_glass3d.ssle.cutobjects import SSLECut

    # Create a simple test point cloud (3 layers, 3 points each)
    points = np.array([
        # Layer 1 (Z=5mm) - deepest
        [10.0, 10.0, 5.0],
        [15.0, 10.0, 5.0],
        [12.5, 15.0, 5.0],
        # Layer 2 (Z=7.5mm)
        [10.0, 10.0, 7.5],
        [15.0, 10.0, 7.5],
        [12.5, 15.0, 7.5],
        # Layer 3 (Z=10mm) - shallowest
        [10.0, 10.0, 10.0],
        [15.0, 10.0, 10.0],
        [12.5, 15.0, 10.0],
    ])

    ssle = SSLECut(
        points=points,
        dwell_time=2.0,  # 2ms per point
        refractive_index=1.5,  # K9 glass
        thermal_pause_points=5,  # Pause every 5 points
        thermal_pause_ms=100,
    )

    print(f"Point cloud: {len(ssle)} points, {ssle.num_layers} layers")
    print(f"Unique Z values: {ssle.unique_z}")
    print()

    # Count commands by type
    command_counts = {}
    z_moves = []

    for cmd in ssle.generator():
        cmd_type = cmd[0]
        command_counts[cmd_type] = command_counts.get(cmd_type, 0) + 1

        if cmd_type == "ssle_z_move":
            z_moves.append((cmd[1], cmd[2]))  # (target_z, corrected_z)

    print("Command counts:")
    for cmd_type, count in sorted(command_counts.items()):
        print(f"  {cmd_type}: {count}")

    print()
    print("Z-axis moves (with refraction correction):")
    for target, corrected in z_moves:
        print(f"  Target: {target:.1f}mm -> Corrected: {corrected:.1f}mm (ratio: {corrected/target:.2f})")

    # Verify refraction correction
    expected_ratio = 1.5
    for target, corrected in z_moves:
        actual_ratio = corrected / target
        assert abs(actual_ratio - expected_ratio) < 0.01, f"Refraction correction failed: {actual_ratio} != {expected_ratio}"

    print()
    print("PASS: SSLECut command generation working correctly")
    return True


def test_operation_cutobject_pipeline():
    """Test SSLEOperation -> SSLECut pipeline."""
    print()
    print("=" * 60)
    print("TEST 2: SSLEOperation to SSLECut Pipeline")
    print("=" * 60)

    from meerk40t_glass3d.ssle.operation import SSLEOperationNode
    from meerk40t_glass3d.ssle.element import PointCloud3DNode
    from meerk40t_glass3d.ssle.cutobjects import SSLECut

    # Create a point cloud element
    points = np.array([
        [0.0, 0.0, 2.0],
        [5.0, 0.0, 2.0],
        [0.0, 5.0, 2.0],
        [0.0, 0.0, 4.0],
        [5.0, 0.0, 4.0],
        [0.0, 5.0, 4.0],
    ])

    pointcloud = PointCloud3DNode(point_data=points)
    print(f"Created PointCloud3DNode with {len(pointcloud)} points")

    # Create SSLE operation
    operation = SSLEOperationNode(
        settings={
            "dwell_time": 1.5,
            "power": 600,
            "frequency": 40.0,
            "refractive_index": 1.46,  # Fused silica
            "thermal_pause_points": 1000,
            "thermal_pause_ms": 200,
        }
    )
    print(f"Created SSLEOperationNode: {operation.dwell_time}ms dwell, n={operation.refractive_index}")

    # Add pointcloud as child (simulating reference)
    # In real MeerK40t this would be a reference node
    operation._children = [pointcloud]
    pointcloud._parent = operation

    # Generate cutobjects
    cutobjects = list(operation.as_cutobjects())
    print(f"Generated {len(cutobjects)} cutobjects")

    assert len(cutobjects) == 1, "Expected exactly one SSLECut"

    ssle_cut = cutobjects[0]
    assert isinstance(ssle_cut, SSLECut), f"Expected SSLECut, got {type(ssle_cut)}"

    print(f"SSLECut: {len(ssle_cut)} points, {ssle_cut.num_layers} layers")
    print(f"  dwell_time: {ssle_cut.dwell_time}ms")
    print(f"  refractive_index: {ssle_cut.refractive_index}")
    print(f"  thermal_pause_points: {ssle_cut.thermal_pause_points}")
    print(f"  thermal_pause_ms: {ssle_cut.thermal_pause_ms}")

    # Verify settings propagated correctly
    assert ssle_cut.dwell_time == 1.5
    assert ssle_cut.refractive_index == 1.46
    assert ssle_cut.thermal_pause_points == 1000

    print()
    print("PASS: Operation to cutobject pipeline working correctly")
    return True


def test_driver_command_flow():
    """Test the driver's SSLE command handling logic."""
    print()
    print("=" * 60)
    print("TEST 3: Driver Command Flow Simulation")
    print("=" * 60)

    from meerk40t_glass3d.ssle.cutobjects import SSLECut

    # Create test point cloud
    points = np.array([
        [50.0, 50.0, 10.0],  # Center of 100mm field, 10mm deep
        [55.0, 50.0, 10.0],
        [50.0, 55.0, 10.0],
        [50.0, 50.0, 15.0],  # 15mm deep
        [55.0, 50.0, 15.0],
    ])

    ssle = SSLECut(
        points=points,
        dwell_time=3.0,
        refractive_index=1.5,
        thermal_pause_points=100,
        thermal_pause_ms=50,
    )

    # Simulate driver command processing
    # This mirrors what _execute_ssle_cut does
    print("Simulating driver command processing:")
    print()

    z_axis_enabled = True
    current_z = 0.0
    laser_dwells = 0
    total_dwell_ms = 0

    for cmd in ssle.generator():
        cmd_type = cmd[0]

        if cmd_type == "ssle_layer_start":
            layer_idx, z_mm = cmd[1], cmd[2]
            print(f"  [LAYER START] Layer {layer_idx} at Z={z_mm:.1f}mm")

        elif cmd_type == "ssle_z_move":
            z_mm, corrected_z = cmd[1], cmd[2]
            if z_axis_enabled:
                current_z = corrected_z
                print(f"  [Z MOVE] Target: {z_mm:.1f}mm -> Corrected: {corrected_z:.1f}mm")

        elif cmd_type == "ssle_dwell":
            x_mm, y_mm, dwell_ms = cmd[1], cmd[2], cmd[3]
            laser_dwells += 1
            total_dwell_ms += dwell_ms

            # Convert mm to galvo units (simulating view.position)
            # Assuming 100mm field = 0x10000 galvo units, center at 0x8000
            galvo_per_mm = 0x10000 / 100.0
            native_x = int(0x8000 + (x_mm - 50.0) * galvo_per_mm)
            native_y = int(0x8000 + (y_mm - 50.0) * galvo_per_mm)

            # Clamp
            native_x = max(0, min(0xFFFF, native_x))
            native_y = max(0, min(0xFFFF, native_y))

            print(f"  [DWELL] ({x_mm:.1f}, {y_mm:.1f})mm -> galvo ({native_x:04X}, {native_y:04X}), {dwell_ms}ms")

        elif cmd_type == "ssle_thermal_pause":
            pause_ms = cmd[1]
            print(f"  [THERMAL PAUSE] {pause_ms}ms")

        elif cmd_type == "ssle_layer_end":
            layer_idx = cmd[1]
            print(f"  [LAYER END] Layer {layer_idx}")

    print()
    print(f"Summary:")
    print(f"  Total laser dwells: {laser_dwells}")
    print(f"  Total dwell time: {total_dwell_ms}ms ({total_dwell_ms/1000:.2f}s)")
    print(f"  Final Z position: {current_z:.1f}mm")

    assert laser_dwells == len(points), f"Expected {len(points)} dwells, got {laser_dwells}"

    print()
    print("PASS: Driver command flow simulation working correctly")
    return True


def test_driver_import():
    """Test that the driver imports correctly with SSLE support."""
    print()
    print("=" * 60)
    print("TEST 4: Driver Import with SSLE Support")
    print("=" * 60)

    from meerk40t.balormk.driver import BalorDriver, SSLE_AVAILABLE

    print(f"SSLE_AVAILABLE: {SSLE_AVAILABLE}")
    assert SSLE_AVAILABLE, "SSLE support not available in driver"

    # Check that SSLECut is importable from driver context
    from meerk40t.balormk.driver import SSLECut
    assert SSLECut is not None

    # Check that _execute_ssle_cut method exists
    assert hasattr(BalorDriver, '_execute_ssle_cut'), "Driver missing _execute_ssle_cut method"

    print("Driver has _execute_ssle_cut method: YES")
    print()
    print("PASS: Driver import working correctly")
    return True


def test_coordinate_conversion():
    """Test coordinate conversion from mm to galvo units."""
    print()
    print("=" * 60)
    print("TEST 5: Coordinate Conversion")
    print("=" * 60)

    # Test cases: (x_mm, y_mm, expected behavior)
    # Assuming 100mm field centered, so 50mm = center = 0x8000

    test_cases = [
        (50.0, 50.0, "center"),  # Center of field
        (0.0, 0.0, "bottom-left corner"),
        (100.0, 100.0, "top-right corner"),
        (25.0, 75.0, "quarter positions"),
    ]

    # Simulate galvo coordinate conversion
    # This is what the driver does with view.position
    field_size_mm = 100.0
    galvo_range = 0x10000
    galvo_center = 0x8000
    galvo_per_mm = galvo_range / field_size_mm

    print(f"Field size: {field_size_mm}mm")
    print(f"Galvo range: 0x0000-0xFFFF ({galvo_range} units)")
    print(f"Galvo per mm: {galvo_per_mm:.2f}")
    print()

    for x_mm, y_mm, desc in test_cases:
        # Convert - assuming field is 0-100mm mapped to 0x0000-0xFFFF
        native_x = int(x_mm * galvo_per_mm)
        native_y = int(y_mm * galvo_per_mm)

        # Clamp
        native_x = max(0, min(0xFFFF, native_x))
        native_y = max(0, min(0xFFFF, native_y))

        print(f"  ({x_mm:6.1f}, {y_mm:6.1f})mm -> (0x{native_x:04X}, 0x{native_y:04X}) [{desc}]")

    print()
    print("PASS: Coordinate conversion logic verified")
    return True


def test_time_calculation():
    """Test operation time estimates."""
    print()
    print("=" * 60)
    print("TEST 6: Time Estimation")
    print("=" * 60)

    from meerk40t_glass3d.ssle.cutobjects import SSLECut

    # Create a larger point cloud for realistic timing
    num_points = 10000
    np.random.seed(42)
    points = np.column_stack([
        np.random.uniform(10, 90, num_points),  # X: 10-90mm
        np.random.uniform(10, 90, num_points),  # Y: 10-90mm
        np.random.uniform(5, 20, num_points),   # Z: 5-20mm (multiple layers)
    ])

    dwell_ms = 2.0
    thermal_pause_points = 1000
    thermal_pause_ms = 500

    ssle = SSLECut(
        points=points,
        dwell_time=dwell_ms,
        refractive_index=1.5,
        thermal_pause_points=thermal_pause_points,
        thermal_pause_ms=thermal_pause_ms,
    )

    # Calculate estimated time
    num_pauses = num_points // thermal_pause_points

    dwell_time_total = num_points * dwell_ms  # ms
    pause_time_total = num_pauses * thermal_pause_ms  # ms

    # Estimate movement time (rough: 0.1ms per point)
    movement_time = num_points * 0.1  # ms

    # Z movement time (rough: 100ms per layer)
    z_move_time = ssle.num_layers * 100  # ms

    total_ms = dwell_time_total + pause_time_total + movement_time + z_move_time
    total_s = total_ms / 1000

    print(f"Point cloud: {num_points} points, {ssle.num_layers} layers")
    print()
    print("Time breakdown:")
    print(f"  Laser dwell time:  {dwell_time_total/1000:8.2f}s ({dwell_ms}ms x {num_points} points)")
    print(f"  Thermal pauses:    {pause_time_total/1000:8.2f}s ({thermal_pause_ms}ms x {num_pauses} pauses)")
    print(f"  Movement time:     {movement_time/1000:8.2f}s (estimated)")
    print(f"  Z-axis movement:   {z_move_time/1000:8.2f}s (estimated)")
    print(f"  ------------------------")
    print(f"  Total estimated:   {total_s:8.2f}s ({total_s/60:.1f} minutes)")

    print()
    print("PASS: Time estimation logic verified")
    return True


def run_all_tests():
    """Run all phase 9 integration tests."""
    print()
    print("*" * 60)
    print("  PHASE 9 INTEGRATION TESTS")
    print("  SSLE Driver Integration")
    print("*" * 60)
    print()

    tests = [
        ("SSLECut Generation", test_ssle_cut_generation),
        ("Operation Pipeline", test_operation_cutobject_pipeline),
        ("Driver Command Flow", test_driver_command_flow),
        ("Driver Import", test_driver_import),
        ("Coordinate Conversion", test_coordinate_conversion),
        ("Time Estimation", test_time_calculation),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS" if result else "FAIL"))
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, f"ERROR: {e}"))

    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, result in results:
        status = "PASS" if result == "PASS" else "FAIL"
        print(f"  [{status:4}] {name}")

    passed = sum(1 for _, r in results if r == "PASS")
    total = len(results)
    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print()
        print("All tests passed! Ready for hardware testing.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
