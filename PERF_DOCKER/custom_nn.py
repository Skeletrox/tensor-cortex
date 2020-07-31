import numpy as np
import tensorflow as tf
import requests
import re
import argparse
from json import dumps

Sequential = tf.keras.models.Sequential
LSTM = tf.keras.layers.LSTM
Dense = tf.keras.layers.Dense
LambdaCallback = tf.keras.callbacks.LambdaCallback

start_flag = False
done_flag = False


class KerasModel(object):
    def __init__(self, source, count, **kwargs):
        self.meta = kwargs
        self.source = source
        self.count = count
        self.model = Sequential()
        self.char_to_index = None
        self.index_to_char = None
        self.dataset_size = -1
        self.input_x = None
        self.output_y = None
        self.longest_word_size = None
        self.num_chars = -1
        self.data = None

    def load_data(self):
        source_url = "http://names.drycodes.com/{}?nameOptions={}".format(
            self.count, self.source)
        r = requests.get(source_url)

        try:
            response = r.json()
            names_duplicates = list(
                map(lambda s: re.sub(r'-_', ' ', s), response))
            names = list(set(names_duplicates))
            names = list(map(lambda s: s.lower() + '.', names))

            # Create a char to index dict to map the text to sequences of numbers
            self.char_to_index = dict((chr(i + 96), i) for i in range(1, 27))
            self.char_to_index[' '] = 0
            self.char_to_index['.'] = 27
            self.index_to_char = dict(
                (v, k) for (k, v) in self.char_to_index.items())

            # Create a one-hot encoding tensor of dimensions
            # (input_size, longest_word_size, num_chars)
            dataset_size = len(names)
            longest_word_size = len(max(names, key=len))
            num_chars = len(self.char_to_index)
            input_x = np.zeros((dataset_size, longest_word_size, num_chars))
            output_y = np.zeros((dataset_size, longest_word_size, num_chars))

            # Populate the one-hot vector
            for i in range(dataset_size):
                name = list(names[i])
                for j, c in enumerate(name):
                    try:
                        input_x[i, j, self.char_to_index[c]] = 1
                    except KeyError:
                        pass

                    if j < len(name) - 1:  # Predict the next letter
                        try:
                            output_y[i, j, self.char_to_index[name[j + 1]]] = 1
                        except KeyError:
                            pass

            self.input_x = input_x
            self.output_y = output_y
            self.dataset_size = dataset_size
            self.longest_word_size = longest_word_size
            self.num_chars = num_chars
            self.data = names

            return True, None

        except Exception as e_e:
            return False, e_e

    def make_name(self):
        name = []
        x = np.zeros((1, self.longest_word_size, self.num_chars))
        end = False
        i = 0

        while not end:
            probs = list(self.model.predict(x)[0, i])
            probs = probs / np.sum(probs)
            index = np.random.choice(range(self.num_chars), p=probs)
            if i == self.longest_word_size - 2:
                character = '.'
                end = True
            else:
                character = self.index_to_char[index]
            name.append(character)
            x[0, i + 1, index] = 1
            i += 1
            if character == '.':
                end = True

        return ''.join(name)

    def generate_name_loop(self, epoch, *args):
        if epoch % 25 == 0:

            print('Names generated after epoch: {}'.format(epoch))

            names = [self.make_name() for _ in range(6)]

            print(names)

    def return_names(self, count=5):
        return [self.make_name() for _ in range(count)]

    def create_model(self):
        self.model.add(
            LSTM(
                256,
                input_shape=(self.longest_word_size, self.num_chars),
                return_sequences=True))
        self.model.add(Dense(self.num_chars, activation='softmax'))
        self.model.compile(loss='categorical_crossentropy', optimizer='adam')

    def train_model(self):
        name_generator = LambdaCallback(on_epoch_end=self.generate_name_loop)
        self.model.fit(
            self.input_x,
            self.output_y,
            batch_size=128,
            epochs=1000,
            callbacks=[name_generator],
            verbose=0)

    def save_model(self, path='model.ckpt'):
        self.model.save(path)


def main(source, count):
    km = KerasModel(source, count)
    km.load_data()
    km.create_model()
    km.train_model()
    with open("names.txt", "w") as names:
        names.write(dumps(km.return_names(5)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--source", required=True, default="boy_names", action="store")
    parser.add_argument(
        "-c", "--count", required=True, default=350, action="store")
    args = parser.parse_args()
    source = args.source
    count = int(args.count)
    main(source, count)
