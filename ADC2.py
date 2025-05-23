# -*- coding: utf-8 -*-
import time
import spidev

delay =0.5
pot_channel=0
spi=spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz=100000

def readadc(adcnum):
	if adcnum > 7 or adcnum < 0:
		return -1
	r = spi.xfer([1,8+adcnum<<4,0])
	data=((r[1]&3)<<8)+r[2]
	return data
	
while True:
	
	pot_value = readadc(pot_channel)
	print("=====")
	print("POT Value: %d" % pot_value)
	time.sleep(delay)

