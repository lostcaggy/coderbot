import time
import pigpio
import logging

class Awesomeinput:
   """
   ound trip time.
   """

   def __init__(self, pi, linesensorpin):
      """
      The class is instantiated with the Pi to use and the
      gpios connected to the trigger and echo pins.
      """
      self.pi = pi
      self._linesensorpin = linesensorpin
      pi.set_mode(self._linesensorpin, pigpio.INPUT)
      self._inited = True

   def buttonInput(self, awesome_button):
       self.pi.set_mode(awesome_button, pigpio.INPUT)
       self.pi.set_pull_up_down(awesome_button, pigpio.PUD_UP)
       print "Button pin:" + str(awesome_button)
       print "Button reads: " + str(self.pi.read(awesome_button))
       if self.pi.read(awesome_button) == 1:
           return False
       else:
           return True

   def lineSensor(self):
       if self._inited:
           if self.pi.read(self._linesensorpin) == 1:
               return False
           else:
               return True
