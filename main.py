from machine import I2C, Pin
from bme280 import BME280
from sh1106 import SH1106_I2C
from micropython import const
import time

# KONSTANY
# nastavení periody čtení BM280 čidla
READ_INTERVAL_MS = const(5000)  
# řízení hystereze ventilátoru 
FAN_HYSTERESIS = const(0.5)
# adresy I2C periferii 
BME280_ADDRESS = const(0x76)
OLED_ADDRESS = const(0x3C)

def display(oled,temperature, humidity, preasure, status, threshold):
    oled.fill(0)
    oled.text("temp: {:.1f}".format(temperature), 0, 0)
    oled.text("humidity: {:.1f}".format(humidity), 0, 12)
    oled.text("pressure: {:.1f}".format(preasure), 0, 24)
    oled.text(status, 0, 36)
    oled.text("limit: {:.1f}".format(threshold), 0, 48)
    oled.show()


def main():
    # I2C
    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100_000)

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

    threshold = 25.3 
    step = 0.5  
    last_clk = clk.value()  

    last_read = time.ticks_ms()    
    temperature, humidity, pressure, _ = sensor.read_values()  

    if temperature >= threshold:
        relay.value(1)
        fanStatus = "ON"
    elif temperature <= threshold - FAN_HYSTERESIS:
        relay.value(0)
        fanStatus = "OFF"

    display(oled,temperature, humidity, pressure, fanStatus, threshold)                             
    print("Reading BME280; press Ctrl+C to stop.")


    try:
        while True:
            # aktualni stav CLK
            now_clk = clk.value()    

            if now_clk != last_clk and now_clk == 0:                         # CLK se zmenil a klesl na 0 = jeden step
                if dt.value() == 1:                                          # DT = 1 -> otaceno jednim smerem
                    threshold += step                                        # prah nahoru
                else:                                                        # DT = 0 -> otaceno druhym smerem
                    threshold -= step                                        # prah dolu
                print(f"Threshold: {threshold:.1f} C")
                display(oled, temperature, humidity, pressure, "THRESHOLD SET", threshold)      # přepsání displeje 
            last_clk = now_clk                                                                  # pamatování stavu 
                                                                         
            if sw.value() == 0:                                              # 0 = tlacitko je stisknute
                threshold = 25.3                                             # vratit vychozi hodnotu
                print(f"Threshold reset: {threshold:.1f} C")
                display(oled,temperature, humidity, pressure, "RESET", threshold)
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
                fanStatus = "ON"
            elif temperature <= threshold - FAN_HYSTERESIS:
                relay.value(0)
                fanStatus = "OFF"

            if newReading: 
                display(oled,temperature, humidity, pressure, fanStatus, threshold)
                print(
                        f"Temperature: {temperature:.1f} C  "
                        f"Humidity: {humidity:.1f} %  "
                        f"Pressure: {pressure:.1f} hPa"
                    )

            time.sleep_ms(2)


    except KeyboardInterrupt:
        print("\nProgram stopped. Exiting...")
        relay.value(0)
        oled.fill(0)
        oled.show()


if __name__ == "__main__":
    main()
