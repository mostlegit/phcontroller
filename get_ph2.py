#!/usr/bin/python
import serial
import time
import json
import lcddriver
import RPi.GPIO as GPIO
import arrow

cycleduration=4
pump_adj_seconds=3
sleep_between_ph_adj=30
display = lcddriver.lcd()

ph_up_gpio = 14
ph_down_gpio = 15

avg_low_goal = 6.0
avg_high_goal = 6.4



def trigger_ph(gpio, seconds=pump_adj_seconds):
    GPIO.setmode(GPIO.BCM)
    print 'Turning on GPIO {} for {} seconds'.format(gpio, seconds)
    GPIO.setup(gpio, GPIO.OUT)
    GPIO.output(gpio, GPIO.LOW)
    time.sleep(seconds)
    GPIO.output(gpio, GPIO.HIGH)
    GPIO.cleanup()
    
def prime_pumps():
    pumps_to_prime = [ph_up_gpio, ph_down_gpio]
    for i in pumps_to_prime: 
        GPIO.setup(i, GPIO.OUT) 
        GPIO.output(i, GPIO.HIGH)
    for i in pumps_to_prime:
        GPIO.output(i, GPIO.LOW)
    time.sleep(10) 
    for i in pumps_to_prime:
        GPIO.output(i, GPIO.HIGH)


def button_check():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    x = 0
    print 'Checking for button inputs'
    while x<3:
        input_state = GPIO.input(24)
        input_state2 = GPIO.input(23)
        if input_state == False and input_state2 == False:
            print 'Both buttons pressed'
            prime_pumps()
        elif input_state == False:
            print('Button Pressed')
        elif input_state2 == False:
            print('Button 2 Pressed')
        time.sleep(0.2)
        x+=1
    GPIO.cleanup()

def get_ph_now(attempt=0):  
    button_check()
    try:
        ser = serial.Serial('/dev/ttyUSB0', 9600)
        rawser = ser.readline().strip()
        while not 'Voltage' in rawser:
            if not 'meter experiment' in rawser:
                print 'No Reading. Trying again'
                time.sleep(.5)
            rawser = ser.readline()
        ph=float(rawser.split(':')[-1].strip())
        voltage=float(rawser.split(':')[1].split(' ')[0].strip())
        print "ph: {}, Voltage: {}".format(ph,voltage)
        display.lcd_display_string("ph: {}".format(ph), 1)
        display.lcd_display_string("Voltage: {}".format(voltage), 2)
        return ph, voltage
    except Exception as exc:
        print 'Attempt {}: Unable to get ph -- {}\nSerial Info:{}'.format(attempt+1, exc,rawser)
        attempt+=1
        get_ph_now(attempt)

def get_ph_average(duration,nextrun,pause=1):
     print 'PH over {} cycles'.format(duration)
     ph_list = []
     for i in range(0,duration):
         ph,voltage = get_ph_now()
         ph_list.append(ph)
         time.sleep(pause)
     avg = sum(ph_list) / len(ph_list)
     print 'Average over the last {} cycles with a pause of {} second(s) between: {}'.format(duration,pause,avg)
     now = arrow.utcnow()
     if now > nextrun:
         if avg < avg_low_goal:
             print "Turning on PH up pump"
             trigger_ph(ph_up_gpio)
             nextrun = arrow.utcnow().replace(seconds=+sleep_between_ph_adj)
             print 'Resetting next PH adjustment to be no earlier than {}'.format(nextrun.format('YYYY-MM-DD HH:mm:ss'))
         if avg > avg_high_goal:
             print "Turning on PH down pump"
             trigger_ph(ph_down_gpio)
             nextrun = arrow.utcnow().replace(seconds=+sleep_between_ph_adj)
             print 'Resetting next PH adjustment to be no earlier than {}'.format(nextrun.format('YYYY-MM-DD HH:mm:ss'))
     else:
         print 'The time : {} is not past the allowed time of the next run: {} which is {} seconds from now'.format(now.format('YYYY-MM-DD HH:mm:ss'),nextrun.format('YYYY-MM-DD HH:mm:ss'), nextrun-now)
     return nextrun


def main():
    nextrun = arrow.utcnow().replace(seconds=+sleep_between_ph_adj)
    try:
        while True:
            nextrun = get_ph_average(cycleduration,nextrun)
    except KeyboardInterrupt: # If there is a KeyboardInterrupt (when you press ctrl+c), exit the program and cleanup
        print("Cleaning up!")
        GPIO.cleanup()
        display.lcd_clear()


if __name__ == "__main__":
    main()
