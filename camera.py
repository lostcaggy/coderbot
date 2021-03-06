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

import time
import copy
import os
import sys
import math
from PIL import Image as PILImage
from StringIO import StringIO
from threading import Thread, Lock
import logging

from viz import camera, streamer, image, blob
import config

MAX_IMAGE_AGE = 0.0
PHOTO_PATH = "./photos"
PHOTO_PREFIX = "DSC"
VIDEO_PREFIX = "VID"
PHOTO_THUMB_SUFFIX = "_thumb"
PHOTO_THUMB_SIZE = (240,180)
VIDEO_ELAPSE_MAX = 900

class Camera(Thread):

  _instance = None
  _img_template = image.Image.load("coderdojo-logo.png")
  stream_port = 8080

  @classmethod
  def get_instance(cls):
    if cls._instance is None:
      cls._instance = Camera()
      cls._instance.start()
    return cls._instance

  def __init__(self):
    logging.info("starting camera")
    cam_props = {"width":640, "height":480, "cv_image_factor":config.Config.get().get("cv_image_factor", 4), "exposure_mode": config.Config.get().get("camera_exposure_mode"), "jpeg_quality": int(config.Config.get().get("camera_jpeg_quality", 20))}
    self._camera = camera.Camera(props=cam_props)
    self.recording = False
    self.video_start_time = time.time() + 8640000
    self._run = True
    self._image_time = 0
    self._cv_image_factor = int(config.Config.get().get("cv_image_factor", 4))
    self._image_lock = Lock()
    self._image_refresh_timeout = float(config.Config.get().get("camera_refresh_timeout", 0.1))
    self._color_object_size_min = int(config.Config.get().get("camera_color_object_size_min", 80)) / (self._cv_image_factor * self._cv_image_factor)
    self._color_object_size_max = int(config.Config.get().get("camera_color_object_size_max", 32000)) / (self._cv_image_factor * self._cv_image_factor)
    self._path_object_size_min = int(config.Config.get().get("camera_path_object_size_min", 80)) / (self._cv_image_factor * self._cv_image_factor)
    self._path_object_size_max = int(config.Config.get().get("camera_path_object_size_max", 32000)) / (self._cv_image_factor * self._cv_image_factor)
    self._photos = []
   
    for dirname, dirnames, filenames,  in os.walk(PHOTO_PATH):
      for filename in filenames:
        if (PHOTO_PREFIX in filename or VIDEO_PREFIX in filename) and PHOTO_THUMB_SUFFIX not in filename:
          self._photos.append(filename)
   
    super(Camera, self).__init__()

  def run(self):
    try:
      self._camera.grab_start()
      while self._run:
        sleep_time = self._image_refresh_timeout - (time.time() - self._image_time)
        if sleep_time <= 0:
          ts = time.time()
          #print "run.1"
          self._image_lock.acquire()
          self._camera.grab_one()
          self._image_lock.release()
          #print "run.2: " + str(time.time()-ts)

          #self.save_image(image.Image(self._camera.get_image_bgr()).filter_color((124,50,74)).to_jpeg())
          self.save_image(self._camera.get_image_jpeg())
          #print "run.3: " + str(time.time()-ts)
        else:
          time.sleep(sleep_time)

        if self.recording and time.time() - self.video_start_time > VIDEO_ELAPSE_MAX:
          self.video_stop()

      self._camera.grab_stop()
    except:
      logging.error("Unexpected error:" + str(sys.exc_info()[0]))
      raise

  def get_image(self, maxage = MAX_IMAGE_AGE):
    return image.Image(self._camera.get_image_bgr())

  def save_image(self, image_jpeg):
    #self._streamer.set_image(image_jpeg)
    self._image_time=time.time()

  def get_image_jpeg(self):
    return copy.copy (self._camera.get_image_jpeg())

  def set_text(self, text):
    self._camera.set_overlay_text(str(text))

  def get_next_photo_index(self):
    last_photo_index = 0
    for p in self._photos:
      try:
        index = int(p[len(PHOTO_PREFIX):-len(self._camera.PHOTO_FILE_EXT)])
        if index > last_photo_index:
          last_photo_index = index
      except:
        pass
    return last_photo_index + 1

  def photo_take(self):
    photo_index = self.get_next_photo_index()
    filename = PHOTO_PREFIX + str(photo_index) + self._camera.PHOTO_FILE_EXT;
    filename_thumb = PHOTO_PREFIX + str(photo_index) + PHOTO_THUMB_SUFFIX + self._camera.PHOTO_FILE_EXT;
    of = open(PHOTO_PATH + "/" + filename, "w+")
    oft = open(PHOTO_PATH + "/" + filename_thumb, "w+")
    im_str = self._camera.get_image_jpeg()
    of.write(im_str)
    # thumb
    im_pil = PILImage.open(StringIO(im_str)) 
    im_pil.resize(PHOTO_THUMB_SIZE).save(oft)
    self._photos.append(filename)

  def is_recording(self):
    return self.recording

  def video_rec(self, video_name=None):
    if self.is_recording():
      return
    self.recording = True

    if video_name is None:
      video_index = self.get_next_photo_index()
      filename = VIDEO_PREFIX + str(video_index) + self._camera.VIDEO_FILE_EXT;
      filename_thumb = VIDEO_PREFIX + str(video_index) + PHOTO_THUMB_SUFFIX + self._camera.PHOTO_FILE_EXT;
    else:
      filename = VIDEO_PREFIX + video_name + self._camera.VIDEO_FILE_EXT;
      filename_thumb = VIDEO_PREFIX + video_name + PHOTO_THUMB_SUFFIX + self._camera.PHOTO_FILE_EXT;
      try:
        #remove previous file and reference in album
        os.remove(PHOTO_PATH + "/" + filename)
        self._photos.remove(filename)
      except:
        pass

    oft = open(PHOTO_PATH +  "/" + filename_thumb, "w")
    im_str = self._camera.get_image_jpeg()
    im_pil = PILImage.open(StringIO(im_str)) 
    im_pil.resize(PHOTO_THUMB_SIZE).save(oft)
    self._photos.append(filename)
    self._camera.video_rec(PHOTO_PATH + "/" + filename)
    self.video_start_time = time.time()

  def video_stop(self):
    if self.recording:
      self._camera.video_stop()
      self.recording = False
    
  def get_photo_list(self):
    return self._photos

  def get_photo_file(self, filename):
    return open(PHOTO_PATH + "/" + filename)

  def get_photo_thumb_file(self, filename):
    return open(PHOTO_PATH + "/" + filename[:-len(PHOTO_FILE_EXT)] + PHOTO_THUMB_SUFFIX + PHOTO_FILE_EXT)

  def delete_photo(self, filename):
    logging.info("delete photo: " + filename)
    os.remove(PHOTO_PATH + "/" + filename)
    os.remove(PHOTO_PATH + "/" + filename[:filename.rfind(".")] + PHOTO_THUMB_SUFFIX + self._camera.PHOTO_FILE_EXT)
    self._photos.remove(filename)

  def exit(self):
    #self._streamer.server.shutdown()
    #self._streamer.server_thread.join()
    self._run = False
    self.join()

  def calibrate(self):
    img = self._camera.getImage()
    self._background = img.hueHistogram()[-1]
  
  def get_average(self):
    self._image_lock.acquire()
    avg = self.get_image(0).get_average()
    self._image_lock.release()
    return avg
      
  def find_line(self):
    self._image_lock.acquire()
    img = self.get_image(0).binarize()
    slices = [0,0,0]
    blobs = [0,0,0]
    slices[0] = img.crop(0, int(self._camera.out_rgb_resolution[1]/1.2), self._camera.out_rgb_resolution[0], self._camera.out_rgb_resolution[1])
    slices[1] = img.crop(0, int(self._camera.out_rgb_resolution[1]/1.5), self._camera.out_rgb_resolution[0], int(self._camera.out_rgb_resolution[1]/1.2))
    slices[2] = img.crop(0, int(self._camera.out_rgb_resolution[1]/2.0), self._camera.out_rgb_resolution[0], int(self._camera.out_rgb_resolution[1]/1.5))
    coords = [-1, -1, -1]
    for idx, slice in enumerate(slices):
      blobs[idx] = slice.find_blobs(minsize=480/(self._cv_image_factor * self._cv_image_factor), maxsize=6400/(self._cv_image_factor * self._cv_image_factor))
      if len(blobs[idx]):
        coords[idx] = (blobs[idx][0].center[0] * 100) / self._camera.out_rgb_resolution[0]
	logging.info("line coord: " + str(idx) + " " +  str(coords[idx])+ " area: " + str(blobs[idx][0].area()))
    
    self._image_lock.release()
    return coords[0]

  def find_signal(self):
    #print "signal"
    angle = None
    ts = time.time()
    self._image_lock.acquire()
    img = self.get_image(0)
    signals = img.find_template(self._img_template)
     
    logging.info("signal: " + str(time.time() - ts))
    if len(signals):
      angle = signals[0].angle

    self._image_lock.release()

    return angle

  def find_face(self):
    face_x = face_y = face_size = None
    self._image_lock.acquire()
    img = self.get_image(0)
    ts = time.time()
    faces = img.grayscale().find_faces()
    logging.info("face.detect: " + str(time.time() - ts))
    self._image_lock.release()
    if len(faces):
      # Get the largest face, face is a rectangle 
      x, y, w, h = faces[0]
      center_x = x + (w/2)
      face_x = ((center_x * 100) / self._camera.out_rgb_resolution[0]) - 50 #center = 0
      center_y = y + (h/2)
      face_y = 50 - (center_y * 100) / self._camera.out_rgb_resolution[1] #center = 0 
      size = h 
      face_size = (size * 100) / self._camera.out_rgb_resolution[1]
      logging.info("face found, x: " + str(face_x) + " y: " + str(face_y) + " size: " + str(face_size))
    return [face_x, face_y, face_size]

  def path_ahead(self):
    image_size = self._camera.out_rgb_resolution    
    ts = time.time()
    self._image_lock.acquire()
    img = self.get_image(0)

    size_y = img._data.shape[0]
    size_x = img._data.shape[1]

    threshold = img.crop(0, size_y - (size_y/12), size_x, size_y)._data.mean() / 2

    blobs = img.binarize(threshold).dilate().find_blobs(minsize=self._path_object_size_min, maxsize=self._path_object_size_max)
    coordY = 60
    if len(blobs):
      obstacle = blob.Blob.sort_distance((image_size[0]/2,image_size[1]), blobs)[0]

      logging.info("obstacle:" + str(obstacle.bottom)) 
      coords = img.transform([(obstacle.center[0], obstacle.bottom)], img.get_transform(img.size()[1]))
      x = coords[0][0]
      y = coords[0][1]
      coordY = 60 - ((y * 48) / (480 / self._cv_image_factor)) 
      logging.info("x: " + str(x) + " y: " + str(y) + " coordY: " + str(coordY))

    self._image_lock.release()
    return coordY

  def find_color(self, s_color):
    image_size = self._camera.out_rgb_resolution
    color = (int(s_color[1:3],16), int(s_color[3:5],16), int(s_color[5:7],16))
    code_data = None
    ts = time.time()
    self._image_lock.acquire()
    img = self.get_image(0)
    bw = img.filter_color(color)
    self._image_lock.release()
    objects = bw.find_blobs(minsize=self._color_object_size_min, maxsize=self._color_object_size_max)
    logging.debug("objects: " + str(objects))
    dist = -1
    angle = 180
    fov_offset = 12 #cm
    fov_total_y = 68 #cm
    fov_total_x = 60 #cm

    if objects and len(objects):
      obj = objects[-1]
      bottom = obj.bottom
      logging.info("bottom: " + str(obj.center[0]) + " " +str(obj.bottom))
      coords = bw.transform([(obj.center[0], obj.bottom)], bw.get_transform(bw.size()[1]))
      logging.info("coordinates: " + str(coords))
      x = coords[0][0]
      y = coords[0][1]
      dist = math.sqrt(math.pow(fov_offset + (fov_total_y * (image_size[1] - y) / (image_size[1]/1.2)),2) + (math.pow((x-(image_size[0]/2)) * fov_total_x / image_size[0],2)))
      angle = math.atan2(x - (image_size[0]/2), image_size[1] - y) * 180 / math.pi
      logging.info("object found, dist: " + str(dist) + " angle: " + str(angle))
    #self.save_image(img.to_jpeg())
    #print "object: " + str(time.time() - ts)
    return [dist, angle]
   
  def find_text(self, accept, back_color):
    text = None
    color = (int(back_color[1:3],16), int(back_color[3:5],16), int(back_color[5:7],16))
    self._image_lock.acquire()
    img = self.get_image(0)
    self._image_lock.release()
    image = img.find_rect(color=color)
    if image:
      logging.info("image: " + str(image))
      bin_image = image.binarize().invert()
      #self.save_image(bin_image.to_jpeg())
      text = bin_image.find_text(accept)
    return text    

  def find_code(self):
    self._image_lock.acquire()
    img = self.get_image(0)
    self._image_lock.release()
    return img.grayscale().find_code()
