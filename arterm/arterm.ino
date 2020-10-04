// Commands follow the pattern COMMAND [ARG1] [ARG2]
//   ms - millis()
//   pu - Serial.println<u32>()
//   pi - Serial.println<i32>()
//   ps - Serial.println<string>()
//   pm - pinMode()
//   dr - digitalRead()
//   dw - digitalWrite()
//   ar - analogRead()
//   aw - analogWrite()
//   ee - EEPROM[]
// ARG1 is a 1-8 digit hex value, ARG2 is 1-2 digits

#include <EEPROM.h>

typedef int32_t i32;

u8 unhex(u8 c) {
  if('0' <= c && c <= '9') return c - '0';
  if('a' <= c && c <= 'f') return c - 'a' + 0xA;
  if('A' <= c && c <= 'F') return c - 'A' + 0xA;
  return 0xFF;
}

struct FSM {
  struct State {
    State (FSM::* call)(u8);
    bool operator==(State rhs) { return call == rhs.call; }
    bool operator==(State (FSM::* rhs)(u8)) { return call == rhs; }
  };
  
  State state;
  u8 counter;
  u8 cmd[2];
  u32 arg1;
  u8 arg2;
  char string_arg[61];
  
  FSM() { reset(); }
  
  void consume(u8 next) {
    if(next == '\n') {
      if(state == &FSM::space) {
        if(cmd[0] == 'm' && cmd[1] == 's') Serial.println(millis());
      } else if(state == &FSM::string && counter) {
        if(cmd[0] == 'p' && cmd[1] == 's') Serial.println((u32) Serial.println(string_arg));
      } else if(state == &FSM::hex1 && counter) {
        if(cmd[0] == 'p' && cmd[1] == 'u') Serial.println((u32) Serial.println((u32) arg1));
        if(cmd[0] == 'p' && cmd[1] == 'i') Serial.println((u32) Serial.println((i32) arg1));
        if(cmd[0] == 'd' && cmd[1] == 'r') Serial.println(digitalRead(arg1));
        if(cmd[0] == 'a' && cmd[1] == 'r') Serial.println(analogRead(arg1));
        if(cmd[0] == 'e' && cmd[1] == 'e') Serial.println(EEPROM[arg1]);
      } else if(state == &FSM::hex2 && counter) {
        if(cmd[0] == 'p' && cmd[1] == 'm') pinMode(arg1, arg2);
        if(cmd[0] == 'd' && cmd[1] == 'w') digitalWrite(arg1, arg2);
        if(cmd[0] == 'a' && cmd[1] == 'w') analogWrite(arg1, arg2);
        if(cmd[0] == 'e' && cmd[1] == 'e') EEPROM[arg1] = arg2;
      }
      
      reset();
    } else {
      State old_state = state;
      state = (this ->* (state.call))(next);
      counter = state == old_state ? counter + 1 : 0;
    }
  }
  
  State start(u8 next) {
    cmd[counter] = next;
    return counter ? (State) { &FSM::space } : (State) { &FSM::start };
  }
  
  State space(u8 next) {
    if(cmd[0] == 'p' && cmd[1] == 's') return { &FSM::string };
    return next == ' ' ? (State) { &FSM::hex1 } : (State) { &FSM::rejected };
  }
  
  State hex1(u8 next) {
    if(counter && next == ' ') return { &FSM::hex2 };
    if(counter >= sizeof(arg1)*2 || unhex(next) == 0xFF) return { &FSM::rejected };
    arg1 = 0x10*arg1 + unhex(next);
    return { &FSM::hex1 };
  }
  
  State hex2(u8 next) {
    if(counter >= sizeof(arg2)*2 || unhex(next) == 0xFF) return { &FSM::rejected };
    arg2 = 0x10*arg2 + unhex(next);
    return { &FSM::hex2 };
  }
  
  State string(u8 next) {
    string_arg[counter] = next;
    return counter >= 60 ? (State) { &FSM::rejected } : (State) { &FSM::string };
  }
  
  State rejected(u8 next) {
    return { &FSM::rejected };
  }
  
  void reset() {
    counter = 0;
    cmd[0] = ' ';
    cmd[1] = ' ';
    arg1 = 0;
    arg2 = 0;
    memset(string_arg, 0, sizeof(string_arg));
    state = { &FSM::start };
  }
};

FSM fsm = FSM();

void setup() {
  Serial.begin(115200);
}

void loop() {
  Serial.available() ? fsm.consume(Serial.read()) : delay(1);
}
