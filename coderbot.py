############################################################################
#    CoderBot, a didactical programmable robot.
#    Copyright (C) 2014, 2015 Roberto Previtera <info@coderbot.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
############################################################################

import os
import time
import pigpio
import config
import logging
import sonar
import awesomeoutput
import awesomeinput


PIN_MOTOR_ENABLE = 22
PIN_LEFT_FORWARD = 8
PIN_LEFT_BACKWARD = 7
PIN_RIGHT_FORWARD = 10
PIN_RIGHT_BACKWARD = 9
PIN_PUSHBUTTON = 11
#PIN_SERVO_3 = 9
#PIN_SERVO_4 = 10
PIN_SONAR_1_TRIGGER = 17
PIN_SONAR_1_ECHO = 18

PWM_FREQUENCY = 100 #Hz
PWM_RANGE = 100 #0-100

PIN_LINE_SENSOR = 25

#OUTPUT_LED = 1
#PIN_LED = 24

def coderbot_callback(gpio, level, tick):
  return CoderBot.get_instance().callback(gpio, level, tick)

class CoderBot:
  _pin_out = [PIN_MOTOR_ENABLE, PIN_LEFT_FORWARD, PIN_RIGHT_FORWARD, PIN_LEFT_BACKWARD, PIN_RIGHT_BACKWARD]

  def __init__(self, servo=False, motor_trim_factor=1.0):
    self.pi = pigpio.pi('localhost')
    self.pi.set_mode(PIN_PUSHBUTTON, pigpio.INPUT)
#    self.pi.set_mode(PIN_ENCODER_LEFT, pigpio.INPUT)
#    self.pi.set_mode(PIN_ENCODER_RIGHT, pigpio.INPUT)
    self._cb = dict()
    self._cb_last_tick = dict()
    self._cb_elapse = dict()
    self._servo = servo
    self._motor_trim_factor = motor_trim_factor
    if self._servo:
      self.motor_control = self._servo_motor
    else:
      self.motor_control = self._dc_motor
    self._cb1 = self.pi.callback(PIN_PUSHBUTTON, pigpio.EITHER_EDGE, coderbot_callback)
    for pin in self._pin_out:
      self.pi.set_PWM_frequency(pin, PWM_FREQUENCY)
      self.pi.set_PWM_range(pin, PWM_RANGE)

    self.stop()
    self._is_moving = False
    self.sonar = [sonar.Sonar(self.pi, PIN_SONAR_1_TRIGGER, PIN_SONAR_1_ECHO)]
    self.awesomeoutput = awesomeoutput.Awesomeoutput(self.pi)
    self.awesomeinput = awesomeinput.Awesomeinput(self.pi, PIN_LINE_SENSOR)
    self._encoder_cur_left = 0
    self._encoder_cur_right = 0
    self._encoder_target_left = -1
    self._encoder_target_right = -1
  the_bot = None

  def exit(self):
    self._cb1.cancel()
#    self._cb2.cancel()
#    self._cb3.cancel()
    for s in self.sonar:
      s.cancel()

  @classmethod
  def get_instance(cls, servo=False, motor_trim_factor=1.0):
    if not cls.the_bot:
      cls.the_bot = CoderBot(servo, motor_trim_factor)
    return cls.the_bot

  def move(self, speed=100, elapse=-1):
    self.motor_control(speed_left=min(100, max(-100, speed * self._motor_trim_factor)), speed_right=min(100, max(-100, speed / self._motor_trim_factor)), elapse=elapse)

  def turn(self, speed=100, elapse=-1):
    self.motor_control(speed_left=min(100, max(-100, speed / self._motor_trim_factor)), speed_right=-min(100, max(-100, speed * self._motor_trim_factor)), elapse=elapse)

  def forward(self, speed=100, elapse=-1):
    self.move(speed=speed, elapse=elapse)

  def backward(self, speed=100, elapse=-1):
    self.move(speed=-speed, elapse=elapse)

  def left(self, speed=100, elapse=-1):
    self.turn(speed=-speed, elapse=elapse)

  def right(self, speed=100, elapse=-1):
    self.turn(speed=speed, elapse=elapse)

  def servo3(self, angle):
    self._servo_control(PIN_SERVO_3, angle)

  def servo4(self, angle):
    self._servo_control(PIN_SERVO_4, angle)

  def get_sonar_distance(self, sonar_id=0):
    return self.sonar[sonar_id].get_distance()

  def ledOutput(self, pin_led, output_led):
    self.awesomeoutput.ledOutput(pin_led, output_led)

  def buttonInput(self, pin_button):
    return self.awesomeinput.buttonInput(pin_button)

  def lineSensor(self):
    return self.awesomeinput.lineSensor()

  def _dc_motor(self, speed_left=100, speed_right=100, elapse=-1, steps_left=-1, steps_right=-1 ):
    self._encoder_cur_left = 0
    self._encoder_cur_right = 0
    self._encoder_target_left = steps_left
    self._encoder_target_right = steps_right

    self._is_moving = True
    if speed_left < 0:
      speed_left = abs(speed_left)
      self.pi.write(PIN_LEFT_FORWARD, 0)
      self.pi.set_PWM_dutycycle(PIN_LEFT_BACKWARD, speed_left)
    else:
      self.pi.write(PIN_LEFT_BACKWARD, 0)
      self.pi.set_PWM_dutycycle(PIN_LEFT_FORWARD, speed_left)

    if speed_right < 0:
      speed_right = abs(speed_right)
      self.pi.write(PIN_RIGHT_FORWARD, 0)
      self.pi.set_PWM_dutycycle(PIN_RIGHT_BACKWARD, speed_right)
    else:
      self.pi.write(PIN_RIGHT_BACKWARD, 0)
      self.pi.set_PWM_dutycycle(PIN_RIGHT_FORWARD, speed_right)

    self.pi.write(PIN_MOTOR_ENABLE, 1)
    if elapse > 0:
      time.sleep(elapse)
      self.stop()

  def _servo_motor(self, speed_left=100, speed_right=100, elapse=-1):
    self._is_moving = True
    speed_left = -speed_left

    self.pi.write(PIN_MOTOR_ENABLE, 1)
    self.pi.write(PIN_RIGHT_BACKWARD, 0)
    self.pi.write(PIN_LEFT_BACKWARD, 0)

    self._servo_motor_control(PIN_LEFT_FORWARD, speed_left)
    self._servo_motor_control(PIN_RIGHT_FORWARD, speed_right)
    if elapse > 0:
      time.sleep(elapse)
      self.stop()


  def _servo_motor_control(self, pin, speed):
    self._is_moving = True
    speed = ((speed + 100) * 50 / 200) + 52

    self.pi.set_PWM_range(pin, 1000)
    self.pi.set_PWM_frequency(pin, 50)
    self.pi.set_PWM_dutycycle(pin, speed)

  def _servo_control(self, pin, angle):
    duty = ((angle + 90) * 100 / 180) + 25

    self.pi.set_PWM_range(pin, 1000)
    self.pi.set_PWM_frequency(pin, 50)
    self.pi.set_PWM_dutycycle(pin, duty)

  def stop(self):
    for pin in self._pin_out:
      self.pi.write(pin, 0)
    self._is_moving = False

  def is_moving(self):
    return self._is_moving

  def set_callback(self, gpio, callback, elapse):
    self._cb_elapse[gpio] = elapse * 1000
    self._cb[gpio] = callback
    self._cb_last_tick[gpio] = 0

  def callback(self, gpio, level, tick):
    if gpio == PIN_ENCODER_LEFT:
      self._encoder_cur_left += 1
      if self._encoder_target_left >= self._encoder_cur_left:
        self.pi.write(PIN_LEFT_FORWARD, 0)
	self.pi.write(PIN_LEFT_BACKWARD, 0)
    elif gpio == PIN_ENCODER_RIGHT:
      self._encoder_cur_right += 1
      if self._encoder_target_right >= self._encoder_cur_right:
        self.pi.write(PIN_RIGHT_FORWARD, 0)
	self.pi.write(PIN_RIGHT_BACKWARD, 0)
    else:
      cb = self._cb.get(gpio)
      if cb:
        elapse = self._cb_elapse.get(gpio)
        if level == 0:
          self._cb_last_tick[gpio] = tick
        elif tick - self._cb_last_tick[gpio] > elapse:
          self._cb_last_tick[gpio] = tick
          print "pushed: ", level, tick
          cb()

  def halt(self):
    os.system ('sudo halt')

  def restart(self):
    os.system ('sudo /etc/init.d/coderbot restart')

  def reboot(self):
    os.system ('sudo reboot')

  def sleep(self, elapse):
    time.sleep(elapse)
