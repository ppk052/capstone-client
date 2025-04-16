#라즈베리파이의 GPIO핀을 제어하기위해 필요한 라이브러리
from RPi import GPIO
#데이터를 httprequest를 통해서 보내기 위한 라이브러리
import datetime
import time
import serial
import sys
import websocket
import threading
import json
import spidev
import logging

plant_id = 0
sensor_thread = None
uart = None
server = None
appropriate_moisture = 0.0
appropriate_temperature = 0.0
appropriate_light = 0.0
pump_auto = True
LED_auto = True
fan_auto = True
pump_on = False
led_on = False
fan_on = False
max_land_moisture_value = 1020
min_land_moisture_value = 330
pump_turn_time = 10
fan_turn_time = 60
led_turn_time = 10
led_on_time = 0
fan_on_time = 0
pump_on_time = 0

# 주기적으로 센서데이터 읽고 데이터값 보내는 함수
def read_and_send_sensor_data(frequency, plant_id):
    global pump_auto, LED_auto, fan_auto, appropriate_light, appropriate_moisture, appropriate_temperature, max_land_moisture_value, min_land_moisture_value, pump_turn_time, fan_turn_time, pump_auto, LED_auto, fan_auto, led_turn_time, pump_on, led_on, fan_on, led_on_time, pump_on_time, fan_on_time

    last_sent_time = time.time()  # 마지막 전송 시간 기록
    land_moisture_list = []
    temperature_list = []
    light_list = []

    while True:
        try:
            # UART에서 데이터를 실시간으로 읽음
            data_byte = uart.readline()
            if data_byte:
                data = data_byte.decode('utf-8').strip()
                data_values = data.split(',')[2:]

                if len(data_values) < 3:
                    print("센서데이터가 올바르지 않습니다 : ", data_byte)
                    continue

                # UART로 받은 센서 데이터
                current_moisture = float(data_values[1])
                current_temperature = float(data_values[0])
                current_light = float(data_values[2])

                # 토양 수분 센서 데이터 읽기
                current_land_moisture = read_spi_adc(0)
                current_land_moisture = (max_land_moisture_value - current_land_moisture)/(max_land_moisture_value - min_land_moisture_value) * 100

                # 센서데이터 리스트에 저장및 보정
                if len(light_list) == 5:
                    del land_moisture_list[0]
                    del temperature_list[0]
                    del light_list[0]
                if not 0<current_temperature<40:
                    print("센서데이터보정")
                    result =  sum(temperature_list)
                    current_temperature = result/4
                    print(current_temperature)
                land_moisture_list.append(current_land_moisture)
                temperature_list.append(current_temperature)
                light_list.append(current_light)

                # 주기적으로 5초마다 센서 데이터를 전송
                current_time = time.time()

                #제어시작
                local_time = time.localtime(current_time)

                #라이트
                #라이트가 자동으로 켜지고 일정시간이 지나면 끄고나서 다시 LED 제어
                if led_on:
                    if LED_auto and current_time - led_on_time>led_turn_time:
                        GPIO.output(led_switch,0)
                        message = {
                            "type": 3,
                            "id": plant_id,
                            "name": 'LED',
                            "newState": False
                            }
                        send_message(server, message)
                        led_on = False
                        if 6<local_time.tm_hour<20 and current_light < appropriate_light:
                            GPIO.output(led_switch,1)
                            led_on = True
                            led_on_time = time.time()
                            message = {
                            "type": 3,
                            "id": plant_id,
                            "name": 'LED',
                            "newState": True
                            }
                            send_message(server, message)
                elif LED_auto:
                    if 6<local_time.tm_hour<20 and current_light < appropriate_light:
                        GPIO.output(led_switch,1)
                        led_on = True
                        led_on_time = time.time()
                        message = {
                        "type": 3,
                        "id": plant_id,
                        "name": 'LED',
                        "newState": True
                        }
                        send_message(server, message)

                #팬
                if fan_on:
                    if fan_auto and current_time - fan_on_time > fan_turn_time:
                        GPIO.output(fan_switch,0)
                        fan_on = False
                        message = {
                            "type": 3,
                            "id": plant_id,
                            "name": 'fan',
                            "newState": False
                            }
                        send_message(server, message)
                        if current_temperature > appropriate_temperature:
                            GPIO.output(fan_switch,1)
                            fan_on = True
                            fan_on_time = time.time()
                            message = {
                            "type": 3,
                            "id": plant_id,
                            "name": 'LED',
                            "newState": True
                            }
                            send_message(server, message)
                elif fan_auto:
                    if current_temperature > appropriate_temperature:
                            GPIO.output(fan_switch,1)
                            fan_on = True
                            fan_on_time = time.time()
                            message = {
                            "type": 3,
                            "id": plant_id,
                            "name": 'LED',
                            "newState": True
                            }
                            send_message(server, message)

                #펌프
                if not pump_on or current_time - pump_on_time>pump_turn_time:
                    GPIO.output(pump_switch1,0)
                    GPIO.output(pump_switch2,0)
                    pump_on = False
                    message = {
                        "type": 3,
                        "id": plant_id,
                        "name": 'pump',
                        "newState": False
                        }
                    send_message(server, message)
                    if pump_auto and current_land_moisture<appropriate_moisture:
                        GPIO.output(pump_switch1,1)
                        GPIO.output(pump_switch2,0)
                        pump_on = True
                        pump_on_time = time.time()
                        message = {
                        "type": 3,
                        "id": plant_id,
                        "name": 'LED',
                        "newState": True
                        }
                        send_message(server, message)

                if current_time - last_sent_time >= frequency:
                    # 일정주기가 지나면 센서 데이터를 전송
                    message = {
                        "type": 2,
                        "id": plant_id,
                        "moisture": current_moisture,
                        "temperature": current_temperature,
                        "light": current_light,
                        "landMoisture": current_land_moisture
                    }
                    send_message(server, message)
                    last_sent_time = current_time  # 마지막 전송 시간 갱신

            else:
                time.sleep(0.1)  # 데이터가 없으면 잠시 대기
        except Exception as e:
            print("센서데이터 처리중 오류 : ", e)
            print("센서데이터 : ", data_byte)


#토양수분데이터
def read_spi_adc(adcChannel):
    global spi
    adcValue = 0
    buff = spi.xfer2([1,(8+adcChannel)<<4,0])
    return ((buff[1]&3)<<8)+buff[2]

#메세지받을때
def on_message(ws,message):
    global plant_id, sensor_thread, appropriate_temperature, appropriate_moisture, appropriate_light, pump_auto, LED_auto, fan_auto, led_on_time, pump_on_time, fan_on_time
    try:
        data = json.loads(message)
        print("메세지수신 : ", message)
        if "type" in data:
            #새식물id받을때
            if data['type'] == 0:
                plant_id = data['id']
                appropriate_moisture = data['moisture']
                appropriate_temperature = data['temperature']
                appropriate_light = data['light']
                print("식물id : ", plant_id)
                write_plant_id(plant_id)
                #새 id 받았으니 센서데이터 받기 시작  
                if sensor_thread is None or not sensor_thread.is_alive():          
                    sensor_thread = threading.Thread(target = read_and_send_sensor_data, args=(frequency, plant_id))
                    sensor_thread.daemon = True
                    sensor_thread.start()
            #LED수동제어
            elif data['type'] == 1:
                if data['switch'] == True:
                    GPIO.output(led_switch,1)
                    led_on_time = time.time()
                    print("LED ON")
                else:
                    GPIO.output(led_switch,0)
                    print("LED OFF")
            #펌프수동제어
            elif data['type'] ==2:
                if data['switch'] == True:
                    GPIO.output(pump_switch1,1)
                    GPIO.output(pump_switch2,0)
                    pump_on_time = time.time()
                    print("펌프 ON")
                else:
                    GPIO.output(pump_switch1,0)
                    GPIO.output(pump_switch2,0)
                    print("펌프 OFF")
            #fan수동제어
            elif data['type']==4:
                if data['switch'] == True:
                    GPIO.output(fan_switch,1)
                    fan_on_time=time.time()
                    print("fan ON")
                else:
                    GPIO.output(fan_switch,0)
                    print("fan Off")
            #자동모드제어
            elif data['type']==5:
                if data['switch'] == True:
                    if data['device'] == 'pump':
                        pump_auto = True
                        print(pump_auto)
                    elif data['device'] == 'LED':
                        LED_auto = True
                        print(LED_auto)
                    elif data['device'] == 'fan':
                        fan_auto = True
                        print(fan_auto)
                elif data['switch'] == False:
                    if data['device'] == 'pump':
                        pump_auto = False
                        print(pump_auto)
                    elif data['device'] == 'LED':
                        LED_auto = False
                        print(LED_auto)
                    elif data['device'] == 'fan':
                        fan_auto = False
                        print(fan_auto)
                        
            #plantid를 보내서 식별완료
            elif data['type'] == 3:
                appropriate_moisture = data['moisture']
                appropriate_temperature = data['temperature']
                appropriate_light = data['light']
                #식물id식별왼료했으니까 센서데이터 받기 시작            
                if sensor_thread is None or not sensor_thread.is_alive():          
                    sensor_thread = threading.Thread(target = read_and_send_sensor_data, args=(frequency, plant_id))
                    sensor_thread.daemon = True
                    sensor_thread.start()
        else:
            print("메세지타입이 없습니다!")
    except json.JSONDecodeError:
        print("받은메세지가 JSON형식이 아닙니다")
    
    
#메세지전송
def send_message(ws,message):
    json_message = json.dumps(message)
    ws.send(json_message)

#웹소켓연결됐을때
def on_open(ws):
    global server, plant_id
    print("웹소켓연결완료")
    server = ws
    #식물id가져오기
    plant_id = load_plant_id()
    if plant_id is None:
        message = {
            "type" : 0,
            "name": sys.argv[3],
            "plantType" : sys.argv[4]
        }
    else:
        message = {
            "type" : 1,
            "id" : plant_id
        }
    send_message(ws,message)
    
#웹소켓연결끊겼을때
def on_close(Ws, close_status_code, close_msg):
    print("웹소켓연결종료됨")

#웹소켓오류일때
def on_error(ws, error):
    print("웹소켓오류 : ",error)

#웹소켓 연결하기
def connect_to_websocket(url):
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(url, on_message = on_message, on_error = on_error, on_close = on_close, on_open = on_open)
    ws.run_forever()

#파일불러오기
def load_plant_id():
    try:
        with open('plant_id.txt', 'r') as file:
            return int(file.read())
    except FileNotFoundError : 
        return None

#파일저장하기
def write_plant_id(id):
    with open('plant_id.txt', 'w') as file:
        file.write(str(id))

#입력데이터 : 센서주기, 웹소켓주소
if len(sys.argv)<9:
    print("Error : 센서데이터 전송주기, URL, 식물이름, 식물종류, LED제어핀번호, 팬제어핀번호, 펌프제어핀번호1, 펌프제어핀번호2를 입력해주세요")
    sys.exit(1)
else :
    frequency = int(sys.argv[1])
    url = sys.argv[2]
    led_switch = int(sys.argv[5])
    fan_switch = int(sys.argv[6])
    pump_switch1 = int(sys.argv[7])
    pump_switch2 = int(sys.argv[8])
    
#ToDo:센서값을 기준으로 화분자동제어
def manipulate_plant():
    return None

#UART설정
uart = serial.Serial(port='/dev/ttyAMA0',baudrate=9600,parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)

#토양센서설정
spi=spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz=50000

#GPIO핀 설정
GPIO.setmode(GPIO.BCM)

#GPIO핀 I/O설정 및 기본 출력 0설정
GPIO.setup(led_switch, GPIO.OUT)
GPIO.output(led_switch,0)
GPIO.setup(pump_switch1,GPIO.OUT)
GPIO.output(pump_switch1,0)
GPIO.setup(pump_switch2,GPIO.OUT)
GPIO.output(pump_switch2,0)
GPIO.setup(fan_switch,GPIO.OUT)
GPIO.output(fan_switch,0)

#웹소켓설정 및 연결
websocket.enableTrace(False)
logging.basicConfig(level=logging.ERROR)
websocket_thread = threading.Thread(target=connect_to_websocket, args=(url,))
websocket_thread.start()
