

# This script was initially from a cv-tricks.com tutorial
# It has MIT licence


import re
import cv2
import numpy as np
import os
from sklearn.utils import shuffle
import tensorflow as tf
import sys
import math

import augment

class DataSet(object):

  def __init__(self, images, labels):
    self._num_examples = images.shape[0]

    self._images = images
    self._labels = labels
    #self._img_names = img_names
    #self._cls = cls
    self._epochs_done = 0
    self._index_in_epoch = 0

  @property
  def images(self):
    return self._images

  @property
  def labels(self):
    return self._labels

  #@property
  #def img_names(self):
  #  return self._img_names

  #@property
  #def cls(self):
  #  return self._cls

  @property
  def num_examples(self):
    return self._num_examples

  @property
  def epochs_done(self):
    return self._epochs_done

  def next_batch(self, batch_size):
    """Return the next `batch_size` examples from this data set."""
    start = self._index_in_epoch
    self._index_in_epoch += batch_size

    if self._index_in_epoch > self._num_examples:
      # After each epoch we update this
      self._epochs_done += 1
      start = 0
      self._index_in_epoch = batch_size
      assert batch_size <= self._num_examples
    end = self._index_in_epoch

    return self._images[start:end], self._labels[start:end]


def load_training_data(labelsfile, imagedir, image_size, classes):
	images = []
	labels = []
	#img_names = []
	#cls = []


	label_counts = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0}
	
	print("Loading ..")
	cnt = 0;
	with open(labelsfile, "r") as ins:
		for line in ins:
			cnt = cnt  + 1
			#if cnt % 600  == 0:
			#	print("loaded %d" % cnt)
			#	break
			myre = re.compile(r'(\S+)\s+(-?\d)$')
			mo = myre.search(line.strip())
			if mo is not None:
				path, cc = mo.groups()				
			else:
				print("Error: No match")
				continue
			try:
				image = cv2.imread(imagedir + "/" + path)
			except cv2.error as e:
				print(e)
				continue

			if image is None:
				print("image %s is none" % path)
				continue
			# Already resized
	        # image = cv2.resize(image, (image_size, image_size),0,0, cv2.INTER_LINEAR)
			if int(cc) < 0:
				continue

			label_counts[int(cc)] = label_counts[int(cc)] + 1 
			index = classes.index(int(cc))
			image = image.astype(np.float32)
			# convert from [0:255] => [0.0:1.0]
			image = np.multiply(image, 1.0 / 255.0)
			images.append(image)
			label = np.zeros(len(classes))
			label[index] = 1.0
			labels.append(label)            
            
	images = np.array(images)
	labels = np.array(labels)

	biggest =  max(label_counts, key=label_counts.get)
	# Oversample minority classes. 
	print("Majority: %d's Count: %d" % (biggest, label_counts[biggest]))  # this is 8 when using all data.

	use_random_rotation=True
	use_random_shift=False   # This is no good ## Not enough RAM
	use_random_shear=True   # Not enough RAM  
	use_random_zoom=False
	num_augs_enabled = 0
	if use_random_rotation:
		num_augs_enabled = num_augs_enabled + 1
	if use_random_shift:
		num_augs_enabled = num_augs_enabled + 1
	if use_random_shear:
		num_augs_enabled = num_augs_enabled + 1
	if use_random_zoom:
		num_augs_enabled = num_augs_enabled + 1
	print("Num augs enabled: %d" % num_augs_enabled)
	aug_factors = dict()
	for ccval in range(0, 9):  # cloud coverage, values in [0,8]
		if num_augs_enabled == 0:
			continue
		aug_factors[ccval] = round((label_counts[biggest]/num_augs_enabled) / label_counts[ccval])
		
		print("dataset.load_training_data(): label %d, " 
			  "Aug_factor: %f, "
			  "Num images: %f, "
			  "Num images after oversampling: %f" %
			  (ccval,
			   aug_factors[ccval],
			   label_counts[ccval],
			   aug_factors[ccval] * label_counts[ccval] * num_augs_enabled))
				
	print("Augmenting data ..")
	"""
	aug_images, aug_labels = augment.augment_data(images, labels,
												  aug_factors,              # Of times to run the  
												                            # (random) augmentation
												  use_random_rotation=use_random_rotation,
                                                  use_random_shift=use_random_shift, # This is no good ## Not enough RAM
                                                  use_random_shear=use_random_shear,   # Not enough RAM  
                                                  use_random_zoom=use_random_zoom,
												  skip_labels = [],        # Skip augment label 8.				  
												  )
	"""

	aug_images, aug_labels = augment.augment_data2(images, labels, 8, label_counts)
	
	images = np.concatenate([images, aug_images])
	labels = np.concatenate([labels, aug_labels])
    

	return images, labels

def read_train_sets(labelsfile, imagedir, image_size, classes, validation_size):
  class DataSets(object):
    pass
  data_sets = DataSets()

 
  images, labels = load_training_data(labelsfile, imagedir, image_size, classes)
  print("SIZE: %d" % (sys.getsizeof(images) / (1024*1024)))
    
  images, labels = shuffle(images, labels)  

    
  if isinstance(validation_size, float):
    validation_size = int(validation_size * images.shape[0])

  validation_images = images[:validation_size]
  validation_labels = labels[:validation_size]
  #validation_img_names = img_names[:validation_size]
  #validation_cls = cls[:validation_size]

  train_images = images[validation_size:]
  train_labels = labels[validation_size:]
  #train_img_names = img_names[validation_size:]
  #train_cls = cls[validation_size:]

  data_sets.train = DataSet(train_images, train_labels)
  data_sets.valid = DataSet(validation_images, validation_labels)

  return data_sets

# Test            
if __name__ == "__main__":
    classes = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    #load_training_data("alldata.txt", 128, classes)
    #load_training_data("alldata.txt", 128, classes)
    data = read_train_sets("alldata.txt", 128, classes, 0.30)
