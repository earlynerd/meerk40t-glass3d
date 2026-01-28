"""
Z-Axis Command Sequence Verification

Tests that the correct hardware commands are generated for Z-axis movement
during SSLE operations.
"""

import sys
sys.path.insert(0, r'C:/Users/mmsyl/Documents/meerk40t')
sys.path.insert(0, r'C:/Users/mmsyl/Documents/meerk40t-glass3d')

import numpy as np


class ZAxisCommandCapture:
    """Captures Z-axis hardware commands for verification."""
    def __init__(self):
        self.commands = []
        self.axis_motion_params = []
        self.axis_origin_params = []
        self.axis_moves = []

    def set_axis_motion_param(self, speed_min, speed_max):
        self.commands.append(("SetAxisMotionParam", speed_min, speed_max))
        self.axis_motion_params.append((speed_min, speed_max))
        print(f"  SetAxisMotionParam(min={speed_min}, max={speed_max})")

    def set_axis_origin_param(self, acc_time):
        self.commands.append(("SetAxisOriginParam", acc_time))
        self.axis_origin_params.append(acc_time)
        print(f"  SetAxisOriginParam(acc_time={acc_time})")

    def move_axis_to(self, p0, p1):
        # Reconstruct position from split words
        pos = (p1 << 16) | p0
        if pos >= 0x80000000:
            pos = -(pos - 0x80000000)
        self.commands.append(("MoveAxisTo", p0, p1, pos))
        self.axis_moves.append(pos)
        print(f"  MoveAxisTo(p0=0x{p0:04X}, p1=0x{p1:04X}) -> {pos} steps")

    def get_list_status(self):
        # Return status with AXIS bit cleared (movement complete)
        return (0, 0, 0, 0)  # No AXIS bit set = idle


class MockConnectionForZTest:
    """Mock connection that captures commands."""
    def __init__(self, capture):
        self.capture = capture
        self.is_open_flag = True
        self._last_x = 0x8000
        self._last_y = 0x8000

    def is_open(self, index=0):
        return self.is_open_flag

    def set_axis_motion_param(self, *args):
        return self.capture.set_axis_motion_param(*args)

    def set_axis_origin_param(self, *args):
        return self.capture.set_axis_origin_param(*args)

    def move_axis_to(self, *args):
        return self.capture.move_axis_to(*args)

    def get_list_status(self):
        return self.capture.get_list_status()

    # Mock other required methods
    def goto(self, x, y, **kwargs):
        self._last_x = x
        self._last_y = y

    def get_last_xy(self):
        return self._last_x, self._last_y

    def list_laser_on_point(self, dwell):
        pass

    def list_delay_time(self, delay):
        pass


class MockChannel:
    """Mock channel for capturing log messages."""
    def __init__(self, name="test"):
        self.name = name
        self.messages = []
        self._ = lambda x: x

    def __call__(self, message):
        self.messages.append(message)
        # Optionally print: print(f"  [CHANNEL] {message}")

    def watch(self, handler):
        pass


class MockServiceForZTest:
    """Mock service with Z-axis settings."""
    def __init__(self):
        self.safe_label = "test"
        self.z_axis_enabled = True
        self.z_min_mm = 0.0
        self.z_max_mm = 50.0
        self.z_steps_per_mm = 1000.0  # 1000 steps per mm
        self.z_speed_min = 100
        self.z_speed_max = 2000
        self.z_acc_time = 150
        self.delay_end = 1000
        self.signal_updates = False
        self._channels = {}

        # Pin settings
        self.light_pin = 8
        self.footpedal_pin = 15

        # Mock view
        self.view = type('MockView', (), {
            'position': lambda self, x, y, **kw: (0x8000, 0x8000),
            'iposition': lambda self, x, y: (50.0, 50.0)
        })()

    def channel(self, name, **kwargs):
        if name not in self._channels:
            self._channels[name] = MockChannel(name)
        return self._channels[name]

    def setting(self, type_, name, default=None):
        """Get a service setting."""
        return getattr(self, name, default)

    def signal(self, *args, **kwargs):
        pass

    def add_service_delegate(self, delegate):
        pass


def test_z_axis_command_sequence():
    """Test the Z-axis command sequence for SSLE layers."""
    print("=" * 60)
    print("Z-AXIS COMMAND SEQUENCE TEST")
    print("=" * 60)

    from meerk40t_glass3d.ssle.cutobjects import SSLECut
    from meerk40t.balormk.driver import BalorDriver

    # Create point cloud with 3 layers
    points = np.array([
        [50.0, 50.0, 5.0],   # 5mm deep
        [50.0, 50.0, 10.0],  # 10mm deep
        [50.0, 50.0, 15.0],  # 15mm deep
    ])

    ssle_cut = SSLECut(
        points=points,
        dwell_time=1.0,
        refractive_index=1.5,  # K9 glass
        thermal_pause_points=1000,
        thermal_pause_ms=50,
    )

    print(f"\nTest SSLECut: 3 points, 3 layers")
    print(f"Refractive index: 1.5")
    print(f"Expected corrected Z positions:")
    print(f"  5mm target -> 7.5mm corrected -> 7500 steps")
    print(f"  10mm target -> 15.0mm corrected -> 15000 steps")
    print(f"  15mm target -> 22.5mm corrected -> 22500 steps")
    print()

    # Create mock environment
    service = MockServiceForZTest()
    capture = ZAxisCommandCapture()
    mock_connection = MockConnectionForZTest(capture)

    # Create driver with mock connection
    driver = BalorDriver(service, force_mock=True)
    driver.connection = mock_connection
    driver.paused = False
    driver._aborting = False
    driver._z_position_mm = 0.0

    print("Executing SSLE cut...")
    print("-" * 40)

    driver._execute_ssle_cut(ssle_cut, mock_connection)

    print("-" * 40)

    # Verify Z moves
    print("\nZ-Axis Move Verification:")
    expected_steps = [7500, 15000, 22500]  # Corrected positions * steps_per_mm

    for i, (actual, expected) in enumerate(zip(capture.axis_moves, expected_steps)):
        status = "OK" if actual == expected else "FAIL"
        print(f"  Layer {i}: {actual} steps (expected {expected}) - {status}")
        assert actual == expected, f"Layer {i}: Expected {expected} steps, got {actual}"

    # Verify motion parameters were set correctly
    print("\nMotion Parameter Verification:")
    for speed_min, speed_max in capture.axis_motion_params[:1]:  # Check first call
        assert speed_min == service.z_speed_min, f"Speed min mismatch"
        assert speed_max == service.z_speed_max, f"Speed max mismatch"
        print(f"  Speed range: {speed_min} - {speed_max} - OK")

    for acc_time in capture.axis_origin_params[:1]:
        assert acc_time == service.z_acc_time, f"Acc time mismatch"
        print(f"  Acceleration time: {acc_time} - OK")

    print()
    print("=" * 60)
    print("Z-AXIS COMMAND SEQUENCE TEST PASSED")
    print("=" * 60)

    return True


def test_z_axis_bounds_clamping():
    """Test that Z positions are clamped to valid bounds."""
    print("\n" + "=" * 60)
    print("Z-AXIS BOUNDS CLAMPING TEST")
    print("=" * 60)

    from meerk40t_glass3d.ssle.cutobjects import SSLECut
    from meerk40t.balormk.driver import BalorDriver

    # Create point cloud with extreme Z values
    points = np.array([
        [50.0, 50.0, 1.0],    # 1mm -> 1.5mm corrected (within bounds)
        [50.0, 50.0, 50.0],   # 50mm -> 75mm corrected (EXCEEDS 50mm max!)
    ])

    ssle_cut = SSLECut(
        points=points,
        dwell_time=1.0,
        refractive_index=1.5,
        thermal_pause_points=1000,
        thermal_pause_ms=50,
    )

    print(f"\nTest with Z=50mm target (would need 75mm with refraction)")
    print(f"Z max setting: 50mm")
    print()

    # Create mock environment
    service = MockServiceForZTest()
    service.z_max_mm = 50.0  # Max Z is 50mm
    capture = ZAxisCommandCapture()
    mock_connection = MockConnectionForZTest(capture)

    driver = BalorDriver(service, force_mock=True)
    driver.connection = mock_connection
    driver.paused = False
    driver._aborting = False
    driver._z_position_mm = 0.0

    print("Executing SSLE cut...")
    print("-" * 40)

    driver._execute_ssle_cut(ssle_cut, mock_connection)

    print("-" * 40)

    # Check that Z was clamped
    print("\nBounds Clamping Verification:")

    # First move: 1mm -> 1.5mm corrected -> 1500 steps
    assert capture.axis_moves[0] == 1500, f"First move should be 1500, got {capture.axis_moves[0]}"
    print(f"  Layer 0: 1500 steps (1.5mm) - OK")

    # Second move: 50mm -> 75mm corrected, but clamped to 50mm -> 50000 steps
    assert capture.axis_moves[1] == 50000, f"Second move should be clamped to 50000, got {capture.axis_moves[1]}"
    print(f"  Layer 1: 50000 steps (50mm, clamped from 75mm) - OK")

    print()
    print("=" * 60)
    print("Z-AXIS BOUNDS CLAMPING TEST PASSED")
    print("=" * 60)

    return True


def test_negative_position_encoding():
    """Test that negative Z positions are encoded correctly."""
    print("\n" + "=" * 60)
    print("NEGATIVE POSITION ENCODING TEST")
    print("=" * 60)

    # Test the encoding formula
    steps_per_mm = 1000.0

    test_cases = [
        (10.0, 10000),     # Positive
        (0.0, 0),          # Zero
        (-5.0, 0x80001388),  # Negative: (-5000) | 0x80000000
    ]

    print("\nPosition encoding test:")
    for position_mm, expected_encoded in test_cases:
        steps = int(position_mm * steps_per_mm)

        if steps < 0:
            encoded = (-steps) | 0x80000000
        else:
            encoded = steps

        p1 = (encoded >> 16) & 0xFFFF
        p0 = encoded & 0xFFFF

        # Decode back
        decoded = (p1 << 16) | p0
        if decoded >= 0x80000000:
            decoded_mm = -(decoded - 0x80000000) / steps_per_mm
        else:
            decoded_mm = decoded / steps_per_mm

        status = "OK" if abs(decoded_mm - position_mm) < 0.001 else "FAIL"
        print(f"  {position_mm:6.1f}mm -> encoded: 0x{encoded:08X} (p0=0x{p0:04X}, p1=0x{p1:04X}) -> decoded: {decoded_mm:.1f}mm - {status}")

        assert abs(decoded_mm - position_mm) < 0.001, f"Round-trip failed for {position_mm}mm"

    print()
    print("=" * 60)
    print("NEGATIVE POSITION ENCODING TEST PASSED")
    print("=" * 60)

    return True


def run_all_tests():
    """Run all Z-axis command tests."""
    print()
    print("*" * 60)
    print("  Z-AXIS COMMAND VERIFICATION TESTS")
    print("*" * 60)

    tests = [
        ("Z-Axis Command Sequence", test_z_axis_command_sequence),
        ("Z-Axis Bounds Clamping", test_z_axis_bounds_clamping),
        ("Negative Position Encoding", test_negative_position_encoding),
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
