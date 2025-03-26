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

plant_id = 0
sensor_thread = None
uart = None
server = None

#주기적으로 센서데이터 읽고 데이터값 보내는 함수
def read_and_send_sonsor_data(frequency,plant_id):
    while True:
        try:

            data_byte = uart.readline()
            data = data_byte.decode('utf-8').strip()
            data_values = data.split(',')[2:]
            if len(data_values) < 3:
                print("센서데이터가 올바르지 않습니다 : ", data_byte)
                continue
            current_moisture = float(data_values[0])
            current_temperature = float(data_values[1])
            current_light = float(data_values[2])
            #ToDo : 토양수분센서, 데이터 보정
            current_land_moisture = float(0)
            
            message = {
                "type" : 2,
                "id" : plant_id,
                "moisture" : current_moisture,
                "temperature" : current_temperature,
                "light" : current_light,
                "landMoisture" : current_land_moisture
            }
            send_message(server,message)
            time.sleep(frequency)
        except Exception as e:
            print("센서데이터 처리중 오류 : ", e)
            print("센서데이터 : ", data_byte)

#메세지받을때
def on_message(ws,message):
    global plant_id, sensor_thread
    try:
        data = json.loads(message)
        print("메세지수신 : ", message)
        if "type" in data:
            #새식물id받을때
            if data['type'] == 0:
                plant_id = data['id']
                appropriate_moisture = data['appropriateMoisture']
                appropriate_temperature = data['appropriateTemperature']
                appropriate_light = data['appropriateLight']
                print("식물id : ", plant_id)
                write_plant_id(plant_id)
                #새 id 받았으니 센서데이터 받기 시작  
                if sensor_thread is None or not sensor_thread.is_alive():          
                    sensor_thread = threading.Thread(target = read_and_send_sonsor_data, args=(frequency, plant_id))
                    sensor_thread.daemon = True
                    sensor_thread.start()
            #LED수동제어
            elif data['type'] == 1:
                if data['switch'] == True:
                    GPIO.output(led_switch,1)
                    print("LED ON")
                else:
                    GPIO.output(led_switch,0)
                    print("LED OFF")
            #펌프수동제어
            elif data['type'] ==2:
                if data['switch'] == True:
                    GPIO.output(pump_switch,1)
                    print("펌프 ON")
                else:
                    GPIO.output(pump_switch,0)
                    print("펌프 OFF")
            #plantid를 보내서 식별완료
            elif data['type'] == 3:
                #식물id식별왼료했으니까 센서데이터 받기 시작            
                if sensor_thread is None or not sensor_thread.is_alive():          
                    sensor_thread = threading.Thread(target = read_and_send_sonsor_data, args=(ws, frequency, plant_id))
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
    if(plant_id == None):
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
if len(sys.argv)<7:
    print("Error : 센서데이터 전송주기, URL, 식물이름, 식물종류, LED제어핀번호, 물펌프제어핀번호를 입력해주세요")
    sys.exit(1)
else :
    frequency = int(sys.argv[1])
    url = sys.argv[2]
    led_switch = int(sys.argv[5])
    pump_switch = int(sys.argv[6])
    
#ToDo:센서값을 기준으로 화분자동제어
def manipulate_plant():
    return None

#UART설정
uart = serial.Serial(port='/dev/ttyAMA0',baudrate=9600,parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)

#GPIO핀 설정
GPIO.setmode(GPIO.BCM)

#GPIO핀 I/O설정 및 기본 출력 0설정
GPIO.setup(led_switch, GPIO.OUT)
GPIO.output(led_switch,0)
GPIO.setup(pump_switch,GPIO.OUT)
GPIO.output(pump_switch,0)

#웹소켓설정 및 연결
websocket_thread = threading.Thread(target=connect_to_websocket, args=(url,))
websocket_thread.start()
