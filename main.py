from machine import I2C, Pin
from bme280 import BME280
from sh1106 import SH1106_I2C
from micropython import const
import time
import network
import urequests
import wifi_utils
import config

# KONSTANY
# nastavení periody čtení BM280 čidla
READ_INTERVAL_MS = const(5000)  
# řízení hystereze ventilátoru 
FAN_HYSTERESIS = const(0.5)
# adresy I2C periferii 
BME280_ADDRESS = const(0x76)
OLED_ADDRESS = const(0x3C)

#url toho co budeme pouzivat
API_URL = "https://api.thingspeak.com/update"

def display(oled,temperature, humidity, preasure, status, threshold):
    oled.fill(0)
    oled.text("temp: {:.1f}".format(temperature), 0, 0)
    oled.text("humidity: {:.1f}".format(humidity), 0, 12)
    oled.text("pressure: {:.1f}".format(preasure), 0, 24)
    oled.text(status, 0, 36)
    oled.text("threshold: {:.1f}".format(threshold), 0, 48)
    oled.show()


def main():
    # I2C
    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100_000)
    
    wifi = network.WLAN(network.STA_IF)

    # kontrola I2C adres 
    adresses = i2c.scan()
    if BME280_ADDRESS not in adresses:
        raise OSError(f"BME280 at {BME280_ADDRESS:#04x} was not detected")
    elif OLED_ADDRESS not in adresses:
        raise OSError(f"OLED at {OLED_ADDRESS:#04x} was not detected")

    # OLED display
    oled = SH1106_I2C(i2c)

    # SENZOR TLAKU/TEPLOTY 
    sensor = BME280(i2c)

    # RELE pro spinani ventilatoru
    relay = Pin(27, Pin.OUT)
    relay.value(0)
    fanStatus = "OFF"

    # Enkoder
    clk = Pin(10, Pin.IN, Pin.PULL_UP)
    dt = Pin(11, Pin.IN, Pin.PULL_UP)  
    sw = Pin(12, Pin.IN, Pin.PULL_UP) 

    threshold = 25 
    step = 0.5  
    last_clk = clk.value()  

    last_read = time.ticks_ms()    
    temperature, humidity, pressure, _ = sensor.read_values()  

    if temperature >= threshold:
        relay.value(1)
        fanStatus = "FAN ON"
    elif temperature <= threshold - FAN_HYSTERESIS:
        relay.value(0)
        fanStatus = "FAN OFF"

    display(oled,temperature, humidity, pressure, fanStatus, threshold)                             
    print("Reading BME280; press Ctrl+C to stop.")


    try:
        while True:
            
            if not wifi.isconnected():
                if not wifi_utils.connect(wifi, config.SSID, config.PSWD):
                    time.sleep(20)
                    continue
            
            # aktualni stav CLK
            now_clk = clk.value()

            #registrujeme zmenu encoderu
            if now_clk != last_clk:
                
                #ked sa zmeni poloha encoderu a knoflik neni zmacknuty ideme do loopu                           
                while sw.value() == 1:
                    #V tomto loope ak detekujeme znovu zmenu polohy encoderu dokym nezmackneme knoflik vtedy sa nam threshold setne a ideme von z loopu                            
                    print("Setting threshold")
                    
                    #aktualny stav clk v loope na detekovanie novej polohy encoderu v loope
                    now_clk = clk.value()
                    
                    if now_clk != last_clk:
                        #bread and butter otacanie encoderu
                        if dt.value() == last_clk:                                          
                            threshold += step                                        
                        else:                                        
                            threshold -= step                                        
                        print(f"Threshold: {threshold:.1f} C")

                    #ulozenie clk na detekovanie
                    last_clk = now_clk

                    #prerusenie loopu
                    if sw.value() == 0:
                        display(oled, temperature, humidity, pressure, "THRESHOLD SET", threshold)       
                        print("Threshold set!")
                        break
            
            #ulozenie clk na detekovanie
            last_clk = now_clk
            

            if sw.value() == 0:                                              # 0 = tlacitko je stisknute
                threshold = 25                                            	 # vratit vychozi hodnotu
                print(f"Threshold reset: {threshold:.1f} C")
                display(oled,temperature, humidity, pressure, "RESET THRESHOLD", threshold)
                time.sleep_ms(300)                   

            # porovnání aktuálního času s posledním čtením, pokud je rozdíl větší než 5s provede se čtení senzoru
            now = time.ticks_ms()
            newReading = time.ticks_diff(now, last_read) >= READ_INTERVAL_MS
            if newReading:
                temperature, humidity, pressure, _ = sensor.read_values()
                last_read = now
                

            # spousteni ventilatoru pres rele s hysterezi 
            if temperature >= threshold:
                relay.value(1)
                fanStatus = "FAN ON"
            elif temperature <= threshold - FAN_HYSTERESIS:
                relay.value(0)
                fanStatus = "FAN OFF"

            if newReading: 
                display(oled,temperature, humidity, pressure, fanStatus, threshold)
                print(
                        f"Temperature: {temperature:.1f} C  "
                        f"Humidity: {humidity:.1f} %  "
                        f"Pressure: {pressure:.1f} hPa"
                    )
                body = (
                     
                        f"api_key={NIEKOHO API KEY}"
                        f"&field1={temperature}"
                        f"&field2={humidity}"
                        f"&field3={pressure}"
                    )
                response = None
                try:
                    response = urequests.post(
                         
                        API_URL,
                        data=body,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                                    )
                except Exception as error:
                                     print("Upload failed:", error)
                finally:
                    if response is not None:
                        response.close()

            


    except KeyboardInterrupt:
        print("\nProgram stopped. Exiting...")
        relay.value(0)
        oled.fill(0)
        oled.show()
    finally:
        wifi_utils.disconnect(wifi)

if __name__ == "__main__":
    main()
