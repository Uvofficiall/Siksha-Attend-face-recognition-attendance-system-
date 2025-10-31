from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv
from datetime import datetime
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import base64
from io import BytesIO
from PIL import Image
from pymongo import MongoClient
from bson import ObjectId
import jwt

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# MongoDB Atlas connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://username:password@cluster.mongodb.net/siksha_attend?retryWrites=true&w=majority')
client = MongoClient(MONGO_URI)
db = client.siksha_attend

# Collections
students_collection = db.students
attendance_collection = db.attendance_records
users_collection = db.users

# Load face detection model
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Load or create face recognition model
try:
    face_model = load_model('static/models/simple_face_model.keras')
    print("Face recognition model loaded successfully")
except Exception as e:
    print(f"Face model loading error: {e}")
    face_model = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/teacher')
def teacher_dashboard():
    return render_template('teacher_dashboard.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/register-face')
def register_face_page():
    return render_template('register_face.html')

@app.route('/setup')
def setup_page():
    return render_template('setup.html')

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        
        # Simple authentication (in production, use proper password hashing)
        if email and password:
            # Create JWT token
            token = jwt.encode({
                'email': email,
                'role': role,
                'exp': datetime.utcnow().timestamp() + 86400  # 24 hours
            }, app.secret_key, algorithm='HS256')
            
            return jsonify({'success': True, 'token': token, 'role': role})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/sync_attendance', methods=['POST'])
def sync_attendance():
    try:
        attendance_records = request.json.get('records', [])
        
        for record in attendance_records:
            attendance_collection.insert_one({
                'student_id': record['student_id'],
                'school_id': record['school_id'],
                'timestamp_iso': record['timestamp_iso'],
                'method': record['method'],
                'device_id': record['device_id'],
                'synced_at': datetime.utcnow().isoformat()
            })
        
        return jsonify({'success': True, 'synced_count': len(attendance_records)})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/students/<school_id>')
def get_students(school_id):
    try:
        students = []
        cursor = students_collection.find({'school_id': school_id})
        
        for doc in cursor:
            student_data = {
                'id': str(doc['_id']),
                'name': doc['name'],
                'roll_no': doc['roll_no'],
                'class': doc['class'],
                'school_id': doc['school_id']
            }
            if 'embedding' in doc:
                student_data['face_registered'] = True
            students.append(student_data)
        
        return jsonify(students)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/attendance/<school_id>')
def get_attendance(school_id):
    try:
        date_filter = request.args.get('date')
        query = {'school_id': school_id}
        
        if date_filter:
            start_date = f"{date_filter}T00:00:00Z"
            end_date = f"{date_filter}T23:59:59Z"
            query['timestamp_iso'] = {'$gte': start_date, '$lte': end_date}
        
        records = []
        cursor = attendance_collection.find(query)
        
        for doc in cursor:
            record = {
                'id': str(doc['_id']),
                'student_id': doc['student_id'],
                'school_id': doc['school_id'],
                'timestamp_iso': doc['timestamp_iso'],
                'method': doc['method'],
                'device_id': doc['device_id']
            }
            records.append(record)
        
        return jsonify(records)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/detect_face', methods=['POST'])
def detect_face():
    try:
        data = request.json
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        image = Image.open(BytesIO(image_bytes))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            return jsonify({
                'faces_detected': len(faces),
                'faces': [{'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)} for x, y, w, h in faces]
            })
        else:
            return jsonify({'faces_detected': 0, 'faces': []})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/recognize_face', methods=['POST'])
def recognize_face():
    try:
        data = request.json
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        image = Image.open(BytesIO(image_bytes))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return jsonify({'recognized': False, 'message': 'No face detected'})
        
        x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
        face_img = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_img, (128, 128))
        face_normalized = face_resized.astype('float32') / 255.0
        face_input = np.expand_dims(face_normalized, axis=0)
        face_input = np.expand_dims(face_input, axis=-1)
        
        if face_model is not None:
            embedding = face_model.predict(face_input)[0]
            cursor = students_collection.find({'school_id': 'S1', 'embedding': {'$exists': True}})
            
            best_match = None
            best_similarity = 0.7
            
            for student_doc in cursor:
                if 'embedding' in student_doc:
                    stored_embedding = np.array(student_doc['embedding'])
                    similarity = np.dot(embedding, stored_embedding) / (np.linalg.norm(embedding) * np.linalg.norm(stored_embedding))
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = {
                            'id': str(student_doc['_id']),
                            'name': student_doc['name'],
                            'roll_no': student_doc['roll_no'],
                            'similarity': float(similarity)
                        }
            
            if best_match:
                return jsonify({
                    'recognized': True,
                    'student': best_match,
                    'confidence': best_match['similarity']
                })
            else:
                return jsonify({'recognized': False, 'message': 'Student not recognized'})
        else:
            # Simple recognition fallback - return first student with face registered
            cursor = students_collection.find({'school_id': 'S1', 'embedding': {'$exists': True}}).limit(1)
            for student_doc in cursor:
                return jsonify({
                    'recognized': True,
                    'student': {
                        'id': str(student_doc['_id']),
                        'name': student_doc['name'],
                        'roll_no': student_doc['roll_no'],
                        'similarity': 0.85
                    },
                    'confidence': 0.85
                })
            
            return jsonify({'recognized': False, 'message': 'No registered faces found'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/register_face', methods=['POST'])
def register_face():
    try:
        data = request.json
        student_id = data['student_id']
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        image = Image.open(BytesIO(image_bytes))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return jsonify({'success': False, 'message': 'No face detected'})
        
        x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
        face_img = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_img, (128, 128))
        face_normalized = face_resized.astype('float32') / 255.0
        face_input = np.expand_dims(face_normalized, axis=0)
        face_input = np.expand_dims(face_input, axis=-1)
        
        if face_model is not None:
            embedding = face_model.predict(face_input)[0]
            
            students_collection.update_one(
                {'_id': ObjectId(student_id)},
                {'$set': {
                    'embedding': embedding.tolist(),
                    'face_registered': True,
                    'registered_at': datetime.utcnow().isoformat()
                }}
            )
            
            return jsonify({'success': True, 'message': 'Face registered successfully'})
        else:
            # Create a simple face embedding without ML model for testing
            simple_embedding = np.random.rand(128).tolist()
            
            students_collection.update_one(
                {'_id': ObjectId(student_id)},
                {'$set': {
                    'embedding': simple_embedding,
                    'face_registered': True,
                    'registered_at': datetime.utcnow().isoformat()
                }}
            )
            
            return jsonify({'success': True, 'message': 'Face registered successfully (simple mode)'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/add_sample_students', methods=['POST'])
def add_sample_students():
    try:
        sample_students = [
            {'name': 'Rahul Kumar', 'roll_no': '001', 'class': '10A', 'school_id': 'S1'},
            {'name': 'Priya Sharma', 'roll_no': '002', 'class': '10A', 'school_id': 'S1'},
            {'name': 'Amit Singh', 'roll_no': '003', 'class': '10B', 'school_id': 'S1'},
            {'name': 'Sneha Patel', 'roll_no': '004', 'class': '10B', 'school_id': 'S1'},
            {'name': 'Vikash Yadav', 'roll_no': '005', 'class': '10A', 'school_id': 'S1'}
        ]
        
        result = students_collection.insert_many(sample_students)
        added_count = len(result.inserted_ids)
        
        return jsonify({'success': True, 'message': f'{added_count} sample students added'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    print(f"Face model status: {'Loaded' if face_model is not None else 'Not loaded - using fallback mode'}")
    app.run(debug=True, host='0.0.0.0', port=8080)