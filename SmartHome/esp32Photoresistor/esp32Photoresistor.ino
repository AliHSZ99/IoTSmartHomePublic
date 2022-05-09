#include "WiFi.h"
#include "PubSubClient.h"
#include <SPI.h>//https://www.arduino.cc/en/reference/SPI
#include <MFRC522.h>//https://github.com/miguelbalboa/rfid

//#include "DHT.h"
//
//#define DHTPIN 4     // Digital pin connected to the DHT sensor
//
//// Uncomment whatever type you're using!
//#define DHTTYPE DHT11   // DHT 11
//DHT dht(DHTPIN, DHTTYPE);

//Constants
#define SS_PIN 5
#define RST_PIN 0

//Parameters
//const int ipaddress[4] = {103, 97, 67, 25};

//Variables
byte nuidPICC[4] = {0, 0, 0, 0};
MFRC522::MIFARE_Key key;
MFRC522 rfid = MFRC522(SS_PIN, RST_PIN);

// WiFi
const char *ssid = "LisaPhone"; 
const char *password = "irur7313";

const char* mqtt_server = "192.168.109.212";

WiFiClient vanieriot;
PubSubClient client(vanieriot);

// constants for the pins where sensors are plugged into.
const int sensorPin = 32;
const int ledPin = 26;

// Set up some global variables for the light level an initial value.
float lightVal;   // light reading
String rfidVal;

// MQTT
void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("WiFi connected - ESP-32 IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(String topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messagein;
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messagein += (char)message[i];
  }

  if(topic=="room/light"){
    if (messagein == "ON") 
      Serial.println("Light is ON");
  }else{
          Serial.println("Light is OFF");

  }
  
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
 
    
   //  String clientId = "ESP8266Client-";
   // clientId += String(random(0xffff), HEX);
    // Attempt to connect
   // if (client.connect(clientId.c_str())) {
   if (client.connect("vanieriot")) {

      Serial.println("connected");  
      client.subscribe("room/light");
   } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}


void setup()
{
  Serial.begin(9600);
//  dht.begin();

  // MQTT
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  Serial.println(F("Initialize System"));
  //init rfid D8,D5,D6,D7
  SPI.begin();
  rfid.PCD_Init();
  Serial.print(F("Reader :"));
  rfid.PCD_DumpVersionToSerial();
  
  // We'll set up the LED pin to be an output.
  pinMode(ledPin, OUTPUT);
}


void loop()
{
//  // Reading temperature or humidity takes about 250 milliseconds!
//  // Sensor readings may also be up to 2 seconds 'old' (its a very slow sensor)
//  float humidity = dht.readHumidity();
//  // Read temperature as Celsius (the default)
//  float temperature = dht.readTemperature();
//
//  // Check if any reads failed and exit early (to try again).
////  if (isnan(h) || isnan(t) || isnan(f)) {
////    Serial.println(F("Failed to read from DHT sensor!"));
////    return;
////  }
//
//  Serial.print(F("Humidity: "));
//  Serial.print(humidity);
//  Serial.print(F("%  Temperature: "));
//  Serial.print(temperature);
//  Serial.print(F("°C "));
  
  // MQTT
  if (!client.connected()) {
    reconnect();
  }
  
  if(!client.loop())
    client.connect("vanieriot");
    
  sleep(0.5);
  lightVal = analogRead(sensorPin); // read the current light levels
  rfidVal = printDec(rfid.uid.uidByte, rfid.uid.size);
  Serial.println(lightVal);

  // If too dark, light up 
  if(lightVal < 2900)
  {
      digitalWrite (ledPin, HIGH);

      char lightArr [8];
      char rfidArr [20];
      
      client.publish("PhotoresistorInfo", dtostrf(lightVal,6,2,lightArr));
      client.publish("RFIDInfo", rfidVal.c_str());
      Serial.println(lightVal);
  }

  // Otherwise, keep LED off
  else
  {
    digitalWrite (ledPin, LOW); // turn off light

    char lightArr [8];
    char rfidArr [20];
    
      
    client.publish("PhotoresistorInfo", dtostrf(lightVal,6,2,lightArr));
    client.publish("RFIDInfo", rfidVal.c_str());
//    Serial.println("OFFFFFFff");
    Serial.println(lightVal);
  }
  
//  char tempArr [8];
//  char humArr [8];
//
//  client.publish("ReadTemperature", dtostrf(temperature, 6, 2, tempArr));
//  client.publish("ReadHumidity", dtostrf(humidity, 6, 2, humArr));

  readRFID();
  
}

void readRFID(void ) { /* function readRFID */
 ////Read RFID card
 for (byte i = 0; i < 6; i++) {
   key.keyByte[i] = 0xFF;
 }
 // Look for new 1 cards
 if ( ! rfid.PICC_IsNewCardPresent())
   return;
 // Verify if the NUID has been readed
 if (  !rfid.PICC_ReadCardSerial())
   return;
 // Store NUID into nuidPICC array
 for (byte i = 0; i < 4; i++) {
   nuidPICC[i] = rfid.uid.uidByte[i];
 }
 Serial.print(F("RFID In dec: "));
 
 Serial.println(printDec(rfid.uid.uidByte, rfid.uid.size));
 // Halt PICC
 rfid.PICC_HaltA();
 // Stop encryption on PCD
 rfid.PCD_StopCrypto1();
}

/**
   Helper routine to dump a byte array as hex values to Serial.
*/
void printHex(byte *buffer, byte bufferSize) {
 for (byte i = 0; i < bufferSize; i++) {
   Serial.print(buffer[i] < 0x10 ? " 0" : " ");
   Serial.print(buffer[i], HEX);
 }
}

/**
   Helper routine to dump a byte array as dec values to Serial.
*/
String printDec(byte *buffer, byte bufferSize) {
  String value = "";
 for (byte i = 0; i < bufferSize; i++) {
   value += buffer[i] < 0x10 ? " 0" : " " + String(buffer[i],DEC);
//   Serial.print(buffer[i] < 0x10 ? " 0" : " ");
//   Serial.print(buffer[i], DEC);
 }

 return value;
}
