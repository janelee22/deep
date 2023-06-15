# -*- coding: utf-8 -*-
"""drnn_0602.ipynb의 사본

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1C0n-6kCHpwohXJrZRDoum93Ktl7ZCA5M

#import
"""

import pandas as pd
import numpy as np
import librosa
import os
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical
from sklearn.preprocessing import LabelEncoder
import random

from google.colab import drive

drive.mount('/content/drive', force_remount=True)

###GPU 러닝
import tensorflow as tf
device_name = tf.test.gpu_device_name()
if device_name != '/device:GPU:0':
  raise SystemError('GPU device not found')
print('Found GPU at: {}'.format(device_name))



"""#pad_seqence"""

def pad_sequences(sequences, max_length=None, padding_value=0):
    if max_length is None:
        max_length = max([len(seq) for seq in sequences])
    max_length = min(max_length, 100000)  # Limit max_length to 10000

    padded_sequences = np.full((len(sequences), max_length), padding_value, dtype=np.float32)
    for i, seq in enumerate(sequences):
        if len(seq) > max_length:
            padded_sequences[i] = seq[:max_length]  # Truncate the sequence if it exceeds max_length
        else:
            padded_sequences[i, :len(seq)] = seq  # Pad the sequence if it is shorter than max_length

    return padded_sequences

"""#Dataload"""

from keras.utils import pad_sequences

def VCTKdataload(wavPath,num,sample_rate,resample_rate):

      
    Fils1 = os.listdir(wavPath)
    if num == 0:
      num = len(Fils1)

    wavedata = {}
    wavelen = []
    wavelabel_train = np.array([])
    wavelabel_test = np.array([])
    
    labels =  pd.DataFrame()
    print(Fils1)
    for i in Fils1[:num]:
      Fils2 = os.listdir(wavPath+'/'+i)
      if '.ipynb_checkpoints' in Fils2:
        Fils2.remove('.ipynb_checkpoints')
      print(Fils2)
      
      wavedata[i] = []
      id=[]
      fname=[]
      
      for j in Fils2:
        w,sr = librosa.load(wavPath+'/'+i+'/'+j, sr = sample_rate)
        rw = librosa.resample(w, orig_sr = sample_rate ,target_sr = resample_rate)
        wavedata[i].append(rw)
        id.append(j.split('_')[0])
        fname.append(j)                                                   #wavdata 추출
   
      df =pd.DataFrame({'ID':id,'fname':fname})
      labels = pd.concat([labels, df], axis=0)
   
    labels = labels.loc[labels['ID'].isin(Fils1[:num])]
    labels = labels.reset_index(drop=True)
   
    y=labels['ID'].values

    encoder = LabelEncoder()
    y = encoder.fit_transform(y)

    y = np.array(y)                                    #레이블

    for i in Fils1[:num]:
      
      a = max([len(seq) for seq in wavedata[i]])
      wavelen.append(a)

    # max_length = max(wavelen)
    max_length=10000
    print(max_length)
    for idx, i in enumerate(Fils1[:num]):
      b = pad_sequences(wavedata[i], max_length=100000, padding_value=0)  # Use max_length=10000
      print(b.shape)  # Zero-padding

    # for idx,i in enumerate(Fils1[:num]):
    #   b = pad_sequences(wavedata[i], max_length, padding_value=0)
    #   print(b.shape)             #제로패딩
      
      if idx == 0:
        data = b
      else:
        data = np.concatenate((data,b),axis=0)


    print(data.shape)
     
    x_train,x_test,y_train,y_test = train_test_split(data,y,test_size = 0.20, stratify=y)  

    x_train_tensor = tf.expand_dims(x_train, axis=-1)
    x_test_tensor = tf.expand_dims(x_test, axis=-1)
  

  
    train_labels_categorical = to_categorical(y_train)
    test_labels_categorical = to_categorical(y_test)
    
    
    
    print('traintensor shape:',x_train_tensor.shape)
    print('testtensor shape:',x_test_tensor.shape)
    print('trainlabel shape:',train_labels_categorical.shape)
    print('testlabel shape:',test_labels_categorical.shape)

    return x_train_tensor,x_test_tensor,train_labels_categorical,test_labels_categorical

wavPath = '/content/drive/MyDrive/wav48'

x_train,x_test,y_train,y_test = VCTKdataload(wavPath,41,48000,24000)

"""# DRNN"""

import copy
import itertools
import numpy as np
import tensorflow as tf
from tensorflow.nn import softmax
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, SimpleRNNCell,Flatten
from tensorflow.keras import Input
from tensorflow.keras.layers import RNN, SimpleRNNCell, LSTMCell, GRUCell

import copy
import itertools
import numpy as np
import tensorflow as tf
from tensorflow.nn import softmax
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, SimpleRNNCell,Flatten
from tensorflow.keras import Input
from tensorflow.keras.layers import RNN, SimpleRNNCell, LSTMCell, GRUCell

def dRNN(cell, inputs, rate, scope='default'):

    n_steps = len(inputs)
    if rate < 0 or rate >= n_steps:
        raise ValueError('The \'rate\' variable needs to be adjusted.')
    print("Building layer: %s, input length: %d, dilation rate: %d, input dim: %d." % (scope, n_steps, rate, inputs[0].shape[1]))

    # make the length of inputs divide 'rate', by using zero-padding
    EVEN = (n_steps % rate) == 0
    if not EVEN:
        # Create a tensor in shape (batch_size, input_dims), which all elements are zero.  
        # This is used for zero padding
        zero_tensor = tf.zeros_like(inputs[0])
        dialated_n_steps = n_steps // rate + 1
        print("=====> %d time points need to be padded. " % (dialated_n_steps * rate - n_steps))
        print("=====> Input length for sub-RNN: %d" % (dialated_n_steps))
        for i_pad in range(dialated_n_steps * rate - n_steps):
            inputs.append(zero_tensor)
    else:
        dialated_n_steps = n_steps // rate
        print("=====> Input length for sub-RNN: %d" % (dialated_n_steps))


    dilated_inputs = [tf.concat(inputs[i * rate:(i + 1) * rate], axis=0) for i in range(dialated_n_steps)]

   
    # building a dilated RNN with reformatted (dilated) inputs
    dilated_outputs = tf.keras.layers.RNN(cell, return_sequences=True, return_state=False, go_backwards=False, 
                                          stateful=False, time_major=True, unroll=False, input_shape=(dialated_n_steps, inputs[0].shape[1]),
                                          name=scope)(tf.stack(dilated_inputs))


    splitted_outputs = tf.split(dilated_outputs, num_or_size_splits=rate, axis=1)
    # unrolled_outputs = [output for sublist in splitted_outputs for output in sublist]
    unrolled_outputs = tf.unstack(tf.concat(splitted_outputs, axis=0))
    # remove padded zeros
    outputs = unrolled_outputs[:n_steps]

    return outputs

def _contruct_cells(hidden_structs, cell_type):
    """
    This function constructs a list of cells.
    """
    # error checking
    if cell_type not in ["RNN", "LSTM", "GRU"]:
        raise ValueError("The cell type is not currently supported.")

    # define cells
    cells = []
    for hidden_dims in hidden_structs:
        if cell_type == "RNN":
            cell = SimpleRNNCell(hidden_dims)
        elif cell_type == "LSTM":
            cell = LSTMCell(hidden_dims)
        elif cell_type == "GRU":
            cell = GRUCell(hidden_dims)
        cells.append(cell)

    return cells

class DRNNclassification(Model):
    def __init__(self,  n_classes, rate, dilations, hidden_dims,cell_type):
        super(DRNNclassification, self).__init__()
        
        assert (len(hidden_dims) == len(dilations))
        
        self.softmax = tf.keras.activations.softmax
        self.cells = _contruct_cells(hidden_dims, cell_type)
        self.rate = rate
        self.classifier = Dense(n_classes, activation='softmax')
      
        self.dense1 = Dense(hidden_dims[-1], activation='relu')
      
        self.dense2 = Dense(hidden_dims[-1]*dilations[0], activation='relu')
        
        
        self.flatten=Flatten()

    def call(self, x):
        x = tf.unstack(x, axis=1)  # Convert tensor to a list
        for idx, i in enumerate(dilations):
            x = dRNN(self.cells[idx], x, i)
        
        if dilations[0] == 1:
            x = self.dense1(x[-1])
        else:
            hidden_outputs_ = tf.concat([x[i] for i in range(-dilations[0], 0, 1)], axis=1)
            x = self.dense2(hidden_outputs_)
        
        return self.classifier(x)

"""#Train"""

from tensorflow.keras.losses import CategoricalCrossentropy
from tensorflow.keras.optimizers import Adam,RMSprop


n_classes = 41
dilations = [32,64,128,256,512,1024]
hidden_dims = [50]*6
cell_type = 'GRU'

model = DRNNclassification(n_classes,2,dilations, hidden_dims, cell_type)
# rms = tf.keras.optimizers.legacy.RMSprop(learning_rate=0.001, rho=0.9, epsilon=None, decay=0.9)
optimizer = tf.keras.optimizers.Adam(learning_rate=0.003)
model.compile(loss='CategoricalCrossentropy', optimizer=optimizer, metrics=['accuracy'])

model.fit(x_train, y_train, batch_size=128, epochs=1000, validation_data=(x_test, y_test))

model.evaluate(x_test,y_test,verbose=1)
