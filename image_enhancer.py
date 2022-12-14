import cv2
import os
import time
##import string
# import random
#import zipfile
import numpy as np
#from PIL import Image
#import datetime
import tensorflow as tf
#from tensorflow.keras.preprocessing.image import ImageDataGenerator
#from tensorflow.keras import backend as K
#from tensorflow import keras
from tensorflow.keras.models import Sequential, Model, load_model
#from tensorflow.keras.optimizers import SGD
#from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
#from google.colab.patches import cv2_imshow
from tensorflow.keras.layers import Input, Add, Conv2DTranspose, Activation, ZeroPadding2D
from tensorflow.keras.layers import BatchNormalization, Flatten, Conv2D, LeakyReLU
#from tensorflow.keras.preprocessing import image
from tensorflow.keras.initializers import glorot_uniform
from tensorflow.keras.losses import BinaryCrossentropy
#from tensorflow.keras.utils import plot_model
import matplotlib.pyplot as plt
from skimage.util import random_noise
from IPython.display import clear_output

AUTOTUNE = tf.data.AUTOTUNE

def getname(n_count, digi_len, n_type="string", ext=""):
  n_str = list(string.ascii_letters)
  n_int = np.random.randint(0, len(n_str)-1, size=(n_count, digi_len)).tolist()
  names = []
  if n_type.lower()=="string":
    for i in n_int:
      name = [n_str[n] for n in i]
      names.append(''.join(name)+ext)
  elif n_type.lower()=="integer":
    n_int = np.random.randint(0, 9, size=(n_count, digi_len)).tolist()
    for i in n_int:
      name = [str(n) for n in i]
      names.append(''.join(name)+ext)
  elif n_type.lower()=="strint":
    for i in n_int:
      rand = np.random.randint(0, 9, size=(digi_len,)).tolist()
      rm = np.random.randint(0, 2, size=(digi_len,)).tolist()
      name = [n_str[n] if y==1 else str(x) for n, x, y in zip(i, rand, rm)]
      names.append(''.join(name)+ext)
  return names

def noise(image, n, noise_type):
  shape = image.shape
  noise_shape = tuple(int(ele // n) for ele in shape[0:2])
  noise_shape = tuple([noise_shape[0]*noise_shape[1]])
  image = image.reshape((
      shape[0] * shape[1], shape[2]
  ))
  if noise_type == "RGB":
     noise_arr = np.random.randint(0, 255, size=noise_shape+(3,), dtype="uint8")
  if noise_type == "GRAYSCALE":
    noise_arr = np.random.randint(0, 255, size=noise_shape+(1,), dtype="uint8")
    i = Image.fromarray(noise_arr, 'L')
    img = Image.new("RGB", i.size)
    img.paste(i)
    noise_arr = np.array(img)
  i = 0
  while True:
    try:
      i1 = random.randint(0, image.shape[0])
      image[i1] = noise_arr[i]
      i += 1
    except IndexError:
      break
  image = image.reshape(shape)
  return image

os.mkdir("/content/data/")
os.chdir("/content/data/")
with zipfile.ZipFile("/content/drive/MyDrive/img.zip", 'r') as zip_ref:
    zip_ref.extractall(os.getcwd())

img_height = 1080
img_width = 1920
BUFFER_SIZE = 400
BATCH_SIZE = 10
EPOCHS = 50
LAMBDA = 10
ds_path = "/content/drive/MyDrive/DataSet"
DSI = "/content/drive/MyDrive/DSI/"
loss_object = BinaryCrossentropy(from_logits=True)

names = getname(len(os.listdir(DSI)), 18, n_type='strint',ext='.jpg')
for old, new in zip(os.listdir(DSI), names):
  os.rename(DSI+old, DSI+new)

os.mkdir("/content/drive/MyDrive/label")
os.mkdir("/content/drive/MyDrive/feat")
for i in os.listdir(DSI):
  img = cv2.imread(DSI+i)
  img = cv2.resize(img, (img_width, img_height))
  cv2.imwrite("/content/drive/MyDrive/label/"+i, img)
  noise_img = random_noise(img, mode='s&p',amount=0.2)
  noise_img = np.array(255*noise_img, dtype = 'uint8')
  worse_img = cv2.GaussianBlur(noise_img, (15,15), 0)
  cv2.imwrite("/content/drive/MyDrive/feat/"+i, worse_img)

feat_path = np.array([])
label_path = np.array([])
for f, l in zip(os.listdir("/content/drive/MyDrive/feat"), os.listdir("/content/drive/MyDrive/label")):
  feat_path = np.append(feat_path, "/content/drive/MyDrive/feat/"+f)
  label_path = np.append(label_path, "/content/drive/MyDrive/label/"+l)
ds = tf.data.Dataset.from_tensor_slices((feat_path, label_path))

def load(input_image, real_image):
  input_image = tf.io.read_file(input_image)
  input_image = tf.image.decode_jpeg(input_image)
  input_image = tf.cast(input_image, tf.float32)

  real_image = tf.io.read_file(real_image)
  real_image = tf.image.decode_jpeg(real_image)
  real_image = tf.cast(real_image, tf.float32)

  return input_image, real_image

def normalize(inp_image, real_image):
  inp_image = tf.cast(inp_image, tf.float32)
  inp_image = (inp_image / 127.5) - 1

  real_image = tf.cast(real_image, tf.float32)
  real_image = (real_image / 127.5) - 1
  return inp_image, real_image

def image_proccess(input_image, real_image):
  input_image, real_image = load(input_image, real_image)
  input_image, real_image = normalize(input_image, real_image)

  return input_image, real_image

train_dataset = ds.map(image_proccess, num_parallel_calls=tf.data.AUTOTUNE)
# train_dataset = train_dataset.shuffle(BUFFER_SIZE)
train_dataset = train_dataset.batch(1)

tf.data.experimental.save(train_dataset, ds_path)

train_dataset = tf.data.experimental.load(path=ds_path)

for i in train_dataset:
  plt.figure(figsize=(18, 18))
  for t in range(2):
    plt.subplot(1, 2, t+1)
    plt.imshow(i[t][0] * 0.5 + 0.5)
    plt.axis('off')
  plt.show()
  break

def identity_block(X, f, filters, stage, block):
   
    conv_name_base = 'res' + str(stage) + block + '_branch'
    bn_name_base = 'bn' + str(stage) + block + '_branch'
    F1, F2, F3 = filters

    X_shortcut = X
   
    X = Conv2D(filters=F1, kernel_size=(5, 5), strides=(1, 1), padding='same', name=conv_name_base + '2a', kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(name=bn_name_base + '2a')(X)
    X = Activation('relu')(X)

    X = Conv2D(filters=F2, kernel_size=(f, f), strides=(1, 1), padding='same', name=conv_name_base + '2b', kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(name=bn_name_base + '2b')(X)
    X = Activation('relu')(X)

    X = Conv2D(filters=F3, kernel_size=(5, 5), strides=(1, 1), padding='same', name=conv_name_base + '2c', kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(name=bn_name_base + '2c')(X)

    X = Add()([X, X_shortcut])# SKIP Connection
    X = LeakyReLU()(X)

    return X

def convolutional_block(X, f, filters, stage, block, s=2):
   
    conv_name_base = 'res' + str(stage) + block + '_branch'
    bn_name_base = 'bn' + str(stage) + block + '_branch'

    F1, F2, F3 = filters

    X_shortcut = X

    X = Conv2D(filters=F1, kernel_size=(5, 5), strides=(s, s), padding='same', name=conv_name_base + '2a', kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(name=bn_name_base + '2a')(X)
    X = Activation('relu')(X)

    X = Conv2D(filters=F2, kernel_size=(f, f), strides=(1, 1), padding='same', name=conv_name_base + '2b', kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(name=bn_name_base + '2b')(X)
    X = Activation('relu')(X)

    X = Conv2D(filters=F3, kernel_size=(5, 5), strides=(1, 1), padding='same', name=conv_name_base + '2c', kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(name=bn_name_base + '2c')(X)

    X_shortcut = Conv2D(filters=F3, kernel_size=(5, 5), strides=(s, s), padding='same', name=conv_name_base + '1', kernel_initializer=glorot_uniform(seed=0))(X_shortcut)
    X_shortcut = BatchNormalization(name=bn_name_base + '1')(X_shortcut)

    X = Add()([X, X_shortcut])
    X = LeakyReLU()(X)

    return X

def ResNet50(input_shape=(1080, 1920, 3)):

    X_input = Input(input_shape)

    last = tf.keras.layers.Conv2DTranspose(3, 5, strides=3, padding='same', activation='tanh')

    X = ZeroPadding2D((3, 3))(X_input)

    X = Conv2D(64, (7, 7), strides=(1, 1), name='conv1', kernel_initializer=glorot_uniform(seed=0))(X)
    X = BatchNormalization(axis=3, name='bn_conv1')(X)
    X = Activation('relu')(X)

    X = convolutional_block(X, f=4, filters=[128, 128, 128], stage=2, block='a', s=3)
    X = identity_block(X, 7, [128, 128, 128], stage=2, block='b')
    X = identity_block(X, 7, [128, 128, 128], stage=2, block='c')


    X = convolutional_block(X, f=4, filters=[384, 256, 384], stage=3, block='a', s=2)
    X = identity_block(X, 7, [384, 256, 384], stage=3, block='b')
    # X = identity_block(X, 7, [384, 256, 384], stage=3, block='c')
    X = identity_block(X, 7, [384, 256, 384], stage=3, block='d')

    X = convolutional_block(X, f=4, filters=[512, 256, 384], stage=4, block='a', s=2)
    X = identity_block(X, 5, [512, 256, 384], stage=4, block='b')
    X = identity_block(X, 5, [512, 256, 384], stage=4, block='c')
    X = identity_block(X, 5, [512, 256, 384], stage=4, block='d')
    X = identity_block(X, 5, [512, 256, 384], stage=4, block='e')
    # X = identity_block(X, 7, [256, 256, 256], stage=4, block='f')

    X = X = convolutional_block(X, f=4, filters=[768, 512, 512], stage=5, block='a', s=1)
    X = identity_block(X, 7, [768, 512, 512], stage=5, block='b')
    X = identity_block(X, 7, [768, 512, 512], stage=5, block='c')

    X = tf.keras.layers.Conv2DTranspose(256, 7, strides=4, padding='same')(X)
    model = Model(inputs=X_input, outputs=last(X), name='ResNet50')

    return model

def downsample(filters, size, apply_batchnorm=True):
  initializer = tf.random_normal_initializer(0., 0.02)

  result = tf.keras.Sequential()
  result.add(
      tf.keras.layers.Conv2D(filters, size, strides=2, padding='same',
                             kernel_initializer=initializer, use_bias=False))

  if apply_batchnorm:
    result.add(tf.keras.layers.BatchNormalization())

  result.add(tf.keras.layers.LeakyReLU())

  return result

def Discriminator():
  initializer = tf.random_normal_initializer(0., 0.02)

  inp = tf.keras.layers.Input(shape=[1080, 1920, 3], name='input_image')
  tar = tf.keras.layers.Input(shape=[1080, 1920, 3], name='target_image')

  x = tf.keras.layers.concatenate([inp, tar])  # (batch_size, 256, 256, channels*2)

  down1 = downsample(32, 4, False)(x)  # (batch_size, 128, 128, 64)
  down2 = downsample(64, 4)(down1)  # (batch_size, 64, 64, 128)
  down3 = downsample(129, 4)(down2)  # (batch_size, 32, 32, 256)

  zero_pad1 = tf.keras.layers.ZeroPadding2D()(down3)  # (batch_size, 34, 34, 256)
  conv = tf.keras.layers.Conv2D(384, 4, strides=2,
                                kernel_initializer=initializer,
                                use_bias=False)(zero_pad1)  # (batch_size, 31, 31, 512)
  conv = tf.keras.layers.Conv2D(64, 4, strides=2,
                                kernel_initializer=initializer,
                                use_bias=False)(conv)
  conv = tf.keras.layers.Conv2D(8, 4, strides=2,
                                kernel_initializer=initializer,
                                use_bias=False)(conv)                                                                  
  batchnorm1 = tf.keras.layers.BatchNormalization()(conv)

  leaky_relu = tf.keras.layers.LeakyReLU()(batchnorm1)

  zero_pad2 = tf.keras.layers.ZeroPadding2D()(leaky_relu)  # (batch_size, 33, 33, 512)
  zero_pad2 = tf.keras.layers.Flatten()(zero_pad2)          
  last = tf.keras.layers.Dense(1, activation=LeakyReLU(), use_bias=False, 
                               kernel_initializer=initializer)(zero_pad2)  # (batch_size, 30, 30, 1)

  return tf.keras.Model(inputs=[inp, tar], outputs=last)

generator = ResNet50()
discriminator = Discriminator()

def generator_loss(disc_generated_output, gen_output, target):
  gan_loss = loss_object(tf.ones_like(disc_generated_output), disc_generated_output)

  # Mean absolute error
  l1_loss = tf.reduce_mean(tf.abs(target - gen_output))

  total_gen_loss = gan_loss + (LAMBDA * l1_loss)

  return total_gen_loss, gan_loss, l1_loss

def discriminator_loss(disc_real_output, disc_generated_output):
  real_loss = loss_object(tf.ones_like(disc_real_output), disc_real_output)

  generated_loss = loss_object(tf.zeros_like(disc_generated_output), disc_generated_output)

  total_disc_loss = real_loss + generated_loss

  return total_disc_loss

generator_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.5)

discriminator_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.5)

checkpoint_dir = '/content/drive/MyDrive/checkpoints/train'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
checkpoint = tf.train.Checkpoint(generator_optimizer=generator_optimizer,
                                 discriminator_optimizer=discriminator_optimizer,
                                 generator=generator,
                                 discriminator=discriminator)

ckpt_manager = tf.train.CheckpointManager(checkpoint, checkpoint_dir, max_to_keep=5)

# if a checkpoint exists, restore the latest checkpoint.
if ckpt_manager.latest_checkpoint:
  checkpoint.restore(ckpt_manager.latest_checkpoint)
  print ('Latest checkpoint restored!!\n{}'.format(ckpt_manager.latest_checkpoint))

def generate_images(model, test_input, target=None):
  prediction = model(test_input)
    
  plt.figure(figsize=(18, 18))
  if target is not None:
    display_list = [test_input[0], prediction[0], target[0]]
    title = ['Input Image', 'Predicted Image', 'Expected Image']
  else:
    display_list = [test_input[0], prediction[0]]
    title = ['Input Image', 'Predicted Image']
  for i in range(len(title)):
    plt.subplot(1, len(title), i+1)
    plt.title(title[i])
    # getting the pixel values between [0, 1] to plot it.
    plt.imshow(display_list[i] * 0.5 + 0.5)
    plt.axis('off')
  plt.show()

d_test = "/content/drive/MyDrive/test/"
tst_lap, tst_ft  = np.array([]), np.array([])
for i in os.listdir(d_test):
  img = cv2.imread(d_test+i)
  img = cv2.resize(img, (img_width, img_height))
  tst_lap = np.append(tst_lap, img)
  noise_img = random_noise(img, mode='s&p',amount=0.2)
  noise_img = np.array(255*noise_img, dtype = 'uint8')
  worse_img = cv2.GaussianBlur(noise_img, (15,15), 0)
  tst_ft = np.append(tst_ft, worse_img)
tst_ft = tst_ft.reshape(
    (len(os.listdir(d_test)), 1, img_height, img_width, 3))
tst_lap = tst_lap.reshape(
    (len(os.listdir(d_test)), 1, img_height, img_width, 3))
tst = tf.data.Dataset.from_tensor_slices((tst_ft, tst_lap))
tst = tst.map(normalize, num_parallel_calls=tf.data.AUTOTUNE)

for i_img, r_img in tst:
    generate_images(generator, i_img, r_img)
    time.sleep(1)

@tf.function
def train_step(input_image, target, epoch):
  with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
    gen_output = generator(input_image, training=True)

    disc_real_output = discriminator([input_image, target], training=True)

    disc_generated_output = discriminator([input_image, gen_output], training=True)

    gen_total_loss, gen_gan_loss, gen_l1_loss = generator_loss(disc_generated_output, gen_output, target)

    disc_loss = discriminator_loss(disc_real_output, disc_generated_output)

  generator_gradients = gen_tape.gradient(gen_total_loss,
                                          generator.trainable_variables)
  discriminator_gradients = disc_tape.gradient(disc_loss,
                                               discriminator.trainable_variables)
  generator_optimizer.apply_gradients(zip(generator_gradients,
                                          generator.trainable_variables))
  discriminator_optimizer.apply_gradients(zip(discriminator_gradients,
                                              discriminator.trainable_variables))

for epoch in range(EPOCHS):
  start = time.time()

  n = 0
  for image_x, image_y in train_dataset:
    train_step(image_x, image_y, epoch)
    if n % 10 == 0:
      e = int(n/10)+1
      print (e, end=' ')
      if e % 10 == 0:
        print ('\n')
    n += 1

  clear_output(wait=True)
  for i_img, r_img in tst:
    generate_images(generator, i_img, r_img)
    time.sleep(1)

  if (epoch + 1) % 1 == 0:
    ckpt_save_path = ckpt_manager.save()
    print ('Saving checkpoint for epoch {} at {}'.format(f"{epoch + 1}/{EPOCHS}",
                                                         ckpt_save_path))

  print ('Time taken for epoch {} is {} sec\n'.format(f"{epoch + 1}/{EPOCHS}",
                                                      time.time()-start))

test_img_path = '/content/drive/MyDrive/test.jpg'
input_image = tf.io.read_file(test_img_path)
input_image = tf.image.decode_jpeg(input_image)
input_image = tf.cast(input_image, tf.float32)

inp_image = (input_image / 127.5) - 1

generate_images(generator, inp_image)

# def Generator(inputs=(1080, 1920, 3)):
#   net = ResNet50(inputs) #270, 480, 2048
#   inputs = Input(inputs)
#   down_stack = [[1024, (7, 7), 3, True],
#                 [1024, (7, 7), 3, True],
#                 [1024, (7, 7), 3, True],
#                 [1024, (7, 7), 1, True],
#                 [1024, (7, 7), 2, True],
#                 [1024, (7, 7), 2, True],
#                 [1024, (7, 7), 2, True]]
#   """down_stack = [
#       downsample(1024, (7, 7), 2, apply_norm=False),  # (None, 135, 240, 128)
#       downsample(1024, (7, 7), 3), # (None, 45, 240, 128)
#       downsample(1024, (7, 7), 3), # (None, 15, 120, 256)
#       downsample(1024, (7, 7), 3), # (None, 5, 30, 256)
#       downsample(1024, (7, 7), 1), # (None, 9, 15, 512)
#       #downsample(1024, (7, 7)), # (None, 5, 8, 512)
#       #downsample(1024, (7, 7)), # (None, 3, 4, 512)
#       #downsample(1024, (7, 7))
#   ]
#   """
#   up_stack = [[1024, (7, 7), 2, True],
#               [1024, (7, 7), 2, True],
#               [1024, (7, 7), 2, True],
#               [1024, (7, 7), 2, False],
#               [1024, (7, 7), 2, False],
#               [1024, (7, 7), 2, False],
#               [1024, (7, 7), 2, False]]
#   """up_stack = [
#       upsample(1024, (7, 7), 3, apply_dropout=True), # (None, 270, 480, 64)
#       upsample(1024, (7, 7), 3, apply_dropout=True),
#       upsample(1024, (7, 7), 3, apply_dropout=True),
#       upsample(1024, (7, 7), 2), 
#       #upsample(1024, (7, 7)),
#       #upsample(1024, (7, 7)),
#       #upsample(1024, (7, 7)),
#   ]"""

#   initializer = tf.random_normal_initializer(0., 0.02)
#   last = tf.keras.layers.Conv2DTranspose(
#       3, 4, strides=2,
#       padding='same', kernel_initializer=initializer,
#       activation='tanh')
  
#   concat = tf.keras.layers.Concatenate()
#   x = downsample(1024, (7, 7), 2, False)(inputs)
#   skips = []
#   for down in down_stack:
#     x = downsample(down[0], down[1], down[2], down[3])()
#     skips.append(x)

#   skips = reversed(skips[:-1])

#   for up, skip in zip(up_stack, skips):
#     x = net(x)
#     x = up(x)
#     x = concat([x, skip])

#   x = last(x)
  
#   return Model(inputs=inputs, outputs=x)

os.chdir("/content/sample_data")
plot_model(generator, show_shapes=True, dpi=64)

import os
 
dir = "/content/data"
for root, dirs, files in os.walk(dir, topdown=False):
   for name in files:
      os.remove(os.path.join(root, name))
   for name in dirs:
      os.rmdir(os.path.join(root, name))
