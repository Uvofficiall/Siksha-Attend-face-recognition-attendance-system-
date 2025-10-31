#!/usr/bin/env python3
"""
Initialize sample data for Siksha Attend system
Run this script after setting up Firebase credentials
"""

import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
firebase_admin.initialize_app(cred)
db = firestore.client()

def create_sample_school():
    """Create a sample school"""
    school_data = {
        'name': 'ABC Rural School',
        'address': 'Village ABC, District XYZ',
        'district': 'XYZ District',
        'device_ids': ['dev_sample123']
    }
    
    school_ref = db.collection('schools').add(school_data)
    print(f"Created school with ID: {school_ref[1].id}")
    return school_ref[1].id

def create_sample_students(school_id):
    """Create sample students"""
    students = [
        {'name': 'Yuvraj Sharma', 'roll_no': '1', 'class': '12', 'school_id': school_id},
        {'name': 'Abhishek Kumar', 'roll_no': '2', 'class': '8', 'school_id': school_id},
        {'name': 'Amit Singh', 'roll_no': '3', 'class': '8', 'school_id': school_id},
        {'name': 'Sunita Devi', 'roll_no': '4', 'class': '8', 'school_id': school_id},
        {'name': 'Ravi Yadav', 'roll_no': '5', 'class': '8', 'school_id': school_id}
    ]
    
    student_ids = []
    for student in students:
        student_ref = db.collection('students').add(student)
        student_ids.append(student_ref[1].id)
        print(f"Created student: {student['name']} with ID: {student_ref[1].id}")
    
    return student_ids

def create_sample_teacher(school_id):
    """Create sample teacher user"""
    try:
        # Create Firebase Auth user
        user = auth.create_user(
            email='teacher@abcschool.com',
            password='teacher123',
            display_name='Mr. Sharma'
        )
        
        # Create teacher document
        teacher_data = {
            'name': 'Mr. Sharma',
            'email': 'teacher@abcschool.com',
            'school_id': school_id,
            'role': 'teacher',
            'uid': user.uid
        }
        
        db.collection('teachers').add(teacher_data)
        print(f"Created teacher: {teacher_data['name']} with email: {teacher_data['email']}")
        
    except Exception as e:
        print(f"Error creating teacher: {e}")

def create_sample_admin(school_id):
    """Create sample admin user"""
    try:
        # Create Firebase Auth user
        user = auth.create_user(
            email='admin@abcschool.com',
            password='admin123',
            display_name='Admin User'
        )
        
        # Create admin document
        admin_data = {
            'name': 'Admin User',
            'email': 'admin@abcschool.com',
            'school_id': school_id,
            'role': 'admin',
            'uid': user.uid
        }
        
        db.collection('teachers').add(admin_data)
        print(f"Created admin: {admin_data['name']} with email: {admin_data['email']}")
        
    except Exception as e:
        print(f"Error creating admin: {e}")

def main():
    print("Initializing sample data for Siksha Attend...")
    
    # Create school
    school_id = create_sample_school()
    
    # Create students
    student_ids = create_sample_students(school_id)
    
    # Create teacher and admin users
    create_sample_teacher(school_id)
    create_sample_admin(school_id)
    
    print("\nSample data initialization complete!")
    print("\nLogin credentials:")
    print("Teacher - Email: teacher@abcschool.com, Password: teacher123")
    print("Admin - Email: admin@abcschool.com, Password: admin123")
    print(f"\nSchool ID: {school_id}")

if __name__ == '__main__':
    main()