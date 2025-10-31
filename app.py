from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv
from datetime import datetime
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
from pymongo import MongoClient
from bson import ObjectId
try:
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    print("Scikit-learn not available, using basic similarity")
    SKLEARN_AVAILABLE = False

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
recognition_data_collection = db.recognition_data

# Load face detection model
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Simple face recognition without TensorFlow
face_model = None
print("Using basic face recognition without TensorFlow")

def extract_face_embedding(face_image):
    """Extract basic face features"""
    try:
        face_resized = cv2.resize(face_image, (64, 64))
        face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        return face_gray.flatten().astype('float32') / 255.0
    except Exception as e:
        print(f"Face embedding extraction error: {e}")
        return None

def compare_faces(embedding1, embedding2, threshold=0.65):
    """Compare two face embeddings using multiple similarity metrics"""
    try:
        if embedding1 is None or embedding2 is None:
            return False, 0.0
        
        # Normalize embeddings
        embedding1 = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
        embedding2 = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
        
        if SKLEARN_AVAILABLE:
            try:
                similarity = cosine_similarity([embedding1], [embedding2])[0][0]
            except:
                similarity = 1.0 - np.linalg.norm(embedding1 - embedding2) / 2.0
        else:
            similarity = np.corrcoef(embedding1, embedding2)[0, 1]
            if np.isnan(similarity):
                similarity = 0.0
            
        # Ensure similarity is between 0 and 1
        similarity = max(0.0, min(1.0, similarity))
        is_match = similarity >= threshold
        return is_match, float(similarity)
        
    except Exception as e:
        print(f"Face comparison error: {e}")
        return False, 0.0

def save_recognition_data(student_id, embedding, similarity):
    """Save recognition data for continuous learning"""
    try:
        recognition_data_collection.insert_one({
            'student_id': student_id,
            'embedding': embedding.tolist(),
            'similarity': similarity,
            'timestamp': datetime.utcnow().isoformat(),
            'used_for_learning': False
        })
        
        # Update student embeddings if high confidence (>0.85)
        if similarity > 0.85:
            student = students_collection.find_one({'_id': ObjectId(student_id)})
            if student:
                existing_embeddings = student.get('face_embeddings', [])
                existing_embeddings.append(embedding.tolist())
                
                # Keep only best 7 embeddings
                if len(existing_embeddings) > 7:
                    existing_embeddings = existing_embeddings[-7:]
                
                students_collection.update_one(
                    {'_id': ObjectId(student_id)},
                    {'$set': {
                        'face_embeddings': existing_embeddings,
                        'last_recognition_update': datetime.utcnow().isoformat()
                    }}
                )
                
    except Exception as e:
        print(f"Error saving recognition data: {e}")

# Role-based UID validation
ROLE_UIDS = {
    'teacher': 'YkkyFCnR0kgJfq3Q0GyzBOyUPAI2',
    'admin': '8C1EXFLKcjgRCkaqrLHd0GuNfjs2', 
    'super_admin': 'kkeqYgaGRRW8k81fbciC1IfKiIr2'
}

def validate_user_role(token, required_role=None):
    """Validate Firebase token and optionally check role"""
    try:
        # For now, skip Firebase token validation since we're using MongoDB
        # In production, you would validate the Firebase token here
        return True
    except Exception as e:
        return False

print("Siksha Attend initialized with MongoDB Atlas and basic face recognition")

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



@app.route('/api/sync_attendance', methods=['POST'])
def sync_attendance():
    try:
        attendance_records = request.json.get('records', [])
        synced_count = 0
        
        for record in attendance_records:
            # Check if record already exists (prevent duplicates)
            existing_record = attendance_collection.find_one({
                'student_id': record['student_id'],
                'timestamp_iso': record['timestamp_iso'],
                'device_id': record['device_id']
            })
            
            if not existing_record:
                attendance_collection.insert_one({
                    'student_id': record['student_id'],
                    'school_id': record['school_id'],
                    'timestamp_iso': record['timestamp_iso'],
                    'method': record['method'],
                    'device_id': record['device_id'],
                    'synced_at': datetime.utcnow().isoformat()
                })
                synced_count += 1
        
        return jsonify({'success': True, 'synced_count': synced_count, 'total_records': len(attendance_records)})
    
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
            if 'face_registered' in doc:
                student_data['face_registered'] = doc['face_registered']
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
        
        # Extract face region with padding for better accuracy
        x, y, w, h = faces[0]
        padding = int(0.2 * min(w, h))
        x_start = max(0, x - padding)
        y_start = max(0, y - padding)
        x_end = min(frame.shape[1], x + w + padding)
        y_end = min(frame.shape[0], y + h + padding)
        
        face_roi = frame[y_start:y_end, x_start:x_end]
        
        # Extract face embedding
        current_embedding = extract_face_embedding(face_roi)
        
        if current_embedding is None:
            return jsonify({'recognized': False, 'message': 'Failed to extract face features'})
        
        # Compare with registered faces using multiple embeddings
        best_match = None
        best_similarity = 0.0
        
        cursor = students_collection.find({
            'school_id': 'S1', 
            'face_registered': True,
            '$or': [
                {'face_embeddings': {'$exists': True}},
                {'face_embedding': {'$exists': True}}
            ]
        })
        
        for student_doc in cursor:
            max_similarity = 0.0
            
            # Check multiple embeddings if available
            if 'face_embeddings' in student_doc and student_doc['face_embeddings']:
                similarities = []
                for stored_embedding_list in student_doc['face_embeddings']:
                    stored_embedding = np.array(stored_embedding_list)
                    is_match, similarity = compare_faces(current_embedding, stored_embedding, threshold=0.65)
                    similarities.append(similarity)
                
                # Use average of top 3 similarities for better accuracy
                similarities.sort(reverse=True)
                top_similarities = similarities[:3]
                max_similarity = sum(top_similarities) / len(top_similarities)
            
            # Fallback to single embedding
            elif 'face_embedding' in student_doc:
                stored_embedding = np.array(student_doc['face_embedding'])
                is_match, max_similarity = compare_faces(current_embedding, stored_embedding, threshold=0.65)
            
            # Check if this is the best match
            if max_similarity >= 0.65 and max_similarity > best_similarity:
                best_similarity = max_similarity
                best_match = student_doc
        
        if best_match:
            # Save recognition data for continuous learning
            save_recognition_data(str(best_match['_id']), current_embedding, best_similarity)
            
            return jsonify({
                'recognized': True,
                'student': {
                    'id': str(best_match['_id']),
                    'name': best_match['name'],
                    'roll_no': best_match['roll_no'],
                    'similarity': best_similarity
                },
                'confidence': best_similarity
            })
        
        return jsonify({'recognized': False, 'message': 'No matching face found'})
            
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
        
        # Extract face region with padding for better accuracy
        x, y, w, h = faces[0]
        padding = int(0.2 * min(w, h))
        x_start = max(0, x - padding)
        y_start = max(0, y - padding)
        x_end = min(frame.shape[1], x + w + padding)
        y_end = min(frame.shape[0], y + h + padding)
        
        face_roi = frame[y_start:y_end, x_start:x_end]
        
        # Extract face embedding
        embedding = extract_face_embedding(face_roi)
        
        if embedding is None:
            return jsonify({'success': False, 'message': 'Failed to extract face features'})
        
        # Get existing embeddings or create new list
        student = students_collection.find_one({'_id': ObjectId(student_id)})
        existing_embeddings = student.get('face_embeddings', []) if student else []
        
        # Add new embedding to list (keep max 5 for better accuracy)
        existing_embeddings.append(embedding.tolist())
        if len(existing_embeddings) > 5:
            existing_embeddings = existing_embeddings[-5:]
        
        # Store multiple face embeddings for better accuracy
        students_collection.update_one(
            {'_id': ObjectId(student_id)},
            {'$set': {
                'face_registered': True,
                'face_embeddings': existing_embeddings,
                'face_embedding': embedding.tolist(),  # Keep single for backward compatibility
                'registered_at': datetime.utcnow().isoformat(),
                'total_captures': len(existing_embeddings)
            }}
        )
        
        return jsonify({
            'success': True, 
            'message': f'Face registered successfully ({len(existing_embeddings)} captures)',
            'total_captures': len(existing_embeddings)
        })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/add_sample_students', methods=['POST'])
def add_sample_students():
    try:
        sample_students = [
            {'name': 'Rahul Kumar', 'roll_no': '1', 'class': '10A', 'school_id': 'S1'},
            {'name': 'Priya Sharma', 'roll_no': '2', 'class': '10A', 'school_id': 'S1'},
            {'name': 'Amit Singh', 'roll_no': '3', 'class': '10B', 'school_id': 'S1'},
            {'name': 'Sneha Patel', 'roll_no': '4', 'class': '10B', 'school_id': 'S1'},
            {'name': 'Vikash Yadav', 'roll_no': '5', 'class': '10A', 'school_id': 'S1'}
        ]
        
        result = students_collection.insert_many(sample_students)
        added_count = len(result.inserted_ids)
        
        return jsonify({'success': True, 'message': f'{added_count} sample students added'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/add_student', methods=['POST'])
def add_student():
    try:
        data = request.json
        student_data = {
            'name': data['name'],
            'roll_no': data['roll_no'],
            'class': data['class'],
            'school_id': data.get('school_id', 'S1'),
            'enrollment_date': datetime.utcnow().isoformat()
        }
        
        # Add optional fields if provided
        if data.get('date_of_birth'):
            student_data['date_of_birth'] = data['date_of_birth']
        if data.get('gender'):
            student_data['gender'] = data['gender']
        if data.get('parent_name'):
            student_data['parent_name'] = data['parent_name']
        if data.get('contact_number'):
            student_data['contact_number'] = data['contact_number']
        
        result = students_collection.insert_one(student_data)
        
        return jsonify({
            'success': True, 
            'message': 'Student enrolled successfully',
            'student_id': str(result.inserted_id)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/update_student/<student_id>', methods=['PUT'])
def update_student(student_id):
    try:
        data = request.json
        update_data = {
            'name': data['name'],
            'roll_no': data['roll_no'],
            'class': data['class'],
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Update optional fields if provided
        if data.get('date_of_birth'):
            update_data['date_of_birth'] = data['date_of_birth']
        if data.get('gender'):
            update_data['gender'] = data['gender']
        if data.get('parent_name'):
            update_data['parent_name'] = data['parent_name']
        if data.get('contact_number'):
            update_data['contact_number'] = data['contact_number']
        
        result = students_collection.update_one(
            {'_id': ObjectId(student_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Student updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Student not found'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete_student/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    try:
        result = students_collection.delete_one({'_id': ObjectId(student_id)})
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Student deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Student not found'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/check_attendance/<student_id>', methods=['GET'])
def check_attendance(student_id):
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        start_date = f"{today}T00:00:00Z"
        end_date = f"{today}T23:59:59Z"
        
        existing_record = attendance_collection.find_one({
            'student_id': student_id,
            'timestamp_iso': {'$gte': start_date, '$lte': end_date}
        })
        
        if existing_record:
            return jsonify({
                'already_marked': True,
                'message': 'Attendance already marked today',
                'timestamp': existing_record['timestamp_iso'],
                'method': existing_record['method']
            })
        else:
            return jsonify({'already_marked': False})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/face_stats/<student_id>', methods=['GET'])
def get_face_stats(student_id):
    try:
        student = students_collection.find_one({'_id': ObjectId(student_id)})
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        face_registered = student.get('face_registered', False)
        total_captures = len(student.get('face_embeddings', []))
        
        # Get recognition accuracy from recent recognitions
        recent_recognitions = list(recognition_data_collection.find({
            'student_id': student_id
        }).sort('timestamp', -1).limit(10))
        
        avg_accuracy = 0.0
        if recent_recognitions:
            avg_accuracy = sum(r['similarity'] for r in recent_recognitions) / len(recent_recognitions)
        
        return jsonify({
            'face_registered': face_registered,
            'total_captures': total_captures,
            'average_accuracy': round(avg_accuracy * 100, 1),
            'recognition_count': len(recent_recognitions),
            'accuracy_status': 'Excellent' if avg_accuracy > 0.9 else 'Good' if avg_accuracy > 0.8 else 'Fair'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print("Starting Siksha Attend with MongoDB Atlas...")
    print(f"Open: http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
