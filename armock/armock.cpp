#include <iostream>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>

#define INPUT 0x0
#define OUTPUT 0x1
#define MODE_UNDEFINED 0x2
#define PINS 16

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t i8;
typedef int16_t i16;
typedef int32_t i32;
typedef int64_t i64;

// Based on glibc's assert implementation
extern const char *__progname;
#define check(expr) (static_cast <bool> (expr) ? false : fprintf(stderr, "%s: %s:%u: %s: Check `%s' failed.\n", __progname, __FILE__, __LINE__, __PRETTY_FUNCTION__, #expr))

u32 millis() {
  timespec result;
  clock_gettime(CLOCK_MONOTONIC, &result);
  return result.tv_sec*1000 + result.tv_nsec/1000000;
}

void delay(u32 ms) { sleep(ms/1000); usleep((ms % 1000)*1000); }
void delayMicroseconds(u16 us) { usleep(us); }

struct SerialMock {
  void begin(u32) {}
  
  i16 available() {
    i32 result;
    ioctl(STDIN_FILENO, FIONREAD, &result);
    return result;
  }
  
  i16 read() {
    u8 byte;
    return ::read(STDIN_FILENO, &byte, 1) < 0 ? -1 : byte;
  }
  
  size_t print(u32 v        ) { return printf("%u", v); }
  size_t print(i32 v        ) { return printf("%i", v); }
  size_t print(const char* v) { return printf("%s", v); }
  
  template <typename T> size_t println(T v) { return print(v) + print("\r\n"); }
};

SerialMock Serial;

u8* pin_values;
u8 pin_modes[PINS];

void pinMode(u8 pin, u8 mode) {
  if(check(pin < PINS) || check(mode < 2)) return;
  pin_modes[pin] = mode;
}

i16 digitalRead(u8 pin) {
  if(check(pin < PINS) || check(pin_modes[pin] == INPUT)) return -1;
  return (bool) pin_values[pin];
}

void digitalWrite(u8 pin, u8 v) {
  if(check(pin < PINS) || check(pin_modes[pin] == OUTPUT) || check(v < 2)) return;
  pin_values[pin] = v ? 0xFF : 0;
}

i16 analogRead(u8 pin) {
  if(check(pin < PINS) || check(pin_modes[pin] == INPUT)) return -1;
  return pin_values[pin];
}

void analogWrite(u8 pin, i16 v) {
  if(check(pin < PINS) || check(pin_modes[pin] == OUTPUT) || check(v == v & 0xFF)) return;
  pin_values[pin] = v & 0xFF;
}

#include SKETCH

u8* get_shm(const char* name, u32 size) {
  int shm_file = shm_open(name, O_CREAT | O_RDWR, 0664);
  if(shm_file < 0) {
    fprintf(stderr, "Error opening /dev/shm/");
    perror(name);
    exit(1);
  }
  
  if(ftruncate(shm_file, size) < 0) {
    fprintf(stderr, "Error sizing /dev/shm/");
    perror(name);
    exit(1);
  }
  
  u8* result = (u8*) mmap(0, PINS, PROT_READ | PROT_WRITE, MAP_SHARED, shm_file, 0);
  if(result < 0) {
    fprintf(stderr, "Error mapping /dev/shm/");
    perror(name);
    exit(1);
  }
  
  return result;
}

int main(int argc, char** argv) {
  /*if(argc < 2) {
    printf("Usage: armock PSEUDOTERMINAL\n");
    exit(0);
  }
  
  Serial.fd = open(argv[1], O_RDWR | O_NONBLOCK);
  if(Serial.fd < 0) {
    perror(argv[1]);
    exit(1);
  }*/
  
  pin_values = get_shm("armock_pins", PINS);
  
  for(u8 i = 0; i < PINS; ++i) {
    pin_modes[i] = MODE_UNDEFINED;
    pin_values[i] = 0;
  }
  
#ifdef EEPROM_h
  EEPROM = get_shm("armock_eeprom", EEPROM_SIZE);
#endif
  
  setvbuf (stdout, NULL, _IOLBF, 1024); // Line-buffering
  
  setup();
  
  while(true) loop();
}
