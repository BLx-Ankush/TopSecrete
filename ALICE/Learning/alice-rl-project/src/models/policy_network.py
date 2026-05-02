from tensorflow import keras
from tensorflow.keras import layers

class PolicyNetwork:
    def __init__(self, input_shape, action_space, hidden_layers=[128, 128]):
        self.model = self.build_model(input_shape, action_space, hidden_layers)

    def build_model(self, input_shape, action_space, hidden_layers):
        model = keras.Sequential()
        model.add(layers.Input(shape=input_shape))
        
        for units in hidden_layers:
            model.add(layers.Dense(units, activation='relu'))
        
        model.add(layers.Dense(action_space, activation='softmax'))
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        
        return model

    def predict(self, state):
        state = state.reshape(1, -1)  # Reshape for a single sample
        return self.model.predict(state)

    def train(self, states, actions, epochs=10, batch_size=32):
        self.model.fit(states, actions, epochs=epochs, batch_size=batch_size)