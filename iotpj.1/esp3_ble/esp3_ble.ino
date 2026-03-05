#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include "DHT.h"

#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// BLE UUID
#define SERVICE_UUID        "12345678-1234-1234-1234-1234567890ab"
#define CHARACTERISTIC_UUID "abcdefab-1234-1234-1234-abcdefabcdef"

BLEServer *pServer = NULL;
BLECharacteristic *pCharacteristic = NULL;
bool deviceConnected = false;

// Callback BLE
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) { deviceConnected = true; }
  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    pServer->startAdvertising();
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("ESP3: Khoi dong BLE");

  dht.begin();

  // BLE setup
  BLEDevice::init("ESP3");  // Ten BLE thiet bi
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_READ
                    );
  pCharacteristic->addDescriptor(new BLE2902());

  pService->start();

  pServer->getAdvertising()->addServiceUUID(SERVICE_UUID);
  pServer->getAdvertising()->setScanResponse(true);
  pServer->getAdvertising()->start();

  Serial.println("ESP3: San sang quang ba BLE");
}

void loop() {
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) {
    Serial.println("ESP3: Loi doc DHT11");
    delay(3000);
    return;
  }

  if (deviceConnected) {
    char sendBuffer[50];
    snprintf(sendBuffer, sizeof(sendBuffer),
             "ESP3 Temp=%.2fC Humi=%.2f%%", temp, hum);

    Serial.print("ESP3 gui du lieu: ");
    Serial.println(sendBuffer);

    pCharacteristic->setValue(sendBuffer);
    pCharacteristic->notify();
  }

  delay(5000); // gui moi 5 giay
}
