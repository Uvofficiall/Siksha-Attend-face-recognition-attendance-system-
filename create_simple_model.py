import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
import os

def create_simple_face_model():
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(128, 128, 1)),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Flatten(),
        Dense(128, activation='relu'),
        Dense(128, activation='linear', name='embeddings')
    ])
    
    model.compile(optimizer='adam', loss='mse')
    return model

def main():
    os.makedirs('static/models', exist_ok=True)
    
    model = create_simple_face_model()
    model.save('static/models/simple_face_model.keras')
    
    print("Simple face model created successfully!")
    model.summary()

if __name__ == "__main__":
    main()