#include <Arduino.h>

// ====== Cấu hình PWM ======
const int freq = 1000;      // Tần số PWM
const int resolution = 8;   // Độ phân giải 8-bit (0-255)
const int pwmChannels[6] = {0, 1, 2, 3, 4, 5}; // 6 kênh PWM riêng

// ====== Chân motor: {PWM, IN1, IN2} ======
// Mỗi motor điều khiển bởi 1 PWM + 2 chân số
const int motorPins[6][3] = {
  {12, 33, 32}, // M1 - PWM, IN1, IN2
  {14, 26, 27}, // M2
  {4, 16, 17},  // M3
  {5, 18, 19},  // M4
  {23, 13, 15}, // M5
  {22, 21, 25}  // M6
};

void setup() {
  Serial.begin(115200);
  Serial.println("Khoi dong...");

  // Khởi tạo PWM cho từng động cơ
  for (int i = 0; i < 6; i++) {
    ledcSetup(pwmChannels[i], freq, resolution);
    ledcAttachPin(motorPins[i][0], pwmChannels[i]); // PWM pin
  }

  // Cấu hình IN1 và IN2 làm output
  for (int i = 0; i < 6; i++) {
    pinMode(motorPins[i][1], OUTPUT);
    pinMode(motorPins[i][2], OUTPUT);
  }
}

// ====== Hàm điều khiển motor ======
// motor: 0..5
// speed: -255..255 (âm = chạy ngược)
void setMotor(int motor, int speed) {
  bool dir = (speed >= 0);
  speed = abs(speed);
  if (speed > 255) speed = 255;

  digitalWrite(motorPins[motor][1], dir ? HIGH : LOW);
  digitalWrite(motorPins[motor][2], dir ? LOW : HIGH);
  ledcWrite(pwmChannels[motor], speed);
}

void loop() {
  Serial.println("Chay xuoi tat ca dong co");
  for (int i = 0; i < 6; i++) setMotor(i, 200); // chạy xuôi
  delay(2000);

  Serial.println("Dung tat ca dong co");
  for (int i = 0; i < 6; i++) setMotor(i, 0); // dừng
  delay(1000);

  Serial.println("Chay nguoc tat ca dong co");
  for (int i = 0; i < 6; i++) setMotor(i, -200); // chạy ngược
  delay(2000);

  Serial.println("Dung");
  for (int i = 0; i < 6; i++) setMotor(i, 0); // dừng
  delay(2000);
}
