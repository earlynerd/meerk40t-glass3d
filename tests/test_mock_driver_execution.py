"""
Mock Driver Execution Test for SSLE

This test creates a minimal mock environment to test the actual
driver execution path with SSLECut objects.
"""

import sys
sys.path.insert(0, r'C:/Users/mmsyl/Documents/meerk40t')
sys.path.insert(0, r'C:/Users/mmsyl/Documents/meerk40t-glass3d')

import numpy as np
from io import StringIO


class MockChannel:
    """Mock channel for capturing log messages."""
    def __init__(self, name="test"):
        self.name = name
        self.messages = []
        self._ = lambda x: x  # Translation function

    def __call__(self, message):
        self.messages.append(message)
        print(f"  [CHANNEL] {message}")

    def watch(self, handler):
        pass


class MockView:
    """Mock view for coordinate conversion."""
    def __init__(self, field_size_mm=100.0):
        self.field_size_mm = field_size_mm
        self.galvo_range = 0x10000
        self.galvo_per_mm = self.galvo_range / field_size_mm

    def position(self, x, y, vector=False, margins=False):
        """Convert mm to galvo units."""
        # Parse string values like "50mm"
        if isinstance(x, str):
            if x.endswith("mm"):
                x = float(x[:-2])
            elif x.endswith("%"):
                x = float(x[:-1]) * self.field_size_mm / 100
            else:
                x = float(x)
        if isinstance(y, str):
            if y.endswith("mm"):
                y = float(y[:-2])
            elif y.endswith("%"):
                y = float(y[:-1]) * self.field_size_mm / 100
            else:
                y = float(y)

        native_x = x * self.galvo_per_mm
        native_y = y * self.galvo_per_mm
        return native_x, native_y

    def iposition(self, x, y):
        """Convert galvo units back to mm."""
        mm_x = x / self.galvo_per_mm
        mm_y = y / self.galvo_per_mm
        return mm_x, mm_y


class MockService:
    """Mock service object providing device settings."""
    def __init__(self):
        self.safe_label = "test_galvo"
        self.view = MockView()
        self._channels = {}

        # Z-axis settings
        self.z_axis_enabled = True
        self.z_min_mm = 0.0
        self.z_max_mm = 50.0
        self.z_steps_per_mm = 1000.0
        self.z_speed_min = 100
        self.z_speed_max = 1000
        self.z_acc_time = 100

        # Laser settings
        self.delay_end = 1000  # microseconds
        self.default_power = 500
        self.default_frequency = 30.0
        self.default_rapid_speed = 2000

        # Mock settings
        self.mock = True
        self.signal_updates = False

    def channel(self, name, **kwargs):
        if name not in self._channels:
            self._channels[name] = MockChannel(name)
        return self._channels[name]

    def signal(self, *args, **kwargs):
        pass

    def setting(self, type_, name, default=None):
        return getattr(self, name, default)

    def add_service_delegate(self, delegate):
        pass


class GalvoCommandCapture:
    """Captures galvo commands for verification."""
    def __init__(self):
        self.commands = []
        self.z_positions = []
        self.xy_positions = []
        self.dwells = []

    def record_command(self, cmd_type, *args):
        self.commands.append((cmd_type, args))

        if cmd_type == "z_move":
            self.z_positions.append(args[0])
        elif cmd_type == "goto":
            self.xy_positions.append((args[0], args[1]))
        elif cmd_type == "dwell":
            self.dwells.append(args[0])

    def summary(self):
        print(f"\nCapture Summary:")
        print(f"  Total commands: {len(self.commands)}")
        print(f"  Z moves: {len(self.z_positions)}")
        print(f"  XY moves: {len(self.xy_positions)}")
        print(f"  Laser dwells: {len(self.dwells)}")

        if self.z_positions:
            print(f"  Z range: {min(self.z_positions):.2f} - {max(self.z_positions):.2f}mm")
        if self.dwells:
            print(f"  Total dwell time: {sum(self.dwells):.2f}ms")


def test_driver_ssle_execution():
    """Test the driver's _execute_ssle_cut method with mock connection."""
    print("=" * 60)
    print("MOCK DRIVER EXECUTION TEST")
    print("=" * 60)

    from meerk40t_glass3d.ssle.cutobjects import SSLECut

    # Create test point cloud
    points = np.array([
        # Layer 1 (Z=5mm)
        [50.0, 50.0, 5.0],
        [55.0, 50.0, 5.0],
        [50.0, 55.0, 5.0],
        # Layer 2 (Z=10mm)
        [50.0, 50.0, 10.0],
        [55.0, 55.0, 10.0],
    ])

    ssle_cut = SSLECut(
        points=points,
        dwell_time=2.0,
        refractive_index=1.5,
        thermal_pause_points=100,
        thermal_pause_ms=50,
    )

    print(f"\nTest SSLECut: {len(ssle_cut)} points, {ssle_cut.num_layers} layers")

    # Create mock service
    service = MockService()
    capture = GalvoCommandCapture()

    # Create mock controller that captures commands
    class MockController:
        def __init__(self, capture):
            self.capture = capture
            self._last_x = 0x8000
            self._last_y = 0x8000

        def goto(self, x, y, **kwargs):
            self.capture.record_command("goto", x, y)
            self._last_x = x
            self._last_y = y
            print(f"    -> GOTO ({x:04X}, {y:04X})")

        def get_last_xy(self):
            return self._last_x, self._last_y

        def list_laser_on_point(self, dwell_10us):
            dwell_ms = dwell_10us / 100.0
            self.capture.record_command("dwell", dwell_ms)
            print(f"    -> LASER ON {dwell_ms:.1f}ms")

        def list_delay_time(self, delay_10us):
            delay_ms = delay_10us / 100.0
            self.capture.record_command("delay", delay_ms)
            print(f"    -> DELAY {delay_ms:.1f}ms")

    # Import driver and create instance
    from meerk40t.balormk.driver import BalorDriver

    # Create driver with mock connection
    driver = BalorDriver(service, force_mock=True)
    driver.paused = False
    driver._aborting = False

    # Create mock Z-axis tracking
    driver._z_position_mm = 0.0

    # Override z_move_absolute to capture Z moves
    original_z_move = driver.z_move_absolute
    def mock_z_move(position_mm):
        capture.record_command("z_move", position_mm)
        print(f"    -> Z MOVE to {position_mm:.2f}mm")
        driver._z_position_mm = position_mm

    driver.z_move_absolute = mock_z_move

    # Create mock controller
    mock_con = MockController(capture)

    print("\nExecuting SSLE cut...")
    print("-" * 40)

    # Execute SSLE cut
    driver._execute_ssle_cut(ssle_cut, mock_con)

    print("-" * 40)

    # Print capture summary
    capture.summary()

    # Verify results
    print("\nVerification:")

    # Check Z moves
    expected_z_moves = 2  # One per layer
    assert len(capture.z_positions) == expected_z_moves, \
        f"Expected {expected_z_moves} Z moves, got {len(capture.z_positions)}"
    print(f"  Z moves: {len(capture.z_positions)} (expected {expected_z_moves}) - OK")

    # Check XY positions
    expected_xy = len(points)
    assert len(capture.xy_positions) == expected_xy, \
        f"Expected {expected_xy} XY moves, got {len(capture.xy_positions)}"
    print(f"  XY moves: {len(capture.xy_positions)} (expected {expected_xy}) - OK")

    # Check laser dwells
    assert len(capture.dwells) == expected_xy, \
        f"Expected {expected_xy} dwells, got {len(capture.dwells)}"
    print(f"  Laser dwells: {len(capture.dwells)} (expected {expected_xy}) - OK")

    # Check refraction correction on Z
    # Layer 1: 5mm target -> 7.5mm corrected (n=1.5)
    # Layer 2: 10mm target -> 15mm corrected
    expected_z = [7.5, 15.0]
    for i, (actual, expected) in enumerate(zip(capture.z_positions, expected_z)):
        assert abs(actual - expected) < 0.01, \
            f"Layer {i}: Expected Z={expected}, got {actual}"
    print(f"  Refraction correction: OK (Z values: {capture.z_positions})")

    print("\n" + "=" * 60)
    print("MOCK DRIVER EXECUTION TEST PASSED")
    print("=" * 60)

    return True


def test_abort_handling():
    """Test that abort is handled correctly during SSLE execution."""
    print("\n" + "=" * 60)
    print("ABORT HANDLING TEST")
    print("=" * 60)

    from meerk40t_glass3d.ssle.cutobjects import SSLECut
    from meerk40t.balormk.driver import BalorDriver

    # Create larger point cloud
    points = np.array([
        [50.0, 50.0, 5.0 + i * 0.1] for i in range(100)
    ])

    ssle_cut = SSLECut(
        points=points,
        dwell_time=1.0,
        refractive_index=1.5,
        thermal_pause_points=1000,
        thermal_pause_ms=10,
    )

    service = MockService()
    driver = BalorDriver(service, force_mock=True)

    # Track how many commands were executed
    command_count = [0]

    class AbortingController:
        def __init__(self):
            self._last_x = 0x8000
            self._last_y = 0x8000

        def goto(self, x, y, **kwargs):
            command_count[0] += 1
            self._last_x = x
            self._last_y = y

        def get_last_xy(self):
            return self._last_x, self._last_y

        def list_laser_on_point(self, dwell):
            command_count[0] += 1

        def list_delay_time(self, delay):
            command_count[0] += 1

    mock_con = AbortingController()

    # Set abort after 10 commands
    abort_after = 10
    original_abort_check = driver._abort_mission
    def abort_after_n():
        if command_count[0] >= abort_after:
            driver._aborting = True
            return True
        return original_abort_check()

    driver._abort_mission = abort_after_n
    driver._aborting = False
    driver.z_move_absolute = lambda x: None  # No-op for this test

    print(f"Executing with abort after {abort_after} commands...")

    driver._execute_ssle_cut(ssle_cut, mock_con)

    print(f"Commands executed before abort: {command_count[0]}")

    # Should have stopped early
    assert command_count[0] < len(points) * 2, "Abort did not stop execution"
    print("Abort handled correctly - execution stopped early")

    print("\n" + "=" * 60)
    print("ABORT HANDLING TEST PASSED")
    print("=" * 60)

    return True


def run_all_tests():
    """Run all mock driver tests."""
    print()
    print("*" * 60)
    print("  MOCK DRIVER EXECUTION TESTS")
    print("*" * 60)

    tests = [
        ("Driver SSLE Execution", test_driver_ssle_execution),
        ("Abort Handling", test_abort_handling),
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

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
