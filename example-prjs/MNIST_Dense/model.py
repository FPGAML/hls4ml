import os
import shutil
import hls4ml
import yaml
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.models import model_from_json
from qkeras import *
import json
from tensorflow.keras import layers
from sklearn.metrics import accuracy_score

## Function to create a simple Convolutional Neural Network model
def create_model():
    # Create a model
    model = tf.keras.Sequential()
    model.add(layers.Flatten(input_shape=(8, 8)))  # Flattens the 28x28 input into a 784-dimensional vector
    model.add(layers.Dense(64, activation='relu'))
    model.add(layers.Dense(32, activation='relu'))
    model.add(layers.Dense(10, activation='softmax'))

    return model

## Function to save model architecture, weights, and configuration
def save_model(model, name=None):
    if name is None:
        name = model.name
    model.save(name + '.h5')
    model.save_weights(name + '_weights.h5')
    with open(name + '.json', 'w') as outfile:
        outfile.write(model.to_json())
    return

if __name__ == '__main__':
    
    #Remove files and directories
    file_list = ['tb_data', 'my-*', 'conv2d*', 'a.out']
    for item in file_list:
        if '*' in item:
            matching_items = [f for f in os.listdir() if f.startswith(item.replace('*', ''))]
            for matching_item in matching_items:
                if os.path.isfile(matching_item):
                    os.remove(matching_item)
                elif os.path.isdir(matching_item):
                    shutil.rmtree(matching_item)
        else:
            if os.path.isfile(item):
                os.remove(item)
            elif os.path.isdir(item):
                shutil.rmtree(item)
    
    # Create directory
    os.makedirs('tb_data', exist_ok=True)
    
    
    # (x_train, y_train), (x_test, y_test) = tf.keras.datasets.fashion_mnist.load_data()
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    x_train = x_train / 255.0
    x_test = x_test / 255.0
    
    # # # Resize the images to 4x4
    x_train_resized = tf.image.resize(x_train[..., np.newaxis], size=(8, 8)).numpy()
    x_test_resized = tf.image.resize(x_test[..., np.newaxis], size=(8, 8)).numpy()

    # Convert labels to one-hot encoding
    y_train = tf.keras.utils.to_categorical(y_train, num_classes=10)
    y_test = tf.keras.utils.to_categorical(y_test, num_classes=10)

    ## Create and compile the model
    model = create_model()
    # Compile the model
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    ## Train the model
    model.fit(x_train_resized, y_train, epochs=10)

    ## Evaluate the model on test data
    test_loss, test_acc = model.evaluate(x_test_resized, y_test)
    print(f"Test Loss: {test_loss}")
    print(f"Test Accuracy: {test_acc}")

    ## Save input features and model predictions
    np.savetxt('tb_data/tb_input_features.dat', x_test_resized.reshape(x_test_resized.shape[0], -1), fmt='%f')
    np.savetxt('tb_data/tb_output_predictions.dat', np.argmax(model.predict(x_test_resized), axis=1), fmt='%d')
    np.savetxt('tb_data/y_test_labels.dat', y_test, fmt='%d')  ## Save y_test labels as well
    save_model(model, name='dense')
    print(hls4ml.__version__)

 
    ## Configure and convert the model for Catapult HLS
    config_ccs = {
    'KerasJson': 'dense.json',
    'KerasH5': 'dense_weights.h5',
    'OutputDir': 'my-Catapult-test',
    'ProjectName': 'myproject',
    'Part': 'xcku115-flvb2104-2-i',
    'XilinxPart': 'xcku115-flvb2104-2-i',
    'InputData': 'tb_data/tb_input_features.dat',
    'OutputPredictions': 'tb_data/tb_output_predictions.dat',
    'ClockPeriod': 5,
    'Backend': 'Catapult',
    'IOType': 'io_stream',
    'HLSConfig': {
        'Model': {
            'Precision': 'ac_fixed<16,6,true>',
            'ReuseFactor': 1,
            'Strategy': 'Latency',
        },
        'LayerName': {
            'softmax': {
                'Precision': 'ac_fixed<16,6,false>',
                'Strategy': 'Stable',
                'exp_table_t': 'ac_fixed<18,8,true>',
                'inv_table_t': 'ac_fixed<18,8,true>',
                'table_size': 1024,
            },
            'Dense1_input': {
                'Precision': {
                    'result': 'ac_fixed<16,6,true>',
                },
            },
            'relu1': {
                'Precision': {
                    'result': 'ac_fixed<7,1,true>',
                },
            },
            'Dense2_input': {
                'Precision': {
                    'result': 'ac_fixed<16,6,true>',
                },
            },
            'Dense1': {
                'Precision': {
                    'bias': 'ac_fixed<6,1,true>',
                    'weight': 'ac_fixed<6,1,true>',
                },
            },
            'Dense2': {
                'Precision': {
                    'bias': 'ac_fixed<6,1,true>',
                    'weight': 'ac_fixed<6,1,true>',
                },
            },
        },
    },
}

    print("\n============================================================================================")
    print("HLS4ML converting keras model/Catapult to HLS C++")
    hls_model_ccs = hls4ml.converters.keras_to_hls(config_ccs)
    hls_model_ccs.compile()
    ccs_hls_model_predictions = hls_model_ccs.predict(x_test_resized)
    print('QKeras Accuracy: {}'.format(accuracy_score(np.argmax(y_test, axis=1), np.argmax(model.predict(x_test_resized), axis=1))))
    print('hls4ml Accuracy: {}'.format(accuracy_score(np.argmax(y_test, axis=1), np.argmax(ccs_hls_model_predictions, axis=1))))
    hls_model_ccs.build(csim=True, synth=True, cosim=True, validation=True, vsynth=True)
    # hls_model_ccs.build()
 
