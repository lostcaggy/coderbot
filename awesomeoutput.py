import time
import pigpio
import logging

class Awesomeoutput:
   """
   ound trip time.
   """

   def __init__(self, pi):
      """
      The class is instantiated with the Pi to use and the
      gpios connected to the trigger and echo pins.
      """
      self.pi = pi


   def ledOutput(self, awesome_led, LED_State):
       self.pi.set_mode(awesome_led, pigpio.OUTPUT)
       self.pi.write(awesome_led, LED_State)
