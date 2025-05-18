const int FSR_PIN_1 = A0;  // 발받침대 FSR 센서
const int FSR_PIN_2 = A1;  // 방석 FSR 센서

void setup() {
  Serial.begin(9600);
}

void loop() {
  // FSR 센서 값 읽기 (0-1023)
  int fsr1Value = analogRead(FSR_PIN_1);
  int fsr2Value = analogRead(FSR_PIN_2);
  
  // 시리얼로 전송 (CSV 형식)
  Serial.print(fsr1Value);
  Serial.print(",");
  Serial.println(fsr2Value);
  
  delay(100);  // 100ms 딜레이
} 