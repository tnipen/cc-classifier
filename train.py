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

# This script was initially from a cv-tricks.com tutorial
# It has a MIT licence


parser = argparse.ArgumentParser(description='Train a cnn for predicting cloud coverage')
parser.add_argument('--labelsfile', type=str, help='A labels file containing lines like this: fileNNN.jpg 6')
parser.add_argument('--imagedir', type=str, help='The training and validation data')
parser.add_argument('--outputdir', type=str, default='modeldata', help='where to write model snapshots')
parser.add_argument('--inputdir', type=str, default=None, help='Start training on exising model')

parser.add_argument('--epoch', type=str, default=None, help='Start training from epoch')


parser.add_argument('--logdir', type=str, default='/tmp/tf', help='Metrics data')
args = parser.parse_args()

logs_path = args.logdir

# For tensorboard
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
    #variable_summaries(weights)

    ## Create biases using the create_biases function. These are also trained.
    biases = create_biases(num_filters)
    #variable_summaries(biases)


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
    # We know that the shape of the layer will be [batch_size img_size img_size num_channels]
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

    # Fully connected layer takes input x and produces wx+b.Since, these are matrices,
    # we use matmul function in Tensorflow
    layer = tf.matmul(input, weights) + biases
    if use_relu:
        layer = tf.nn.relu(layer, name='activation')

    tf.summary.histogram('activations', layer)

    return layer


def show_progress(iteration, epoch, feed_dict_train, feed_dict_validate, val_loss):
    acc = session.run(accuracy, feed_dict=feed_dict_train)
    #val_acc = session.run(accuracy, feed_dict=feed_dict_validate)
    summary, val_acc = session.run([merged, accuracy], feed_dict=feed_dict_validate)

    # Tensorboard:
    test_writer.add_summary(summary, iteration)

    #print('Accuracy at step %s: %s' % (iteration, val_acc))
    msg = "Iteration {4} Training Epoch {0} --- Training Accuracy: {1:>6.1%}, Validation Accuracy: {2:>6.1%},  Validation Loss: {3:.3f}"
    print("%s %s" % (msg.format(epoch + 1, acc, val_acc, val_loss, iteration +1), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))


def train(start, num_iterations):

    run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)

    for i in range(start, num_iterations):
        x_batch, y_true_batch = data.train.next_batch(batch_size)
        x_valid_batch, y_valid_batch = data.valid.next_batch(batch_size)


        feed_dict_tr = {x: x_batch,
                        y_true: y_true_batch}
        feed_dict_val = {x: x_valid_batch,
                         y_true: y_valid_batch}


        run_metadata = tf.RunMetadata()
        summary, _ = session.run([merged, optimizer],
                                 feed_dict_tr,
                                 options=run_options,
                                 run_metadata=run_metadata)

        if i % int(data.train.num_examples/batch_size) == 0:

            val_loss = session.run(cost, feed_dict=feed_dict_val)
            epoch = int(i / int(data.train.num_examples/batch_size))
            show_progress(i, epoch, feed_dict_tr, feed_dict_val, val_loss)

            saver.save(session, args.outputdir + '/cc-predictor-model', global_step=epoch)


            # For tensorboard:
            train_writer.add_run_metadata(run_metadata, 'step%03d' % i)
            train_writer.add_summary(summary, i)

            #if epoch == 10:
            #       tf.saved_model.simple_save(session,
            #                                                          "cc-predictor-model",
            #                                                          inputs={"x": x, "y_true": y_true},
            #                                                          outputs={"infer": y_pred_cls})

            #       builder = tf.saved_model.builder.SavedModelBuilder('cc-predictor-model')
            #       builder.add_meta_graph_and_variables(session, [tf.saved_model.tag_constants.SERVING])
            #       builder.save()
            #       return


            # Export the model for use with other languages
            """
            builder = tf.saved_model.builder.SavedModelBuilder("cc-predictor-model-%d" % epoch)
            tensor_info_x = tf.saved_model.utils.build_tensor_info(x)
            tensor_info_y = tf.saved_model.utils.build_tensor_info(y_pred)

            prediction_signature = (
                    tf.saved_model.signature_def_utils.build_signature_def(
                            inputs={'input': tensor_info_x},
                            outputs={'output': tensor_info_y},
                            method_name=tf.saved_model.signature_constants.PREDICT_METHOD_NAME))



            builder.add_meta_graph_and_variables(
                    session, [tf.saved_model.tag_constants.SERVING],
                    signature_def_map={
                            tf.saved_model.signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY:
                            prediction_signature,
                    },
            )

            builder.save(as_text=False)
            """
            #tf.saved_model.simple_save(session, "cc-predictor-model-%d" % i, inputs=feed_dict_tr, outputs=feed_dict_val)

if __name__ == "__main__":

    os.system("rm -rf /tmp/tf ")
    retval = os.system("mkdir -p " + args.outputdir)
    if retval != 0:
        sys.stderr.write('Could not create outputdir\n')
        sys.exit(63)

    #Adding Seed so that random initialization is consistent
    seed(1)
    set_random_seed(2)

    batch_size = 32
    #batch_size = 64


    #Prepare input data
    #classes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    classes = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    num_classes = len(classes)

    # Train/validation split 25% of the data will automatically be used for validation
    validation_size = 0.30
    #
    #validation_size = 0.40

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

    # GOLANG note that we must label the input-tensor! (name='x')
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

    # Argument to droupout is the probability of _keeping_ the neuron:
    #dropped = tf.nn.dropout(layer_fc1, 0.8)
    dropped = tf.nn.dropout(layer_fc1, 0.3)
    layer_fc2 = create_fc_layer(input=dropped,
        num_inputs=128,
        num_outputs=num_classes,
        use_relu=False)

    # Softmax is a function that maps [-inf, +inf] to [0, 1] similar as Sigmoid. But Softmax also
    # normalizes the sum of the values(output vector) to be 1.
    y_pred = tf.nn.softmax(layer_fc2,name='y_pred')
    # GOLANG note that we must label the infer-operation!!
    y_pred_cls = tf.argmax(y_pred, axis=1, name="infer")


    # Class penalty
    #class_weights = tf.constant([[1-2943.0/28512.0, 1-2140.0/28512.0, 1-1048.0/28512.0,
    #            1-921.0/28512.0, 1-796.0/28512.0, 1-1144.0/28512.0, 1-1493.0/28512.0,
    #                                                         1-4104.0/28512.0, 1-13923.0/28512.0]])

    #scaled_logits = tf.multiply(layer_fc2, class_weights)
    #cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits=scaled_logits,
    #                                                        labels=y_true)
    # Logit is a function that maps probabilities [0, 1] to [-inf, +inf].
    cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits=layer_fc2,
                                                           labels=y_true)

    #scaled_err = tf.multiply(cross_entrpy, class_wheigts)
    #cost = tf.reduce_mean(scaled_err)

    cost = tf.reduce_mean(cross_entropy)
    optimizer = tf.train.AdamOptimizer(learning_rate=1e-5).minimize(cost)
    # This converge fast and should be good enough for our use. Lets use this.
    # TTruning it off for testing :
    #correct_prediction = tf.abs(tf.subtract(y_pred_cls, y_true_cls)) <= 1

    correct_prediction = tf.equal(y_pred_cls, y_true_cls)
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    # Create a summary to monitor cost tensor
    tf.summary.scalar("loss", cost)
    # Create a summary to monitor accuracy tensor
    tf.summary.scalar("Accuracy", accuracy)

    #tf.summary.scalar('cross_entropy', cross_entropy)

    # merge all summaries into a single "operation" which we can execute in a session
    merged = tf.summary.merge_all()
    # create log writer object

    train_writer = tf.summary.FileWriter(logs_path + '/train', session.graph)
    test_writer  = tf.summary.FileWriter(logs_path + '/test')

    session.run(tf.global_variables_initializer())

    saver = tf.train.Saver(max_to_keep=100000)
    path = args.inputdir
    start = 0

    #if path is not None and tf.train.latest_checkpoint(path) is not None:
    if path is not None and args.epoch is not None:
        print("Loading %s  %s " % (path, path + "/cc-predictor-model-" + args.epoch))
        #saver.restore(session, tf.train.latest_checkpoint(path))
        print("Try restoring model ..")
        saver.restore(session, path + "/cc-predictor-model-" + args.epoch)
        #found_num = re.search(r'\d+$', tf.train.latest_checkpoint(path))
        #print(tf.train.latest_checkpoint(path))
        #epoch = int(found_num.group(0))
        print("Training from epoch %d" % int(args.epoch))
        start = int(args.epoch)  * int(data.train.num_examples/batch_size) + 2
        print("StartIter: %d " % start)
    train(start, num_iterations=10000000)
