import unittest, os, sys, time, select
import subprocess, fcntl # Used by sim target
import serial # Used by nano target

ARMOCK_PATH = os.path.join(os.path.dirname(__file__), 'armock')

dummy = unittest.TestCase()

def ereadline():
    select.select([dut.stderr], [], [], 1)[0]
    return str(dut.stderr.readline(), 'utf-8')

def sreadline(count=1):
    result = []
    line = b''
    
    while len(result) < count:
        # Select waits for data with a timeout
        if line == b'' and  len(select.select([dut.stdout], [], [], 1)[0]) == 0: break
        
        line = dut.stdout.readline()
        # .readline() will return an empty string if it doesn't have data available
        if(line): result.append(line)
    
    return ''.join(str(line, 'utf-8') for line in result)

def srun(cmd, readlines=0):
    dut.stdin.write(bytes(cmd, 'utf-8'))
    dut.stdin.flush()
    return sreadline(count=readlines) if readlines else ''

def assert_srun(cmd, expected):
    dummy.assertEqual(srun(cmd, readlines=expected.count('\n')), expected)

def assert_error_msg(error_msg, fname):
    dummy.assertIn(fname, error_msg)
    dummy.assertIn('Check', error_msg)
    dummy.assertIn('failed', error_msg)

def expand_cmd(cmd):
    return {
        'ms': 'millis',
        'ps': 'println<string>',
        'pu': 'println<u32>',
        'pi': 'println<i32>',
        'pm': 'pinMode',
        'dr': 'digitalRead',
        'dw': 'digitalWrite',
        'ar': 'analogRead',
        'aw': 'analogWrite',
        'ee': 'EEPROM',
    }.get(cmd[:2])

def setUpModule():
    global target, shm_pins, shm_eeprom
    
    assert 'TARGET' in os.environ, '$TARGET envionment variable not set'
    target = os.environ['TARGET']
    assert target in ['armock', 'nano', 'nano-fixture'], 'Unknown $TARGET: {}'.format(target)
    
    if target == 'armock':
        shm_pins = open('/dev/shm/armock_pins', 'w+b', buffering=0)
        shm_pins.size = 16
        shm_eeprom = open('/dev/shm/armock_eeprom', 'w+b', buffering=0)
        shm_eeprom.size = 1024
    
    if target == 'nano' or target == 'nano-fixture':
        global dut, nano
        nano = serial.Serial(port='/dev/ttyUSB0', baudrate=115200, timeout=1)
        dut = lambda: None
        setattr(dut, 'stdin', nano)
        setattr(dut, 'stdout', nano)
        time.sleep(1) # Wait for nano to reset
        dut.stdout.readline() # Will time out

def tearDownModule():
    if target == 'armock':
        shm_pins.close()
        shm_eeprom.close()
    
    if target == 'nano' or target == 'nano-fixture':
        nano.close()

class Shared(unittest.TestCase):
    def setUp(self, clear_eeprom=True):
        if target == 'armock':
            global dut
            shm_pins.expected = bytearray(shm_pins.size)
            shm_eeprom.expected = bytearray(shm_eeprom.size)
            
            if clear_eeprom:
                shm_eeprom.seek(0)
                shm_eeprom.write(bytes(shm_eeprom.size))
            
            self.dut = subprocess.Popen([ARMOCK_PATH, 'armock_pins', 'armock_eeprom'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Device Under Test
            dut = self.dut
            fcntl.fcntl(dut.stdout, fcntl.F_SETFL, fcntl.fcntl(dut.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
            fcntl.fcntl(dut.stderr, fcntl.F_SETFL, fcntl.fcntl(dut.stderr, fcntl.F_GETFL) | os.O_NONBLOCK)
        
        # Wait until dut has finished starting up
        assert_srun('ps ready\n', 'ready\r\n7\r\n')
    
    def tearDown(self):
        response = srun('ps teardown\n', readlines=2)
        
        if target == 'armock':
            dummy.assertEqual(dut.stderr.readline(), b'')
            self.dut.terminate()
            self.dut.wait()
            self.dut.stdin.close()
            self.dut.stdout.close()
            self.dut.stderr.close()
            
            for shm in [shm_pins, shm_eeprom]:
                shm.seek(0)
                self.assertEqual(shm.read(), shm.expected)
        
        self.assertEqual(response, 'teardown\r\n10\r\n')

class Time(Shared):
    pass

for Δ in [50, 100, 200]:
    def test(self, Δ=Δ):
        start = int(srun('ms\n', readlines=1), 16)
        time.sleep(Δ/1000)
        self.assertAlmostEqual(int(srun('ms\n', readlines=1), 16) - start, Δ + 5, delta=5)
    
    setattr(Time, 'test_Δmillis()->{:x}'.format(Δ), test)

class Serial(Shared):
    pass

# NOTE Integers of 2^32 and larger cannot be tested, because the Arduino and gcc implementations of strtoul
# handle them differently
for cmd, expected in [
    ('pu -0x100 16\n', 'FFFFFF00\r\n10\r\n'),
    ('pu -0x1 16\n', 'FFFFFFFF\r\n10\r\n'),
    ('pu 0x0 16\n', '0\r\n3\r\n'),
    ('pu 0x1 16\n', '1\r\n3\r\n'),
    ('pu 0x7fffffff 16\n', '7FFFFFFF\r\n10\r\n'),
    ('pu 0x80000000 16\n', '80000000\r\n10\r\n'),
    ('pu 0xffffffff 16\n', 'FFFFFFFF\r\n10\r\n'),
    
    ('pu -0x100\n', '4294967040\r\n12\r\n'),
    ('pu -0x1\n', '4294967295\r\n12\r\n'),
    ('pu 0x0\n', '0\r\n3\r\n'),
    ('pu 0x1\n', '1\r\n3\r\n'),
    ('pu 0x7fffffff\n', '2147483647\r\n12\r\n'),
    ('pu 0x80000000\n', '2147483648\r\n12\r\n'),
    ('pu 0xffffffff\n', '4294967295\r\n12\r\n'),
    
    ('pi -256 10\n', '-256\r\n6\r\n'),
    ('pi -1 10\n', '-1\r\n4\r\n'),
    ('pi 0 10\n', '0\r\n3\r\n'),
    ('pi 1 10\n', '1\r\n3\r\n'),
    ('pi 2147483647 10\n', '2147483647\r\n12\r\n'),
    ('pi 2147483648 10\n', '-2147483648\r\n13\r\n'),
    ('pi 4294967295 10\n', '-1\r\n4\r\n'),
    
    ('pi -0400 16\n', 'FFFFFF00\r\n10\r\n'),
    ('pi -01 16\n', 'FFFFFFFF\r\n10\r\n'),
    ('pi 00 16\n', '0\r\n3\r\n'),
    ('pi 01 16\n', '1\r\n3\r\n'),
    ('pi 017777777777 16\n', '7FFFFFFF\r\n10\r\n'),
    ('pi 020000000000 16\n', '80000000\r\n10\r\n'),
    ('pi 037777777777 16\n', 'FFFFFFFF\r\n10\r\n'),
    
    ('pu\n', ''),
    ('pu foo\n', ''),
    ('pu bar 10\n', ''),
    ('pu 133 foos\n', ''),
    ('pu 1 16 3\n', ''),
    ('pu 123foo\n', ''),
    
    ('ps\n', ''),
    ('ps    \n', ''),
    ('ps Hello\n', 'Hello\r\n7\r\n'),
    ('ps Unicode_☺\n', 'Unicode_☺\r\n13\r\n'),
    ('ps foo bar   \n', ''),
]:
    def test(self, cmd=cmd, expected=expected):
        assert_srun(cmd, expected)
    
    cmd = cmd.split()
    
    setattr(Serial, 'test_{}({}){}'.format(
        expand_cmd(cmd[0]),
        ','.join(cmd[1:]) if len(cmd) > 1 else '',
        '->' + expected.split()[0] if expected else '!',
    ), test)

class PinsSim(Shared):
    @classmethod
    def setUpClass(cls):
        dummy.assertEqual(target, 'armock', 'not yet implemented for real hardware')

for cmd, expected, pin_value in [
    ('ar 0\n', '255\r\n', 0xff),
    ('ar 3\n', '0\r\n', 0),
    ('ar 7\n', '2\r\n', 2),
    ('dr 8\n', '1\r\n', 1),
    ('dr 9\n', '1\r\n', 4),
    ('dr 13\n', '1\r\n', 0xff),
    ('dr 15\n', '0\r\n', 0),
]:
    def test(self, cmd=cmd, expected=expected, pin_value=pin_value):
        pin = int(cmd.split(' ')[1])
        srun('pm {} 0\n'.format(pin))
        
        shm_pins.seek(pin)
        shm_pins.write(bytes([pin_value]))
        shm_pins.expected[pin] = pin_value
        
        assert_srun(cmd, expected)
    
    setattr(PinsSim, 'test_{}({})->{}'.format(expand_cmd(cmd), cmd[3:-1], expected[:-2].lower()), test)

for cmd, pin_value, error in [
    ('aw 15 0\n', 0, False),
    ('aw 13 1\n', 1, False),
    ('aw 12 0x7f\n', 0x7f, False),
    ('aw 8 0xff\n', 0xff, False),
    ('dw 7 0\n', 0, False),
    ('dw 4 1\n', 0xff, False),
    ('dw 2 2\n', 0, True),
    ('dw 1 0x80\n', 0, True),
    ('dw 0 0xff\n', 0, True),
]:
    def test(self, cmd=cmd, pin_value=pin_value, error=error):
        pin = int(cmd.split(' ')[1])
        srun('pm {} 1\n'.format(pin))
        
        srun(cmd)
        shm_pins.expected[pin] = pin_value
        
        if error: assert_error_msg(ereadline(), fname=expand_cmd(cmd))
    
    setattr(PinsSim, 'test_{}({},{}){}'.format(expand_cmd(cmd), cmd.split(' ')[1], cmd.split(' ')[2][:-1],
        '!' if error else '->{:x}'.format(pin_value)), test)

class PinsFixture(Shared):
    @classmethod
    def setUpClass(cls):
        dummy.assertEqual(target, 'nano-fixture', 'Requires Nano fixture')

for pins in [
    ('2', '4'),
    ('7', '8'),
    ('12', '13'),
]:
    def test(self, pins=pins):
        # Configure input pin first, to avoid having two outputs shorted
        srun('pm {1} 0\npm {0} 1\n'.format(*pins))
        assert_srun('dw {0} 0\ndr {1}\n'.format(*pins), '0\r\n')
        assert_srun('dw {0} 1\ndr {1}\n'.format(*pins), '1\r\n')
        
        srun('pm {0} 0\npm {1} 1\n'.format(*pins))
        assert_srun('dw {1} 0\ndr {0}\n'.format(*pins), '0\r\n')
        assert_srun('dw {1} 1\ndr {0}\n'.format(*pins), '1\r\n')
    
    setattr(PinsFixture, 'test_digitalRead/Write({}-{})'.format(*pins), test)

for pins in [
    ('11', '0'),
    ('10', '1'),
]:
    for pwm, analog_read in [
        ('0x00', 0x008), # In testing, 0% duty cycle didn't quite reach 0%
        ('0x80', 0x200),
        ('0xff', 0x3f8), # In testing, 100% duty cycle didn't quite reach 100%
    ]:
        def test(self, pins=pins, pwm=pwm, analog_read=analog_read):
            srun('pm {0} 1\naw {0} {1}\n'.format(pins[0], pwm))
            
            # Time constant is 0.22 Hz. In testing, 1 s settling time was not enough
            time.sleep(1.5)
            
            '''
            Theoretical variation is:
            - 100 kΩ resistor
            - For 5 V nano, 2.5 V difference between capacitor and driving pin
            - 2.5 V / 100 kΩ = 25 mA driving current
            - 2 ms PWM period for these pins on Arduino nano
            - 2 ms * 25 mA = 50 nC variability in capacitor charge
            - 2.2 μF capacitor
            - 50 nC / 2.2 μF = 22.7 mV variability in capacitor voltage
            - At ~5 mV / unit for analog pins, this is ±2 units
            
            Test results (using 1.5 s settling time):
            
            Pins   Expected  Deltas
            D10-A1 0x000     + 4  + 4  + 7  + 7  + 8  + 7  + 7  + 8  + 6  + 7
            D10-A1 0x200     - 2  - 3  - 2  - 2  - 2  - 1  - 2  - 3  - 2  - 2
            D10-A1 0x3ff     - 6  - 5  - 4  - 5  - 5  - 5  - 4  - 5  - 5  - 5
            D11-A0 0x000     + 5  + 5  + 9  + 9  +10  +11  +10  + 9  + 9  +11
            D11-A0 0x200     - 4  - 2  - 2  - 3  - 2  - 4  - 3  - 4  - 1  - 2
            D11-A0 0x3ff     - 8  - 8  - 7  - 7  - 7  - 7  - 7  - 7  - 6  - 8
            
            For the mid voltage, variation is -1 to -4, comparable in range to theory
            '''
            dummy.assertAlmostEqual(int(srun('ar {}\n'.format(pins[1]), readlines=1)), analog_read, delta=4)
        
        setattr(PinsFixture, 'test_analogRead/Write({}-{},{})'.format(*pins, pwm), test)

class InvalidPinModes(Shared):
    @classmethod
    def setUpClass(cls):
        dummy.assertEqual(target, 'armock', 'Pin modes only enforced on sim')

for cmd, expected in [
    ('ar 0\n', '-1\r\n'),
    ('aw 1 0\n', ''),
    ('aw 2 0x80\n', ''),
    ('aw 3 0xff\n', ''),
    ('dr 7\n', '-1\r\n'),
    ('dw 8 0\n', ''),
    ('dw 10 0x80\n', ''),
    ('dw 15 0xff\n', ''),
    ('pm 0 2\n', ''),
    ('pm 14 0xff\n', ''),
    ('pm 15 0x10\n', ''),
    ('pm 16 0\n', ''),
]:
    def test(self, cmd=cmd, expected=expected):
        assert_srun(cmd, expected)
        assert_error_msg(ereadline(), fname=expand_cmd(cmd))
    
    setattr(InvalidPinModes, 'test_{}({})!'.format(expand_cmd(cmd), cmd[3:-1].replace(' ', ',')), test)

class EEPROM(Shared):
    @classmethod
    def setUpClass(cls):
        dummy.assertEqual(target, 'armock', 'not yet implemented for real hardware')

# NOTE Arduino allows reading and writing address outside the valid range, in which case they wrap around.
# However, I do not know a good way to reproduce that in C++, so armock doesn't support it
for cmd, index, expected in [
    ('ee   0x0\n', 0x000, '255\r\n'),
    ('ee     1\n', 0x001, '254\r\n'),
    ('ee    02\n', 0x002, '128\r\n'),
    ('ee 0x07f\n', 0x07f, '127\r\n'),
    ('ee   128\n', 0x080, '64\r\n'),
    ('ee  0377\n', 0x0ff, '48\r\n'),
    ('ee 0x100\n', 0x100, '32\r\n'),
    ('ee   511\n', 0x1ff, '16\r\n'),
    ('ee 01000\n', 0x200, '15\r\n'),
    ('ee 0x2ff\n', 0x2ff, '2\r\n'),
    ('ee   768\n', 0x300, '1\r\n'),
    ('ee 01777\n', 0x3ff, '0\r\n'),
]:
    def test(self, cmd=cmd, index=index, expected=expected):
        shm_eeprom.seek(index)
        shm_eeprom.write(bytes([int(expected)]))
        shm_eeprom.expected[index] = int(expected)
        
        assert_srun(cmd, expected)
    
    setattr(EEPROM, 'test_read_EEPROM[{}]->{}'.format(cmd.split()[1], expected[:-2]), test)

for cmd, index, ee_value in [
    ('ee   0x0  255\n', 0x000, 0xff),
    ('ee     1 0376\n', 0x001, 0xfe),
    ('ee    02 0x80\n', 0x002, 0x80),
    ('ee 0x07f  127\n', 0x07f, 0x7f),
    ('ee   128 0100\n', 0x080, 0x40),
    ('ee  0377 0x30\n', 0x0ff, 0x30),
    ('ee 0x100   32\n', 0x100, 0x20),
    ('ee   511  020\n', 0x1ff, 0x10),
    ('ee 01000 0x0f\n', 0x200, 0x0f),
    ('ee 0x2ff    2\n', 0x2ff, 0x02),
    ('ee   768   01\n', 0x300, 0x01),
    ('ee 01777  0x0\n', 0x3ff, 0x00),
]:
    def test(self, cmd=cmd, index=index, ee_value=ee_value):
        srun(cmd)
        shm_eeprom.expected[index] = ee_value
    
    setattr(EEPROM, 'test_write_EEPROM[{}]->{}'.format(cmd.split()[1], ee_value), test)

class ShmClearing(Shared):
    @classmethod
    def setUpClass(cls):
        dummy.assertEqual(target, 'armock', 'shm tests do not apply to real hardware')
    
    def setUp(self):
        pass # Overwrite Shared.setUp() to skip it
    
    def test_Pins_Cleared(self):
        shm_pins.seek(0)
        shm_pins.write(bytes([i % 256 for i in range(shm_pins.size)]))
        
        Shared.setUp(self)
    
    def test_EEPROM_Not_Cleared(self):
        shm_eeprom.seek(0)
        shm_eeprom.write(bytes([i % 256 for i in range(shm_eeprom.size)]))
        
        Shared.setUp(self, clear_eeprom=False)
        
        shm_eeprom.expected = bytes([i % 256 for i in range(shm_eeprom.size)])

# Remove stray test left behind by test-creating loops
del test
