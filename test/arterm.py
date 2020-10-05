import unittest, os, time, select, subprocess, fcntl

ARMOCK_PATH = os.path.join(os.path.dirname(__file__), 'armock')

dummy = unittest.TestCase()

def ereadline():
    select.select([armock.stderr], [], [], 1)[0]
    return str(armock.stderr.readline(), 'utf-8')

def sreadline(count=1):
    result = []
    line = b''
    
    while len(result) < count:
        # Select waits for data with a timeout
        if line == b'' and  len(select.select([armock.stdout], [], [], 1)[0]) == 0: break
        
        line = armock.stdout.readline()
        # .readline() will return an empty string if it doesn't have data available
        if(line): result.append(line)
    
    return ''.join(str(line, 'utf-8') for line in result)

def srun(cmd, readlines=0):
    armock.stdin.write(bytes(cmd, 'utf-8'))
    armock.stdin.flush()
    return sreadline(count=readlines) if readlines else ''

def assert_srun(cmd, expected):
    dummy.assertEquals(srun(cmd, readlines=expected.count('\n')), expected)

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
    global shm_pins, shm_eeprom
    
    shm_pins = open('/dev/shm/armock_pins', 'w+b', buffering=0)
    shm_pins.size = 16
    shm_eeprom = open('/dev/shm/armock_eeprom', 'w+b', buffering=0)
    shm_eeprom.size = 1024

def tearDownModule():
    pass

class Shared(unittest.TestCase):
    def setUp(self, clear_eeprom=True):
        global armock
        
        shm_pins.expected = bytearray(shm_pins.size)
        shm_eeprom.expected = bytearray(shm_eeprom.size)
        
        if clear_eeprom:
            shm_eeprom.seek(0)
            shm_eeprom.write(bytes(shm_eeprom.size))
        
        self.armock = subprocess.Popen([ARMOCK_PATH, 'armock_pins', 'armock_eeprom'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        armock = self.armock
        fcntl.fcntl(armock.stdout, fcntl.F_SETFL, fcntl.fcntl(armock.stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(armock.stderr, fcntl.F_SETFL, fcntl.fcntl(armock.stderr, fcntl.F_GETFL) | os.O_NONBLOCK)
        
        # Wait until armock has finished starting up
        assert_srun('ps ready\n', 'ready\r\n7\r\n')
    
    def tearDown(self):
        dummy.assertEqual(armock.stderr.readline(), b'')
        response = srun('ps teardown\n', readlines=2)
        self.armock.terminate()
        self.assertEquals(response, 'teardown\r\n10\r\n')
        
        for shm in [shm_pins, shm_eeprom]:
            shm.seek(0)
            self.assertEquals(shm.read(), shm.expected)

class Time(Shared):
    pass

for Δ in [50, 100, 200]:
    def test(self, Δ=Δ):
        start = int(srun('ms\n', readlines=1))
        time.sleep(Δ/1000)
        self.assertAlmostEqual(int(srun('ms\n', readlines=1)) - start, Δ + 5, delta=5)
    
    setattr(Time, 'Δmillis()->{}'.format(Δ), test)

class Serial(Shared):
    pass

for cmd, expected in [
    ('pu 0\n', '0\r\n3\r\n'),
    ('pu 00000000\n', '0\r\n3\r\n'),
    ('pu 0001\n', '1\r\n3\r\n'),
    ('pu 1\n', '1\r\n3\r\n'),
    ('pu 7FFFFFFF\n', '2147483647\r\n12\r\n'),
    ('pu 80000000\n', '2147483648\r\n12\r\n'),
    ('pu FFFFFFFF\n', '4294967295\r\n12\r\n'),
    
    ('ps Hello\n', 'Hello\r\n7\r\n'),
    ('ps Unicode_☺!\n', 'Unicode_☺!\r\n14\r\n'),
    
    ('pi 0\n', '0\r\n3\r\n'),
    ('pi 00000000\n', '0\r\n3\r\n'),
    ('pi 0001\n', '1\r\n3\r\n'),
    ('pi 1\n', '1\r\n3\r\n'),
    ('pi 7FFFFFFF\n', '2147483647\r\n12\r\n'),
    ('pi 80000000\n', '-2147483648\r\n13\r\n'),
    ('pi FFFFFFFF\n', '-1\r\n4\r\n'),
]:
    def test(self, cmd=cmd, expected=expected):
        assert_srun(cmd, expected)
    
    setattr(Serial, '{}({})'.format(expand_cmd(cmd), cmd[3:-1]), test)

class Pins(Shared):
    pass

for cmd, expected, pin_value in [
    ('ar 0\n', '255\r\n', 0xff),
    ('ar 3\n', '0\r\n', 0),
    ('ar 7\n', '2\r\n', 2),
    ('dr 8\n', '1\r\n', 1),
    ('dr 9\n', '1\r\n', 4),
    ('dr b\n', '1\r\n', 0xff),
    ('dr f\n', '0\r\n', 0),
]:
    def test(self, cmd=cmd, expected=expected, pin_value=pin_value):
        pin = int(cmd.split(' ')[1], 16)
        srun('pm {:x} 0\n'.format(pin))
        
        shm_pins.seek(pin)
        shm_pins.write(bytes([pin_value]))
        shm_pins.expected[pin] = pin_value
        
        assert_srun(cmd, expected)
    
    setattr(Pins, '{}({})->{}'.format(expand_cmd(cmd), cmd[3], expected[:-2]), test)

for cmd, pin_value, error in [
    ('aw f 0\n', 0, False),
    ('aw d 1\n', 1, False),
    ('aw c 7f\n', 0x7f, False),
    ('aw 8 ff\n', 0xff, False),
    ('dw 7 0\n', 0, False),
    ('dw 4 1\n', 0xff, False),
    ('dw 2 2\n', 0, True),
    ('dw 1 80\n', 0, True),
    ('dw 0 ff\n', 0, True),
]:
    def test(self, cmd=cmd, pin_value=pin_value, error=error):
        pin = int(cmd.split(' ')[1], 16)
        srun('pm {:x} 1\n'.format(pin))
        
        srun(cmd)
        shm_pins.expected[pin] = pin_value
        
        if error: assert_error_msg(ereadline(), fname=expand_cmd(cmd))
    
    setattr(Pins, '{}({},{}){}'.format(expand_cmd(cmd), cmd[3], cmd[5:-1],
        '!' if error else '->{}'.format(pin_value)), test)

class InvalidPinModes(Shared):
    pass

for cmd, expected in [
    ('ar 0\n', '-1\r\n'),
    ('aw 1 0\n', ''),
    ('aw 2 80\n', ''),
    ('aw 3 ff\n', ''),
    ('dr 7\n', '-1\r\n'),
    ('dw 8 0\n', ''),
    ('dw a 80\n', ''),
    ('dw f ff\n', ''),
    ('pm 0 2\n', ''),
    ('pm e ff\n', ''),
    ('pm f 10\n', ''),
    ('pm 10 0\n', ''),
]:
    def test(self, cmd=cmd, expected=expected):
        assert_srun(cmd, expected)
        assert_error_msg(ereadline(), fname=expand_cmd(cmd))
    
    setattr(InvalidPinModes, '{}({})!'.format(expand_cmd(cmd), cmd[3:-1].replace(' ', ',')), test)

class EEPROM(Shared):
    pass

for cmd, expected in [
    ('ee 000\n', '255\r\n'),
    ('ee 001\n', '254\r\n'),
    ('ee 002\n', '128\r\n'),
    ('ee 07f\n', '127\r\n'),
    ('ee 080\n', '64\r\n'),
    ('ee 0ff\n', '48\r\n'),
    ('ee 100\n', '32\r\n'),
    ('ee 1ff\n', '16\r\n'),
    ('ee 200\n', '15\r\n'),
    ('ee 2ff\n', '2\r\n'),
    ('ee 300\n', '1\r\n'),
    ('ee 3ff\n', '0\r\n'),
]:
    def test(self, cmd=cmd, expected=expected):
        index = int(cmd.split(' ')[1], 16)
        
        shm_eeprom.seek(index)
        shm_eeprom.write(bytes([int(expected)]))
        shm_eeprom.expected[index] = int(expected)
        
        assert_srun(cmd, expected)
    
    setattr(EEPROM, 'read_EEPROM[{}]->{}'.format(cmd[3:6], expected[:-2]), test)

for cmd, ee_value in [
    ('ee 000 ff\n', 0xff),
    ('ee 001 fe\n', 0xfe),
    ('ee 002 80\n', 0x80),
    ('ee 07f 7f\n', 0x7f),
    ('ee 080 40\n', 0x40),
    ('ee 0ff 30\n', 0x30),
    ('ee 100 20\n', 0x20),
    ('ee 1ff 10\n', 0x10),
    ('ee 200 0f\n', 0x0f),
    ('ee 2ff 02\n', 0x02),
    ('ee 300 01\n', 0x01),
    ('ee 3ff 00\n', 0x00),
]:
    def test(self, cmd=cmd, ee_value=ee_value):
        srun(cmd)
        shm_eeprom.expected[int(cmd.split(' ')[1], 16)] = ee_value
    
    setattr(EEPROM, 'write_EEPROM[{}]->{:x}'.format(cmd[3:6], ee_value), test)

class ShmClearing(Shared):
    def setUp(self):
        pass
    
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
