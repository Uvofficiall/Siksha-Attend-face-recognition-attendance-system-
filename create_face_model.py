import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
import os

def create_face_recognition_model():
    """Create a simple CNN model for face recognition embeddings"""
    
    model = Sequential([
        # First convolutional block
        Conv2D(32, (3, 3), activation='relu', input_shape=(128, 128, 1)),
        MaxPooling2D((2, 2)),
        
        # Second convolutional block
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        
        # Third convolutional block
        Conv2D(128, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        
        # Fourth convolutional block
        Conv2D(256, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        
        # Flatten and dense layers
        Flatten(),
        Dense(512, activation='relu'),
        Dropout(0.5),
        Dense(256, activation='relu'),
        Dropout(0.3),
        
        # Output layer for embeddings (128-dimensional)
        Dense(128, activation='linear', name='embeddings')
    ])
    
    model.compile(
        optimizer='adam',
        loss='mse',
        metrics=['mae']
    )
    
    return model

def main():
    # Create models directory if it doesn't exist
    os.makedirs('static/models', exist_ok=True)
    
    # Create and save the model
    model = create_face_recognition_model()
    model.save('static/models/face_recognition_model.h5')
    
    print("Face recognition model created and saved to static/models/face_recognition_model.h5")
    print("Model summary:")
    model.summary()

if __name__ == "__main__":
    main()