#!/usr/bin/python
import serial
import time
import json
import lcddriver
import RPi.GPIO as GPIO
import arrow
import ConfigParser

display = lcddriver.lcd()


def get_settings():
    settings = {}
    Config = ConfigParser.ConfigParser()
    Config.read('/home/pi/git/phcontroller/settings.ini')
    settings['pumps_on'] = Config.getfloat('pumps', 'on_time')
    settings['ph_low_range'] = Config.getfloat('ph', 'low_range')
    settings['ph_high_range'] = Config.getfloat('ph', 'high_range')
    settings['cycle_time'] = Config.getint('general', 'cycle_time')
    settings['circ_time'] = Config.getint('general', 'circulate_time')
    settings['sleep_between_adj'] = Config.getfloat('general', 'sleep_between_ph_adj')
    settings['gpio'] = {}
    settings['gpio']['ph_up'] = Config.getint('gpio', 'ph_up')
    settings['gpio']['ph_down'] = Config.getint('gpio', 'ph_down')
    settings['gpio']['menu'] = Config.getint('gpio', 'menu_button')
    settings['gpio']['select'] = Config.getint('gpio', 'select_button')
    settings['gpio']['up_button'] = Config.getint('gpio', 'up_button')
    settings['gpio']['down_button'] = Config.getint('gpio', 'down_button')
    return settings    

def trigger_ph(gpio, seconds, circ_time):
    display.lcd_clear()
    display.lcd_display_string("PH Adjusting" , 1)
    GPIO.setmode(GPIO.BCM)
    print 'Turning on GPIO {} for {} seconds'.format(gpio, seconds)
    GPIO.setup(gpio, GPIO.OUT)
    GPIO.output(gpio, GPIO.LOW)
    time.sleep(seconds)
    GPIO.output(gpio, GPIO.HIGH)
    display.lcd_clear()
    display.lcd_display_string("Circulating" , 1)
    display.lcd_display_string("Be Patient" , 2)
    time.sleep(circ_time)    
    display.lcd_clear()
    GPIO.cleanup()
    
def prime_pumps(settings):
    display.lcd_clear()
    display.lcd_display_string("Priming" , 1)
    display.lcd_display_string("Pumps" , 2)
    try:
        pumps_to_prime = [settings['gpio']['ph_up'], settings['gpio']['ph_down']]
        for i in pumps_to_prime: 
            GPIO.setup(i, GPIO.OUT) 
            GPIO.output(i, GPIO.HIGH)
        for i in pumps_to_prime:
            GPIO.output(i, GPIO.LOW)
        time.sleep(10) 
        for i in pumps_to_prime:
            GPIO.output(i, GPIO.HIGH)
        display.lcd_clear()
        display.lcd_display_string("Please hold" , 1)
        time.sleep(settings['circulate_time'])
        display.lcd_clear()
    except Exception as exc:
        print exc
    display.lcd_clear()


def enter_menu(settings):
    main_menu = ['Prime\nPumps', 'PH Low\nRange', 'PH High\nRange','Exit\nNow']
    display.lcd_clear()
    display.lcd_display_string("Menu" , 1)
    menu_position = 0
    display.lcd_clear()
    while True:
        time.sleep(.2)
        settings = get_settings()
        display.lcd_display_string(main_menu[menu_position].split('\n')[0] , 1)
        display.lcd_display_string(main_menu[menu_position].split('\n')[1] , 2)
        down_button_state = GPIO.input(settings['gpio']['down_button'])
        up_button_state = GPIO.input(settings['gpio']['up_button'])
        select_button_state = GPIO.input(settings['gpio']['select'])
        if down_button_state == False:
            menu_position += 1
            if menu_position  < len(main_menu):
                print 'Going to next menu place'
            else:
                print 'Starting menu over'
                menu_position = 0
            time.sleep(.2)
            display.lcd_clear()
        if up_button_state == False:
            menu_position -= 1
            if menu_position  >= 0:
                print 'Going to next menu place'
            else:
                print 'Starting looping to the end'
                menu_position = len(main_menu) -1
            time.sleep(.2)
        if select_button_state == False:
            if menu_position==0:
                prime_pumps(settings)
            if menu_position==1:
                write_ini('ph','low_range', adj_ph_setting('low',settings))
                time.sleep(.2)
            if menu_position==2:
                write_ini('ph','high_range', adj_ph_setting('high',settings))
                time.sleep(.2)
            if menu_position==len(main_menu)-1:
                return
            else:
                print menu_position
            display.lcd_clear()
        else:
            time.sleep(.1)

def write_ini(section,name,value):
    parser = ConfigParser.ConfigParser()
    parser.read('/home/pi/git/phcontroller/settings.ini')
    parser.set(section, name, value)
    with open('/home/pi/git/phcontroller/settings.ini', 'wb') as configfile:
        parser.write(configfile)

def adj_ph_setting(direction,settings):
    time.sleep(.3)
    display.lcd_clear()
    display.lcd_display_string('Set PH {}'.format(direction) , 1)
    if direction == 'low':
        info = settings['ph_low_range']
    else:
        info = settings['ph_high_range']
    while True:
        down_button_state = GPIO.input(settings['gpio']['down_button'])
        up_button_state = GPIO.input(settings['gpio']['up_button'])
        select_button_state = GPIO.input(settings['gpio']['select'])
        display.lcd_display_string('{}'.format(info) , 2)
        if down_button_state == False:
            info -= .1
            time.sleep(.2)
        if up_button_state == False:
            info += .1
            time.sleep(.2)
        if select_button_state == False:
            print 'Returning info : {}'.format(info)
            return info

def button_check(settings):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(settings['gpio']['select'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(settings['gpio']['menu'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(settings['gpio']['down_button'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(settings['gpio']['up_button'], GPIO.IN, pull_up_down=GPIO.PUD_UP)

    x = 0
    print 'Checking for button inputs'
    while x<3:
        select_button_state = GPIO.input(settings['gpio']['select'])
        menu_button_state = GPIO.input(settings['gpio']['menu'])
        if select_button_state == False and menu_button_state == False:
            print 'Both buttons pressed'
            prime_pumps(settings)
        elif select_button_state == False:
            print('Select Button Pressed')
        elif menu_button_state == False:
            enter_menu(settings)
            print('Menu Button Pressed')
        time.sleep(0.2)
        x+=1
    GPIO.cleanup()

def get_ph_now(settings,attempt=0,):  
    try:
        ser = serial.Serial('/dev/ttyUSB0', 9600)
        rawser = ser.readline().strip()
        button_check(settings)
        while not 'Voltage' in rawser:
            if not 'meter experiment' in rawser:
                print 'No Reading. Trying again'
                time.sleep(.5)
            rawser = ser.readline()
        print rawser
        ph=float(rawser.split(':')[-1].strip())
        voltage=float(rawser.split(':')[-2].split(' ')[1].split('\t')[0])
        print "PH: {}, Voltage: {}".format(ph,voltage)
        display.lcd_display_string("PH: {}".format(ph), 1)
        display.lcd_display_string("Voltage: {}".format(voltage), 2)
        return ph, voltage
    except Exception as exc:
        print 'Attempt {}: Unable to get ph -- {}\nSerial Info:{}'.format(attempt+1, exc,rawser)
        attempt+=1
        get_ph_now(attempt,settings)
        time.sleep(.2)

def get_ph_average(duration,nextrun,settings,pause=1):
     print 'PH over {} cycles'.format(duration)
     ph_list = []
     for i in range(0,duration):
         ph,voltage = get_ph_now(settings)
         ph_list.append(ph)
         time.sleep(pause)
     avg = sum(ph_list) / len(ph_list)
     print 'Average over the last {} cycles with a pause of {} second(s) between: {}'.format(duration,pause,avg)
     now = arrow.utcnow()
     if now > nextrun:
         if avg < settings['ph_low_range']:
             print "Turning on PH up pump"
             trigger_ph(settings['gpio']['ph_up'], settings['pumps_on'],settings['circ_time'])
             nextrun = arrow.utcnow().replace(seconds=+settings['sleep_between_adj'])
             print 'Resetting next PH adjustment to be no earlier than {}'.format(nextrun.format('YYYY-MM-DD HH:mm:ss'))
         if avg > settings['ph_high_range']:
             print "Turning on PH down pump"
             trigger_ph(settings['gpio']['ph_down'], settings['pumps_on'],settings['circ_time'])
             nextrun = arrow.utcnow().replace(seconds=+settings['sleep_between_adj'])
             print 'Resetting next PH adjustment to be no earlier than {}'.format(nextrun.format('YYYY-MM-DD HH:mm:ss'))
     else:
         print 'The time : {} is not past the allowed time of the next run: {} which is {} seconds from now'.format(now.format('YYYY-MM-DD HH:mm:ss'),nextrun.format('YYYY-MM-DD HH:mm:ss'), nextrun-now)
     return nextrun


def main():
    settings = get_settings()
    print settings
    nextrun = arrow.utcnow().replace(seconds=+settings['sleep_between_adj'])
    try:
        while True:
            settings = get_settings()
            nextrun = get_ph_average(settings['cycle_time'],nextrun,settings)
    except KeyboardInterrupt: # If there is a KeyboardInterrupt (when you press ctrl+c), exit the program and cleanup
        print("Cleaning up!")
        GPIO.cleanup()
        display.lcd_clear()


if __name__ == "__main__":
    main()
