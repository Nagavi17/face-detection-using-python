# -*- coding: utf-8 -*-
"""face_recognition.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/126vFHOMD0W9Wo1LHETaZOj6iZRfCCwuR
"""

#pip install face_classification

!pip install dlib
import dlib

pip install face_recognition

import cv2
import numpy as np
import os
import face_recognition as fr
from google.colab.patches import cv2_imshow

from google.colab import drive
drive.mount('/content/drive')

path = "/content/drive/MyDrive/train/"

known_names = []
known_name_encodings = []

images = os.listdir(path)
for _ in images:
    image = fr.load_image_file(path + _)
    image_path = path + _
    encoding = fr.face_encodings(image)[0]

    known_name_encodings.append(encoding)
    known_names.append(os.path.splitext(os.path.basename(image_path))[0].capitalize())

print(known_names)

test_image = "/content/drive/MyDrive/test/we.jpg"
image = cv2.imread(test_image)
# image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

face_locations = fr.face_locations(image)
face_encodings = fr.face_encodings(image, face_locations)

for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
    matches = fr.compare_faces(known_name_encodings, face_encoding)
    name = ""

    face_distances = fr.face_distance(known_name_encodings, face_encoding)
    best_match = np.argmin(face_distances)

    if matches[best_match]:
        name = known_names[best_match]

    cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 2)
    cv2.rectangle(image, (left, bottom - 15), (right, bottom), (0, 0, 255), cv2.FILLED)
    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(image, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)


cv2_imshow(image)
cv2.imwrite("/content/drive/MyDrive/Colab Notebooks/face-recognition-python-code/output/output.jpg", image)
cv2.waitKey(0)
cv2.destroyAllWindows()

pip install tflearn

pip install speech_data

import os
import re
import sys
import wave

import numpy
import numpy as np
import skimage.io  # scikit-image
import librosa
import matplotlib

from random import shuffle
from six.moves import urllib
from six.moves import xrange  # pylint: disable=redefined-builtin

# TRAIN_INDEX='train_words_index.txt'
# TEST_INDEX='test_words_index.txt'
SOURCE_URL = 'http://pannous.net/files/' #spoken_numbers.tar'
DATA_DIR = 'data/'
pcm_path = "data/spoken_numbers_pcm/" # 8 bit
wav_path = "data/spoken_numbers_wav/" # 16 bit s16le
path = pcm_path
CHUNK = 4096
test_fraction=0.1 # 10% of data for test / verification

# http://pannous.net/files/spoken_numbers_pcm.tar
class Source:  # labels
  DIGIT_WAVES = 'spoken_numbers_pcm.tar'
  DIGIT_SPECTROS = 'spoken_numbers_spectros_64x64.tar'  # 64x64  baby data set, works astonishingly well
  NUMBER_WAVES = 'spoken_numbers_wav.tar'
  NUMBER_IMAGES = 'spoken_numbers.tar'  # width=256 height=256
  WORD_SPECTROS = 'https://dl.dropboxusercontent.com/u/23615316/spoken_words.tar'  # width,height=512# todo: sliding window!
  TEST_INDEX = 'test_index.txt'
  TRAIN_INDEX = 'train_index.txt'

from enum import Enum
class Target(Enum):  # labels
  digits=1
  speaker=2
  words_per_minute=3
  word_phonemes=4
  word=5#characters=5
  sentence=6
  sentiment=7
  first_letter=8



def progresshook(blocknum, blocksize, totalsize):
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        s = "\r%5.1f%% %*d / %d" % (
            percent, len(str(totalsize)), readsofar, totalsize)
        sys.stderr.write(s)
        if readsofar >= totalsize: # near the end
            sys.stderr.write("\n")
    else: # total size is unknown
        sys.stderr.write("read %d\n" % (readsofar,))

def maybe_download(file, work_directory):
  """Download the data from Pannous's website, unless it's already here."""
  print("Looking for data %s in %s"%(file,work_directory))
  if not os.path.exists(work_directory):
    os.mkdir(work_directory)
  filepath = os.path.join(work_directory, re.sub('.*\/','',file))
  if not os.path.exists(filepath):
    if not file.startswith("http"): url_filename = SOURCE_URL + file
    else: url_filename=file
    print('Downloading from %s to %s' % (url_filename, filepath))
    filepath, _ = urllib.request.urlretrieve(url_filename, filepath,progresshook)
    statinfo = os.stat(filepath)
    print('Successfully downloaded', file, statinfo.st_size, 'bytes.')
    # os.system('ln -s '+work_directory)
  if os.path.exists(filepath):
    print('Extracting %s to %s' % ( filepath, work_directory))
    os.system('tar xf %s -C %s' % ( filepath, work_directory))
    print('Data ready!')
  return filepath.replace(".tar","")

def spectro_batch(batch_size=10):
  return spectro_batch_generator(batch_size)

def speaker(file):  # vom Dateinamen
  # if not "_" in file:
  #   return "Unknown"
  return file.split("_")[1]

def get_speakers(path=pcm_path):
  files = os.listdir(path)
  def nobad(file):
    return "_" in file and not "." in file.split("_")[1]
  speakers=list(set(map(speaker,filter(nobad,files))))
  print(len(speakers)," speakers: ",speakers)
  return speakers

def load_wav_file(name):
  f = wave.open(name, "rb")
  # print("loading %s"%name)
  chunk = []
  data0 = f.readframes(CHUNK)
  while data0:  # f.getnframes()
    # data=numpy.fromstring(data0, dtype='float32')
    # data = numpy.fromstring(data0, dtype='uint16')
    data = numpy.fromstring(data0, dtype='uint8')
    data = (data + 128) / 255.  # 0-1 for Better convergence
    # chunks.append(data)
    chunk.extend(data)
    data0 = f.readframes(CHUNK)
  # finally trim:
  chunk = chunk[0:CHUNK * 2]  # should be enough for now -> cut
  chunk.extend(numpy.zeros(CHUNK * 2 - len(chunk)))  # fill with padding 0's
  # print("%s loaded"%name)
  return chunk


def spectro_batch_generator(batch_size=10,width=64,source_data=Source.DIGIT_SPECTROS,target=Target.digits):
  # maybe_download(Source.NUMBER_IMAGES , DATA_DIR)
  # maybe_download(Source.SPOKEN_WORDS, DATA_DIR)
  path=maybe_download(source_data, DATA_DIR)
  path=path.replace("_spectros","")# HACK! remove!
  height = width
  batch = []
  labels = []
  speakers=get_speakers(path)
  if target==Target.digits: num_classes=10
  if target==Target.first_letter: num_classes=32
  files = os.listdir(path)
  # shuffle(files) # todo : split test_fraction batch here!
  # files=files[0:int(len(files)*(1-test_fraction))]
  print("Got %d source data files from %s"%(len(files),path))
  while True:
    # print("shuffling source data files")
    shuffle(files)
    for image_name in files:
      if not "_" in image_name: continue # bad !?!
      image = skimage.io.imread(path + "/" + image_name).astype(numpy.float32)
      # image.resize(width,height) # lets see ...
      data = image / 255.  # 0-1 for Better convergence
      data = data.reshape([width * height])  # tensorflow matmul needs flattened matrices wtf
      batch.append(list(data))
      # classe=(ord(image_name[0]) - 48)  # -> 0=0 .. A:65-48 ... 74 for 'z'
      classe = (ord(image_name[0]) - 48) % 32# -> 0=0  17 for A, 10 for z ;)
      labels.append(dense_to_one_hot(classe,num_classes))
      if len(batch) >= batch_size:
        yield batch, labels
        batch = []  # Reset for next batch
        labels = []

def mfcc_batch_generator(batch_size=10, source=Source.DIGIT_WAVES, target=Target.digits):
  maybe_download(source, DATA_DIR)
  if target == Target.speaker: speakers = get_speakers()
  batch_features = []
  labels = []
  files = os.listdir(path)
  while True:
    print("loaded batch of %d files" % len(files))
    shuffle(files)
    for wav in files:
      if not wav.endswith(".wav"): continue
      wave, sr = librosa.load(path+wav, mono=True)
      if target==Target.speaker: label=one_hot_from_item(speaker(wav), speakers)
      elif target==Target.digits:  label=dense_to_one_hot(int(wav[0]),10)
      elif target==Target.first_letter:  label=dense_to_one_hot((ord(wav[0]) - 48) % 32,32)
      else: raise Exception("todo : labels for Target!")
      labels.append(label)
      mfcc = librosa.feature.mfcc(wave, sr)
      # print(np.array(mfcc).shape)
      mfcc=np.pad(mfcc,((0,0),(0,80-len(mfcc[0]))), mode='constant', constant_values=0)
      batch_features.append(np.array(mfcc))
      if len(batch_features) >= batch_size:
        # print(np.array(batch_features).shape)
        # yield np.array(batch_features), labels
        yield batch_features, labels  # basic_rnn_seq2seq inputs must be a sequence
        batch_features = []  # Reset for next batch
        labels = []


# If you set dynamic_pad=True when calling tf.train.batch the returned batch will be automatically padded with 0s. Handy! A lower-level option is to use tf.PaddingFIFOQueue.
# only apply to a subset of all images at one time
def wave_batch_generator(batch_size=10,source=Source.DIGIT_WAVES,target=Target.digits): #speaker
  maybe_download(source, DATA_DIR)
  if target == Target.speaker: speakers=get_speakers()
  batch_waves = []
  labels = []
  # input_width=CHUNK*6 # wow, big!!
  files = os.listdir(path)
  while True:
    shuffle(files)
    print("loaded batch of %d files" % len(files))
    for wav in files:
      if not wav.endswith(".wav"):continue
      if target==Target.digits: labels.append(dense_to_one_hot(int(wav[0])))
      elif target==Target.speaker: labels.append(one_hot_from_item(speaker(wav), speakers))
      elif target==Target.first_letter:  label=dense_to_one_hot((ord(wav[0]) - 48) % 32,32)
      else: raise Exception("todo : Target.word label!")
      chunk = load_wav_file(path+wav)
      batch_waves.append(chunk)
      # batch_waves.append(chunks[input_width])
      if len(batch_waves) >= batch_size:
        yield batch_waves, labels
        batch_waves = []  # Reset for next batch
        labels = []

class DataSet(object):

  def __init__(self, images, labels, fake_data=False, one_hot=False, load=False):
    """Construct a DataSet. one_hot arg is used only if fake_data is true."""
    if fake_data:
      self._num_examples = 10000
      self.one_hot = one_hot
    else:
      num = len(images)
      assert num == len(labels), ('images.shape: %s labels.shape: %s' % (images.shape, labels.shape))
      print("len(images) %d" % num)
      self._num_examples = num
    self.cache={}
    self._image_names = numpy.array(images)
    self._labels = labels
    self._epochs_completed = 0
    self._index_in_epoch = 0
    self._images=[]
    if load: # Otherwise loaded on demand
      self._images=self.load(self._image_names)

  @property
  def images(self):
    return self._images

  @property
  def image_names(self):
    return self._image_names

  @property
  def labels(self):
    return self._labels

  @property
  def num_examples(self):
    return self._num_examples

  @property
  def epochs_completed(self):
    return self._epochs_completed

  # only apply to a subset of all images at one time
  def load(self,image_names):
    print("loading %d images"%len(image_names))
    return list(map(self.load_image,image_names)) # python3 map object WTF

  def load_image(self,image_name):
    if image_name in self.cache:
        return self.cache[image_name]
    else:
      image = skimage.io.imread(DATA_DIR+ image_name).astype(numpy.float32)
      # images = numpy.multiply(images, 1.0 / 255.0)
      self.cache[image_name]=image
      return image


  def next_batch(self, batch_size, fake_data=False):
    """Return the next `batch_size` examples from this data set."""
    if fake_data:
      fake_image = [1] * width * height
      if self.one_hot:
        fake_label = [1] + [0] * 9
      else:
        fake_label = 0
      return [fake_image for _ in xrange(batch_size)], [
          fake_label for _ in xrange(batch_size)]
    start = self._index_in_epoch
    self._index_in_epoch += batch_size
    if self._index_in_epoch > self._num_examples:
      # Finished epoch
      self._epochs_completed += 1
      # Shuffle the data
      perm = numpy.arange(self._num_examples)
      numpy.random.shuffle(perm)
      # self._images = self._images[perm]
      self._image_names = self._image_names[perm]
      self._labels = self._labels[perm]
      # Start next epoch
      start = 0
      self._index_in_epoch = batch_size
      assert batch_size <= self._num_examples
    end = self._index_in_epoch
    return self.load(self._image_names[start:end]), self._labels[start:end]


# multi-label
def dense_to_some_hot(labels_dense, num_classes=140):
  """Convert class labels from int vectors to many-hot vectors!"""
  raise "TODO dense_to_some_hot"


def one_hot_to_item(hot, items):
  i=np.argmax(hot)
  item=items[i]
  return item

def one_hot_from_item(item, items):
  # items=set(items) # assure uniqueness
  x=[0]*len(items)# numpy.zeros(len(items))
  i=items.index(item)
  x[i]=1
  return x

def dense_to_one_hot(batch, batch_size, num_labels):
  sparse_labels = tf.reshape(batch, [batch_size, 1])
  indices = tf.reshape(tf.range(0, batch_size, 1), [batch_size, 1])
  concatenated = tf.concat(1, [indices, sparse_labels])
  concat = tf.concat(0, [[batch_size], [num_labels]])
  output_shape = tf.reshape(concat, [2])
  sparse_to_dense = tf.sparse_to_dense(concatenated, output_shape, 1.0, 0.0)
  return tf.reshape(sparse_to_dense, [batch_size, num_labels])

def dense_to_one_hot(labels_dense, num_classes=10):
  """Convert class labels from scalars to one-hot vectors."""
  return numpy.eye(num_classes)[labels_dense]

def extract_labels(names_file,train, one_hot):
  labels=[]
  for line in open(names_file).readlines():
    image_file,image_label = line.split("\t")
    labels.append(image_label)
  if one_hot:
      return dense_to_one_hot(labels)
  return labels

def extract_images(names_file,train):
  image_files=[]
  for line in open(names_file).readlines():
    image_file,image_label = line.split("\t")
    image_files.append(image_file)
  return image_files


def read_data_sets(train_dir,source_data=Source.NUMBER_IMAGES, fake_data=False, one_hot=True):
  class DataSets(object):
    pass
  data_sets = DataSets()
  if fake_data:
    data_sets.train = DataSet([], [], fake_data=True, one_hot=one_hot)
    data_sets.validation = DataSet([], [], fake_data=True, one_hot=one_hot)
    data_sets.test = DataSet([], [], fake_data=True, one_hot=one_hot)
    return data_sets
  VALIDATION_SIZE = 2000
  local_file = maybe_download(source_data, train_dir)
  train_images = extract_images(TRAIN_INDEX,train=True)
  train_labels = extract_labels(TRAIN_INDEX,train=True, one_hot=one_hot)
  test_images = extract_images(TEST_INDEX,train=False)
  test_labels = extract_labels(TEST_INDEX,train=False, one_hot=one_hot)
  # train_images = train_images[:VALIDATION_SIZE]
  # train_labels = train_labels[:VALIDATION_SIZE:]
  # test_images = test_images[VALIDATION_SIZE:]
  # test_labels = test_labels[VALIDATION_SIZE:]
  data_sets.train = DataSet(train_images, train_labels , load=False)
  data_sets.test = DataSet(test_images, test_labels, load=True)
  # data_sets.validation = DataSet(validation_images, validation_labels, load=True)
  return data_sets

if __name__ == "__main__":
  print("downloading speech datasets")
  maybe_download(Source.DIGIT_SPECTROS)
  maybe_download(Source.DIGIT_WAVES)
  maybe_download(Source.NUMBER_IMAGES)
  maybe_download(Source.NUMBER_WAVES)

from __future__ import division, print_function, absolute_import
import tflearn

import tensorflow as tf


learning_rate = 0.0001
training_iters = 300000  # steps
batch_size = 64

width = 20  # mfcc features
height = 80  # (max) length of utterance
classes = 10  # digits

batch = word_batch = mfcc_batch_generator(batch_size)
X, Y = next(batch)
trainX, trainY = X, Y
testX, testY = X, Y #overfit for now

# Network building
net = tflearn.input_data([None, width, height])
net = tflearn.lstm(net, 128, dropout=0.8)
net = tflearn.fully_connected(net, classes, activation='softmax')
net = tflearn.regression(net, optimizer='adam', learning_rate=learning_rate, loss='categorical_crossentropy')
# Training

### add this "fix" for tensorflow version errors
col = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)
for x in col:
    tf.add_to_collection(tf.GraphKeys.VARIABLES, x )


model = tflearn.DNN(net, tensorboard_verbose=0)
while 1: #training_iters
  model.fit(trainX, trainY, n_epoch=10, validation_set=(testX, testY), show_metric=True,
          batch_size=batch_size)
  _y=model.predict(X)
model.save("tflearn.lstm.model")
print (_y)
print (y)