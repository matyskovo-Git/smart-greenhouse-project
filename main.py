from machine import I2C, Pin
from bme280 import BME280
from sh1106 import SH1106_I2C
import time

def display(temperature, humidity, preasure, status):
    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100_000)
    oled = SH1106_I2C(i2c)

    oled.fill(0)
    oled.text("temp: {:.1f}".format(temperature), 0, 0)
    oled.text("humidity: {:.1f}".format(humidity), 0, 12)
    oled.text("pressure: {:.1f}".format(preasure), 0, 24)
    oled.text(status, 0, 36)
    oled.show()


def main():
    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100_000)
    address = 0x76
    relay = Pin(27, Pin.OUT)

    if address not in i2c.scan():
        raise OSError(f"BME280 at {address:#04x} was not detected")

    sensor = BME280(i2c)
    print("Reading BME280; press Ctrl+C to stop.")

    try:
        while True:
            temperature, humidity, pressure, _ = sensor.read_values()
            print(
                f"Temperature: {temperature:.1f} C  "
                f"Humidity: {humidity:.1f} %  "
                f"Pressure: {pressure:.1f} hPa"
            )
            display(temperature,humidity,pressure,"ON")
            if temperature >= 25.3:
                relay.value(1)
            else:
                relay.value(0)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nProgram stopped. Exiting...")
        relay.value(0)


if __name__ == "__main__":
    main()