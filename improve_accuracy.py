#!/usr/bin/env python3
"""
Face Recognition Accuracy Improvement Script
This script helps improve face recognition accuracy by:
1. Analyzing existing face data
2. Optimizing embeddings
3. Removing poor quality samples
"""

import os
import numpy as np
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
import cv2

load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://username:password@cluster.mongodb.net/siksha_attend?retryWrites=true&w=majority')
client = MongoClient(MONGO_URI)
db = client.siksha_attend

students_collection = db.students
recognition_data_collection = db.recognition_data

def analyze_face_quality():
    """Analyze quality of stored face embeddings"""
    print("🔍 Analyzing face recognition quality...")
    
    students = list(students_collection.find({'face_registered': True}))
    
    for student in students:
        student_id = str(student['_id'])
        name = student['name']
        embeddings = student.get('face_embeddings', [])
        
        if len(embeddings) < 2:
            print(f"⚠️  {name}: Only {len(embeddings)} capture(s) - Need more samples")
            continue
        
        # Calculate similarity between embeddings
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i+1, len(embeddings)):
                emb1 = np.array(embeddings[i])
                emb2 = np.array(embeddings[j])
                
                # Normalize embeddings
                emb1 = emb1 / (np.linalg.norm(emb1) + 1e-8)
                emb2 = emb2 / (np.linalg.norm(emb2) + 1e-8)
                
                sim = cosine_similarity([emb1], [emb2])[0][0]
                similarities.append(sim)
        
        avg_similarity = np.mean(similarities) if similarities else 0
        
        if avg_similarity > 0.8:
            status = "✅ Excellent"
        elif avg_similarity > 0.7:
            status = "🟡 Good"
        else:
            status = "❌ Poor"
        
        print(f"{status} {name}: {len(embeddings)} samples, {avg_similarity:.3f} consistency")

def optimize_embeddings():
    """Remove poor quality embeddings and keep best ones"""
    print("\n🔧 Optimizing face embeddings...")
    
    students = list(students_collection.find({'face_registered': True}))
    
    for student in students:
        student_id = student['_id']
        name = student['name']
        embeddings = student.get('face_embeddings', [])
        
        if len(embeddings) <= 3:
            continue
        
        # Calculate quality score for each embedding
        embedding_scores = []
        
        for i, embedding in enumerate(embeddings):
            emb = np.array(embedding)
            emb = emb / (np.linalg.norm(emb) + 1e-8)
            
            # Calculate average similarity with other embeddings
            similarities = []
            for j, other_embedding in enumerate(embeddings):
                if i != j:
                    other_emb = np.array(other_embedding)
                    other_emb = other_emb / (np.linalg.norm(other_emb) + 1e-8)
                    sim = cosine_similarity([emb], [other_emb])[0][0]
                    similarities.append(sim)
            
            avg_sim = np.mean(similarities) if similarities else 0
            embedding_scores.append((i, avg_sim, embedding))
        
        # Sort by quality score and keep top 5
        embedding_scores.sort(key=lambda x: x[1], reverse=True)
        best_embeddings = [score[2] for score in embedding_scores[:5]]
        
        # Update database
        students_collection.update_one(
            {'_id': student_id},
            {'$set': {
                'face_embeddings': best_embeddings,
                'optimized_at': np.datetime64('now').isoformat()
            }}
        )
        
        print(f"🔧 {name}: Optimized from {len(embeddings)} to {len(best_embeddings)} embeddings")

def get_recognition_stats():
    """Get overall recognition statistics"""
    print("\n📊 Recognition Statistics:")
    
    total_students = students_collection.count_documents({'face_registered': True})
    
    # Students with multiple captures
    multi_capture_students = students_collection.count_documents({
        'face_registered': True,
        'face_embeddings.4': {'$exists': True}  # At least 5 captures
    })
    
    # Recent recognition data
    recent_recognitions = list(recognition_data_collection.find().sort('timestamp', -1).limit(100))
    
    if recent_recognitions:
        avg_accuracy = np.mean([r['similarity'] for r in recent_recognitions])
        high_accuracy_count = sum(1 for r in recent_recognitions if r['similarity'] > 0.9)
        
        print(f"📈 Total registered students: {total_students}")
        print(f"🎯 Students with 5+ captures: {multi_capture_students}")
        print(f"📊 Average recognition accuracy: {avg_accuracy:.1%}")
        print(f"🏆 High accuracy recognitions (>90%): {high_accuracy_count}/{len(recent_recognitions)}")
    else:
        print("📈 No recognition data available yet")

def main():
    print("🚀 Face Recognition Accuracy Improvement Tool")
    print("=" * 50)
    
    try:
        analyze_face_quality()
        optimize_embeddings()
        get_recognition_stats()
        
        print("\n✅ Face recognition optimization completed!")
        print("💡 Tips for 100% accuracy:")
        print("   • Capture 3-5 face samples per student")
        print("   • Ensure good lighting during capture")
        print("   • Capture from slightly different angles")
        print("   • System learns and improves over time")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()