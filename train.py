#!/usr/bin/python3 -u

import dataset
import tensorflow as tf
import time
from datetime import timedelta
import math
import random
import numpy as np
import datetime
import re
from numpy.random import seed
from tensorflow import set_random_seed
import argparse
import os


# TODO: 
# - Logging for tensorboard



#logs_path = "/tmp/tf/cc-predictor-model"


parser = argparse.ArgumentParser(description='Train a cnn for predicting cloud coverage')
parser.add_argument('--labelsfile', type=str, help='A labels file containing lines like this: fileNNN.jpg 6')
parser.add_argument('--imagedir', type=str, help='The training and validation data')
parser.add_argument('--outputdir', type=str, help='where to write model snapshots')	
args = parser.parse_args()

# For tensorboard, not used yet.
def variable_summaries(var):
  """Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
  with tf.name_scope('summaries'):
    mean = tf.reduce_mean(var)
    tf.summary.scalar('mean', mean)
    with tf.name_scope('stddev'):
      stddev = tf.sqrt(tf.reduce_mean(tf.square(var - mean)))
    tf.summary.scalar('stddev', stddev)
    tf.summary.scalar('max', tf.reduce_max(var))
    tf.summary.scalar('min', tf.reduce_min(var))
    tf.summary.histogram('histogram', var)

def create_weights(shape):
    return tf.Variable(tf.truncated_normal(shape, stddev=0.05))

def create_biases(size):
    return tf.Variable(tf.constant(0.05, shape=[size]))

def create_convolutional_layer(input,
               num_input_channels, 
               conv_filter_size,        
               num_filters):  
    
    # Define the weights that will be trained.
    weights = create_weights(shape=[conv_filter_size, conv_filter_size, num_input_channels, num_filters])
    variable_summaries(weights)

    ## Create biases using the create_biases function. These are also trained.
    biases = create_biases(num_filters)
    variable_summaries(biases)

    
    ## Creating the convolutional layer
    layer = tf.nn.conv2d(input=input,
                     filter=weights,
                     strides=[1, 1, 1, 1],
                     padding='SAME')

    layer += biases

    ## We shall be using max-pooling.  
    layer = tf.nn.max_pool(value=layer,
                            ksize=[1, 2, 2, 1],
                            strides=[1, 2, 2, 1],
                            padding='SAME')
    ## Output of pooling is fed to Relu which is the activation function for us.
    layer = tf.nn.relu(layer)

    return layer




def create_flatten_layer(layer):
    #We know that the shape of the layer will be [batch_size img_size img_size num_channels] 
    # But let's get it from the previous layer.
    layer_shape = layer.get_shape()

    ## Number of features will be img_height * img_width* num_channels. But we shall calculate it in place of hard-coding it.
    num_features = layer_shape[1:4].num_elements()

    ## Now, we Flatten the layer so we shall have to reshape to num_features
    layer = tf.reshape(layer, [-1, num_features])

    return layer


def create_fc_layer(input,          
             num_inputs,    
             num_outputs,
             use_relu=True):
    
    #Let's define trainable weights and biases.
    weights = create_weights(shape=[num_inputs, num_outputs])
    biases = create_biases(num_outputs)

    # Fully connected layer takes input x and produces wx+b.Since, these are matrices, we use matmul function in Tensorflow
    layer = tf.matmul(input, weights) + biases
    if use_relu:
        layer = tf.nn.relu(layer)

    return layer


def show_progress(iteration, epoch, feed_dict_train, feed_dict_validate, val_loss):
    acc = session.run(accuracy, feed_dict=feed_dict_train)
    val_acc = session.run(accuracy, feed_dict=feed_dict_validate)
    msg = "Iteration {4} Training Epoch {0} --- Training Accuracy: {1:>6.1%}, Validation Accuracy: {2:>6.1%},  Validation Loss: {3:.3f}"
    print("%s %s" % (msg.format(epoch + 1, acc, val_acc, val_loss, iteration +1), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))


def train(start, num_iterations):

    # merge all summaries into a single "operation" which we can execute in a session 
    summary_op = tf.summary.merge_all()
    
    for i in range(start, num_iterations):
        x_batch, y_true_batch = data.train.next_batch(batch_size)
        x_valid_batch, y_valid_batch = data.valid.next_batch(batch_size)

        
        feed_dict_tr = {x: x_batch,
                        y_true: y_true_batch}
        feed_dict_val = {x: x_valid_batch,
                         y_true: y_valid_batch}

        #summary = session.run([optimizer, merged], feed_dict=feed_dict_tr)
        #train_writer.add_summary(summary, i)
        session.run(optimizer, feed_dict=feed_dict_tr)
        # write log
        #writer.add_summary(summary,  i)
        if i % int(data.train.num_examples/batch_size) == 0: 
            val_loss = session.run(cost, feed_dict=feed_dict_val)
            epoch = int(i / int(data.train.num_examples/batch_size))
            show_progress(i, epoch, feed_dict_tr, feed_dict_val, val_loss)

            saver.save(session, args.outputdir + '/cc-predictor-model', global_step=epoch)


if __name__ == "__main__":


	retval = os.system("mkdir -p " + args.outputdir)
	if retval != 0:
		sys.stderr.write('Could not create outputdir\n')
		sys.exit(63)
		
    #Adding Seed so that random initialization is consistent
	seed(1)
	set_random_seed(2)
    
    
	batch_size = 32

	#Prepare input data
	#classes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
	classes = [0, 1, 2, 3, 4, 5, 6, 7, 8]
	num_classes = len(classes)
    
    # 25% of the data will automatically be used for validation
	#validation_size = 0.35
	validation_size = 0.25
    
	img_size = 128
	num_channels = 3
    
	# We shall load all the training and validation images and labels into memory
	# using openCV and use that during training
	data = dataset.read_train_sets(args.labelsfile, args.imagedir, img_size, classes, validation_size=validation_size)
    
	print("Complete reading input data. ")
	print("Number of files in Training-set:\t\t{}".format(len(data.train.labels)))
	print("Number of files in Validation-set:\t{}".format(len(data.valid.labels)))
	print("data.train.num_examples: %d" % data.train.num_examples)

	session = tf.Session()

	x = tf.placeholder(tf.float32, shape=[None, img_size,img_size,num_channels], name='x')
    
	## labels
	y_true = tf.placeholder(tf.float32, shape=[None, num_classes], name='y_true')
	#y_true_cls = tf.argmax(y_true, dimension=1)
	y_true_cls = tf.argmax(y_true, axis=1)

	layer_conv1 = create_convolutional_layer(input=x,
											 num_input_channels=3,
											 conv_filter_size=128,
                                             num_filters=3)
	layer_conv2 = create_convolutional_layer(input=layer_conv1,
                                             num_input_channels=3,
                                             conv_filter_size=64,
                                             num_filters=3)

	layer_conv3= create_convolutional_layer(input=layer_conv2,
                                            num_input_channels=3,
                                            conv_filter_size=32,
                                            num_filters=3)

	layer_conv4= create_convolutional_layer(input=layer_conv3,
                                            num_input_channels=3,
                                            conv_filter_size=16,
                                            num_filters=3)

	layer_conv5= create_convolutional_layer(input=layer_conv4,
                                            num_input_channels=3,
                                            conv_filter_size=8,
                                            num_filters=3)

    

	layer_flat = create_flatten_layer(layer_conv5)
    
	layer_fc1 = create_fc_layer(input=layer_flat,
            num_inputs=layer_flat.get_shape()[1:4].num_elements(),
            num_outputs=128,
            use_relu=True)

    #dropped = tf.nn.dropout(layer_fc1, 0.5)
	dropped = tf.nn.dropout(layer_fc1, 0.5)
	layer_fc2 = create_fc_layer(input=dropped,
            num_inputs=128,
            num_outputs=num_classes,
            use_relu=False) 

    # Softmax is a function that maps [-inf, +inf] to [0, 1] similar as Sigmoid. But Softmax also
    # normalizes the sum of the values(output vector) to be 1.    
	y_pred = tf.nn.softmax(layer_fc2,name='y_pred')

	y_pred_cls = tf.argmax(y_pred, dimension=1)
	session.run(tf.global_variables_initializer())
    # create log writer object
    #merged = tf.summary.merge_all()
    #train_writer = tf.summary.FileWriter(logs_path + '/train', graph=tf.get_default_graph())
    #test_writer  = tf.summary.FileWriter(logs_path + '/test',  graph=tf.get_default_graph())
    

    
    # Logit is a function that maps probabilities [0, 1] to [-inf, +inf]. 
	cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits=layer_fc2,
                                                            labels=y_true)
	cost = tf.reduce_mean(cross_entropy)
	optimizer = tf.train.AdamOptimizer(learning_rate=1e-4).minimize(cost)
	correct_prediction = tf.equal(y_pred_cls, y_true_cls)
	accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))


	session.run(tf.global_variables_initializer()) 

	saver = tf.train.Saver(max_to_keep=100000)
	path = args.outputdir
	start = 0
    
	if tf.train.latest_checkpoint(path) is not None:
		print("Loading %s  %s " % (path, tf.train.latest_checkpoint(path)))
		saver.restore(session, tf.train.latest_checkpoint(path))
		found_num = re.search(r'\d+', tf.train.latest_checkpoint(path))
		epoch = int(found_num.group(0))
		print("Training from epoch %d" % epoch)
		start = epoch * int(data.train.num_examples/batch_size) + 2 
		print("StartIter: %d " % start)
	train(start, num_iterations=10000000)