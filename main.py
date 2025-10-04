import network
import urequests as requests
import ujson as json
import time
from machine import Pin, I2C
import gc

# WiFi Configuration - MODIFY THESE
WIFI_SSID = "YOUR_SSID"
WIFI_PASSWORD = "YOUR_PASSWORD"

# I2C Configuration for Raspberry Pi Pico
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)

class SSH1106:
    """Driver for SSH1106 OLED display 128x64"""
    
    def __init__(self, i2c, addr=0x3C):
        self.i2c = i2c
        self.addr = addr
        self.width = 128
        self.height = 64
        self.pages = 8
        self.buffer = bytearray(self.width * self.pages)
        self.init_display()
    
    def write_cmd(self, cmd):
        """Send command to display"""
        self.i2c.writeto(self.addr, bytes([0x00, cmd]))
    
    def write_data(self, data):
        """Send data to display"""
        self.i2c.writeto(self.addr, bytes([0x40]) + data)
    
    def init_display(self):
        """Initialize SSH1106 display with 180° rotation"""
        commands = [
            0xAE, 0x02, 0x10, 0x40, 0x81, 0xA1, 0xC8, 0xA6,
            0xA8, 0x3F, 0xF0, 0x00, 0xD5, 0x80, 0xD9, 0x22,
            0xDA, 0x12, 0xDB, 0x20, 0x20, 0x02, 0xA4, 0xA6, 0xAF
        ]
        for cmd in commands:
            self.write_cmd(cmd)
    
    def fill(self, color):
        """Fill entire screen with color (0=black, 1=white)"""
        fill_byte = 0xFF if color else 0x00
        for i in range(len(self.buffer)):
            self.buffer[i] = fill_byte
    
    def pixel(self, x, y, color):
        """Set a single pixel"""
        if 0 <= x < self.width and 0 <= y < self.height:
            page = y // 8
            bit = y % 8
            index = x + page * self.width
            if color:
                self.buffer[index] |= (1 << bit)
            else:
                self.buffer[index] &= ~(1 << bit)
    
    def text_simple(self, text, x, y):
        """Display text using 6x8 font"""
        font = {
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            '0': [0x3E, 0x51, 0x49, 0x45, 0x3E, 0x00],
            '1': [0x00, 0x42, 0x7F, 0x40, 0x00, 0x00],
            '2': [0x42, 0x61, 0x51, 0x49, 0x46, 0x00],
            '3': [0x21, 0x41, 0x45, 0x4B, 0x31, 0x00],
            '4': [0x18, 0x14, 0x12, 0x7F, 0x10, 0x00],
            '5': [0x27, 0x45, 0x45, 0x45, 0x39, 0x00],
            '6': [0x3C, 0x4A, 0x49, 0x49, 0x30, 0x00],
            '7': [0x01, 0x71, 0x09, 0x05, 0x03, 0x00],
            '8': [0x36, 0x49, 0x49, 0x49, 0x36, 0x00],
            '9': [0x06, 0x49, 0x49, 0x29, 0x1E, 0x00],
            'A': [0x7E, 0x11, 0x11, 0x11, 0x7E, 0x00],
            'B': [0x7F, 0x49, 0x49, 0x49, 0x36, 0x00],
            'C': [0x3E, 0x41, 0x41, 0x41, 0x22, 0x00],
            'D': [0x7F, 0x41, 0x41, 0x22, 0x1C, 0x00],
            'E': [0x7F, 0x49, 0x49, 0x49, 0x41, 0x00],
            'F': [0x7F, 0x09, 0x09, 0x09, 0x01, 0x00],
            'G': [0x3E, 0x41, 0x49, 0x49, 0x7A, 0x00],
            'H': [0x7F, 0x08, 0x08, 0x08, 0x7F, 0x00],
            'I': [0x00, 0x41, 0x7F, 0x41, 0x00, 0x00],
            'L': [0x7F, 0x40, 0x40, 0x40, 0x40, 0x00],
            'M': [0x7F, 0x02, 0x04, 0x02, 0x7F, 0x00],
            'N': [0x7F, 0x04, 0x08, 0x10, 0x7F, 0x00],
            'O': [0x3E, 0x41, 0x41, 0x41, 0x3E, 0x00],
            'P': [0x7F, 0x09, 0x09, 0x09, 0x06, 0x00],
            'Q': [0x3E, 0x41, 0x51, 0x21, 0x5E, 0x00],
            'R': [0x7F, 0x09, 0x19, 0x29, 0x46, 0x00],
            'S': [0x46, 0x49, 0x49, 0x49, 0x31, 0x00],
            'T': [0x01, 0x01, 0x7F, 0x01, 0x01, 0x00],
            'U': [0x3F, 0x40, 0x40, 0x40, 0x3F, 0x00],
            'V': [0x1F, 0x20, 0x40, 0x20, 0x1F, 0x00],
            'W': [0x3F, 0x40, 0x38, 0x40, 0x3F, 0x00],
            'X': [0x63, 0x14, 0x08, 0x14, 0x63, 0x00],
            'Y': [0x07, 0x08, 0x70, 0x08, 0x07, 0x00],
            'Z': [0x61, 0x51, 0x49, 0x45, 0x43, 0x00],
            'a': [0x20, 0x54, 0x54, 0x54, 0x78, 0x00],
            'b': [0x7F, 0x48, 0x44, 0x44, 0x38, 0x00],
            'c': [0x38, 0x44, 0x44, 0x44, 0x20, 0x00],
            'd': [0x38, 0x44, 0x44, 0x48, 0x7F, 0x00],
            'e': [0x38, 0x54, 0x54, 0x54, 0x18, 0x00],
            'f': [0x08, 0x7E, 0x09, 0x01, 0x02, 0x00],
            'g': [0x0C, 0x52, 0x52, 0x52, 0x3E, 0x00],
            'h': [0x7F, 0x08, 0x04, 0x04, 0x78, 0x00],
            'i': [0x00, 0x44, 0x7D, 0x40, 0x00, 0x00],
            'l': [0x00, 0x41, 0x7F, 0x40, 0x00, 0x00],
            'm': [0x7C, 0x04, 0x18, 0x04, 0x78, 0x00],
            'n': [0x7C, 0x08, 0x04, 0x04, 0x78, 0x00],
            'o': [0x38, 0x44, 0x44, 0x44, 0x38, 0x00],
            'p': [0x7C, 0x14, 0x14, 0x14, 0x08, 0x00],
            'q': [0x08, 0x14, 0x14, 0x18, 0x7C, 0x00],
            'r': [0x7C, 0x08, 0x04, 0x04, 0x08, 0x00],
            's': [0x48, 0x54, 0x54, 0x54, 0x20, 0x00],
            't': [0x04, 0x3F, 0x44, 0x40, 0x20, 0x00],
            'u': [0x3C, 0x40, 0x40, 0x20, 0x7C, 0x00],
            'v': [0x1C, 0x20, 0x40, 0x20, 0x1C, 0x00],
            'w': [0x3C, 0x40, 0x30, 0x40, 0x3C, 0x00],
            'x': [0x44, 0x28, 0x10, 0x28, 0x44, 0x00],
            'y': [0x0C, 0x50, 0x50, 0x50, 0x3C, 0x00],
            'z': [0x44, 0x64, 0x54, 0x4C, 0x44, 0x00],
            ':': [0x00, 0x36, 0x36, 0x00, 0x00, 0x00],
            '.': [0x00, 0x60, 0x60, 0x00, 0x00, 0x00],
            '-': [0x08, 0x08, 0x08, 0x08, 0x08, 0x00],
            '/': [0x60, 0x30, 0x18, 0x0C, 0x06, 0x03],
            '%': [0x46, 0x26, 0x10, 0x08, 0x64, 0x62],
        }
        
        char_x = x
        for char in text:
            if char in font:
                char_data = font[char]
                for col in range(6):
                    for row in range(8):
                        if char_data[col] & (1 << row):
                            self.pixel(char_x + col, y + row, 1)
                char_x += 7
    
    def line(self, x0, y0, x1, y1, color):
        """Draw a line between two points"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2
        
        while True:
            self.pixel(x, y, color)
            if x == x1 and y == y1:
                break
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
    
    def show(self):
        """Update display with buffer content (180° rotation)"""
        for page in range(self.pages):
            self.write_cmd(0xB0 + page)
            self.write_cmd(0x02)
            self.write_cmd(0x10)
            
            start = page * self.width
            end = start + self.width
            page_data = self.buffer[start:end]
            reversed_data = bytes(reversed(page_data))
            
            self.write_data(reversed_data)

def connect_wifi():
    """Connect to WiFi with multiple attempts"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("Already connected to WiFi")
        return True
    
    print(f"Connecting to {WIFI_SSID}...")
    
    max_attempts = 3
    for attempt in range(max_attempts):
        print(f"Attempt {attempt + 1}/{max_attempts}")
        
        try:
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            timeout = 20
            while timeout > 0:
                if wlan.isconnected():
                    print(f"WiFi connected: {wlan.ifconfig()[0]}")
                    return True
                
                time.sleep(1)
                timeout -= 1
            
            wlan.disconnect()
            time.sleep(2)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
    
    return False

def get_weather_data():
    """Fetch weather data for Paris (Open-Meteo - free API)"""
    try:
        # Open-Meteo API (no API key needed)
        # Paris: lat=48.8566, lon=2.3522
        url = "https://api.open-meteo.com/v1/forecast?latitude=48.8566&longitude=2.3522&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=Europe/Paris"
        
        print("Fetching Paris weather...")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            response.close()
            gc.collect()
            
            current = data.get('current', {})
            print(f"Temperature: {current.get('temperature_2m')}C")
            return current
        else:
            print(f"Weather error: {response.status_code}")
            response.close()
            return None
            
    except Exception as e:
        print(f"Weather error: {e}")
        return None

def get_air_quality():
    """Fetch air quality data for Paris"""
    try:
        # Open-Meteo Air Quality API
        url = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=48.8566&longitude=2.3522&current=pm10,pm2_5,european_aqi"
        
        print("Fetching Paris air quality...")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            response.close()
            gc.collect()
            
            current = data.get('current', {})
            print(f"AQI: {current.get('european_aqi')}")
            return current
        else:
            print(f"Air quality error: {response.status_code}")
            response.close()
            return None
            
    except Exception as e:
        print(f"Air quality error: {e}")
        return None

def weather_code_to_text(code):
    """Convert weather code to text description"""
    codes = {
        0: "Clear", 1: "Mostly clear", 2: "Cloudy", 3: "Overcast",
        45: "Fog", 48: "Frost",
        51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
        61: "Rain", 63: "Rain", 65: "Heavy rain",
        71: "Snow", 73: "Snow", 75: "Heavy snow",
        80: "Showers", 81: "Showers", 82: "Showers",
        95: "Thunderstorm", 96: "Thunderstorm", 99: "Heavy storm"
    }
    return codes.get(code, "Variable")

def aqi_to_quality(aqi):
    """Convert AQI index to quality level"""
    if aqi is None:
        return "Unknown"
    if aqi <= 20:
        return "Excellent"
    elif aqi <= 40:
        return "Good"
    elif aqi <= 60:
        return "Moderate"
    elif aqi <= 80:
        return "Poor"
    else:
        return "Very poor"

def display_info(oled, weather, air_quality):
    """Display weather information on OLED screen"""
    try:
        oled.fill(0)
        
        # Title
        oled.text_simple("PARIS WEATHER", 10, 0)
        oled.line(0, 10, 127, 10, 1)
        
        y_pos = 12
        
        # Temperature and weather
        if weather:
            temp = weather.get('temperature_2m', 'N/A')
            humidity = weather.get('relative_humidity_2m', 'N/A')
            wind = weather.get('wind_speed_10m', 'N/A')
            w_code = weather.get('weather_code', 0)
            
            oled.text_simple(f"T: {temp}C  H: {humidity}%", 0, y_pos)
            y_pos += 10
            
            oled.text_simple(f"Wind: {wind} km/h", 0, y_pos)
            y_pos += 10
            
            weather_text = weather_code_to_text(w_code)
            oled.text_simple(weather_text, 0, y_pos)
            y_pos += 10
        else:
            oled.text_simple("Weather N/A", 0, y_pos)
            y_pos += 20
        
        # Separator line
        oled.line(0, y_pos, 127, y_pos, 1)
        y_pos += 3
        
        # Air quality (compact format)
        if air_quality:
            aqi = air_quality.get('european_aqi')
            pm25 = air_quality.get('pm2_5', 'N/A')
            
            quality = aqi_to_quality(aqi)
            
            # Display on 2 compact lines
            oled.text_simple(f"Air: {quality}", 0, y_pos)
            y_pos += 9
            oled.text_simple(f"PM2.5: {pm25}", 0, y_pos)
        else:
            oled.text_simple("Air N/A", 0, y_pos)
        
        # Time at bottom (fixed position)
        t = time.localtime()
        time_str = f"{t[3]:02d}:{t[4]:02d}"
        oled.text_simple(time_str, 85, 54)
        
        oled.show()
        print("Display updated")
        
    except Exception as e:
        print(f"Display error: {e}")

def main():
    """Main program"""
    print("=== Paris Weather & Air Quality Display ===")
    print(f"Free memory: {gc.mem_free()} bytes")
    
    # Initialize OLED display
    try:
        oled = SSH1106(i2c)
        print("OLED display OK")
    except Exception as e:
        print(f"OLED error: {e}")
        return
    
    # Startup screen
    oled.fill(0)
    oled.text_simple("STARTING...", 25, 20)
    oled.text_simple("WiFi connect", 15, 35)
    oled.show()
    
    # Connect to WiFi
    if not connect_wifi():
        oled.fill(0)
        oled.text_simple("WIFI ERROR", 25, 20)
        oled.text_simple("Check config", 15, 35)
        oled.show()
        return
    
    oled.fill(0)
    oled.text_simple("WIFI OK", 40, 25)
    oled.show()
    time.sleep(2)
    
    # Main loop
    while True:
        try:
            print(f"\n--- Update ---")
            
            # Loading screen
            oled.fill(0)
            oled.text_simple("LOADING...", 25, 25)
            oled.show()
            
            gc.collect()
            
            # Fetch data
            weather = get_weather_data()
            air_quality = get_air_quality()
            
            # Display
            display_info(oled, weather, air_quality)
            
            print(f"Memory: {gc.mem_free()} bytes")
            
            # Wait 5 minutes (300 seconds)
            time.sleep(300)
            
        except KeyboardInterrupt:
            print("\nStopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            oled.fill(0)
            oled.text_simple("ERROR", 40, 25)
            oled.show()
            time.sleep(60)
            gc.collect()
    
    oled.fill(0)
    oled.text_simple("STOPPED", 35, 25)
    oled.show()

if __name__ == "__main__":
    main()
