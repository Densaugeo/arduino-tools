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

#include <EEPROM.h>

enum arg_type { NONE, INTEGER, STRING };

char line[65];
char line_index = 0;
char DELIMITERS[5] = " \t\r\n";

void process_line() {
  char* command = strtok(line, DELIMITERS);
  if(command == NULL) return;
  
  char* args[3];
  arg_type arg_types[3] = { NONE, NONE, NONE };
  u32 args_u32[3] = { 0, 0, 0 };
  
  for(u8 i = 0; i < 3; ++i) {
    args[i] = strtok(NULL, DELIMITERS);
    if(args[i] != NULL) {
      char* endptr;
      args_u32[i] = (u32) strtoul(args[i], &endptr, 0);
      arg_types[i] = STRING;
      for(u8 j = 0; j < 5; ++j) if(*endptr == DELIMITERS[j]) arg_types[i] = INTEGER;
    }
  }
  
  if(arg_types[0] == NONE) {
    if(strcmp(command, "ms") == 0) Serial.println(millis(), HEX);
  } else if(arg_types[0] == STRING && arg_types[1] == NONE) {
    if(strcmp(command, "ps") == 0) Serial.println((u32) Serial.println(args[0]));
  } else if(arg_types[0] == INTEGER && arg_types[1] == NONE) {
    if(strcmp(command, "pu") == 0) Serial.println((u32) Serial.println(args_u32[0]));
    if(strcmp(command, "pi") == 0) Serial.println((u32) Serial.println((int32_t) args_u32[0]));
    if(strcmp(command, "dr") == 0) Serial.println(digitalRead(args_u32[0]));
    if(strcmp(command, "ar") == 0) Serial.println(analogRead(args_u32[0]));
    if(strcmp(command, "ee") == 0) Serial.println(EEPROM[args_u32[0]]);
  } else if(arg_types[0] == INTEGER && arg_types[1] == INTEGER && arg_types[2] == NONE) {
    if(strcmp(command, "pu") == 0) Serial.println((u32) Serial.println(args_u32[0], args_u32[1]));
    if(strcmp(command, "pi") == 0) Serial.println((u32) Serial.println((int32_t) args_u32[0], args_u32[1]));
    if(strcmp(command, "pm") == 0) pinMode(args_u32[0], args_u32[1]);
    if(strcmp(command, "dw") == 0) digitalWrite(args_u32[0], args_u32[1]);
    if(strcmp(command, "aw") == 0) analogWrite(args_u32[0], args_u32[1]);
    if(strcmp(command, "ee") == 0) EEPROM[args_u32[0]] = args_u32[1];
  }
}

void setup() {
  Serial.begin(115200);
}

void loop() {
  char next = Serial.read();
  if(next == -1) return;
  
  if(line_index < 64) line[line_index++] = next;
  
  if(next == '\n') {
    line[line_index] = '\0';
    line_index = 0;
    process_line();
  }
}
