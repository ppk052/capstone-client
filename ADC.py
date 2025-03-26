import spidev
import time

delay = 1 

# Open Spi Bus
# SPI 버스 0과 디바이스 0을 열고
# 최대 전송 속도를 1MHz로 설정
spi = spidev.SpiDev()
spi.open(0,0) # open(bus, device)
spi.max_speed_hz = 1000000 # set transfer speed

# To read SPI data from MCP3008 chip
# Channel must be 0~7 integer
def readChannel(channel): 
  val = spi.xfer2([1, (8+channel)<<4, 0])
  data = ((val[1]&3) << 8) + val[2]
  return data

# 0~1023 value가 들어옴. 1023이 수분함량 min값
def convertPercent(data):
  return 100.0-round(((data*100)/float(1023)),1)

try:
  while True:
    val = readChannel(0)
    if (val != 0) : # filtering for meaningless num
      print(val, "/", convertPercent(val),"%")
    time.sleep(delay)
except KeyboardInterrupt:
  spi.close()
  print("Keyboard Interrupt!!!!")