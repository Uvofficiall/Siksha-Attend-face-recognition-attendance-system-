# Siksha Attend - Automated Attendance System

[**Live Demo**](https://siksha-attend.onrender.com)

## Setup Instructions

### 1. Firebase Setup
1. Create a Firebase project at https://console.firebase.google.com
2. Enable Authentication and Firestore Database
3. Generate service account credentials:
   - Go to Project Settings > Service Accounts
   - Generate new private key
   - Save as `firebase-credentials.json` in project root
4. Update Firebase config in `templates/index.html`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Download Face Recognition Models
Create `static/models` directory and download face-api.js models:
- tiny_face_detector_model-weights_manifest.json
- face_landmark_68_model-weights_manifest.json  
- face_recognition_model-weights_manifest.json

### 4. Environment Setup
1. Copy `.env` file and update values
2. Set your Firebase credentials path
3. Generate a secure secret key

### 5. Database Schema
Create these Firestore collections:

#### schools
```json
{
  "name": "ABC School",
  "address": "School Address",
  "district": "District Name",
  "device_ids": []
}
```

#### students  
```json
{
  "name": "Student Name",
  "roll_no": "12",
  "school_id": "school_doc_id",
  "class": "8",
  "embeddings": {}
}
```

#### teachers
```json
{
  "name": "Teacher Name", 
  "email": "teacher@school.com",
  "school_id": "school_doc_id",
  "role": "teacher"
}
```

### 6. Run Application
```bash
python app.py
```

## Features

- **Facial Recognition**: Automatic attendance using webcam
- **Offline Support**: Works without internet, syncs when online
- **Manual Fallback**: Manual attendance marking option
- **Role-based Access**: Teacher, Admin, Super Admin roles
- **Real-time Sync**: Automatic background synchronization
- **Reports**: Attendance reports and analytics

## Usage

1. **Login**: Use email/password with role selection
2. **Teacher Dashboard**: 
   - Start camera for facial recognition
   - Mark manual attendance
   - View today's attendance
3. **Admin Dashboard**:
   - View attendance reports
   - Manage students
   - Monitor sync status

## Offline Functionality

- Attendance records stored in IndexedDB when offline
- Automatic sync when internet connection restored
- Manual sync option available
- Queue status indicator

## Security

- Firebase Authentication for secure login
- JWT token validation on API endpoints
- Device ID tracking for audit trails
- Secure face embedding storage
- 
## License

This project is licensed under the [Apache License 2.0](LICENSE).

## Authors

- [YUVRAJ SHARMA](https://github.com/Uvofficiall)
