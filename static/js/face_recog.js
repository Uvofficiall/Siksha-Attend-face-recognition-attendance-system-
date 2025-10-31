class FaceRecognition {
    constructor() {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.isRecording = false;
        this.stream = null;
        this.recognitionInterval = null;
        this.trackingInterval = null;
    }

    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: 640, 
                    height: 480,
                    facingMode: 'user'
                } 
            });
            
            this.video.srcObject = this.stream;
            this.video.style.display = 'block';
            document.getElementById('camera-placeholder').style.display = 'none';
            
            this.isRecording = true;
            this.updateStatus('Camera started - Position your face in the frame');
            
            // Start face tracking every 200ms for smooth box movement
            this.trackingInterval = setInterval(() => {
                this.trackFace();
            }, 200);
            
            // Start face recognition every 2 seconds
            this.recognitionInterval = setInterval(() => {
                this.detectAndRecognize();
            }, 2000);
            
            return true;
        } catch (error) {
            console.error('Camera access error:', error);
            this.updateStatus('Camera access denied or not available');
            return false;
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.recognitionInterval) {
            clearInterval(this.recognitionInterval);
            this.recognitionInterval = null;
        }
        
        if (this.trackingInterval) {
            clearInterval(this.trackingInterval);
            this.trackingInterval = null;
        }
        
        this.clearFaceBox();
        this.video.style.display = 'none';
        document.getElementById('camera-placeholder').style.display = 'flex';
        this.isRecording = false;
        this.updateStatus('Camera stopped');
    }

    captureFrame() {
        if (!this.isRecording) return null;
        
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        this.ctx.drawImage(this.video, 0, 0);
        
        return this.canvas.toDataURL('image/jpeg', 0.8);
    }

    async detectAndRecognize() {
        if (!this.isRecording) return;
        
        const imageData = this.captureFrame();
        if (!imageData) return;
        
        try {
            this.updateStatus('Detecting faces...');
            
            // First detect faces
            const detectResponse = await fetch('/api/detect_face', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });
            
            const detectResult = await detectResponse.json();
            
            if (detectResult.faces_detected === 0) {
                this.clearFaceBox();
                this.updateStatus('No face detected - Please position your face in the frame');
                return;
            }
            
            // Draw green box around detected face
            this.drawFaceBox(detectResult.faces[0]);
            this.updateStatus(`${detectResult.faces_detected} face(s) detected - Recognizing...`);
            
            // Then recognize the face
            const recognizeResponse = await fetch('/api/recognize_face', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });
            
            const recognizeResult = await recognizeResponse.json();
            
            if (recognizeResult.recognized) {
                const student = recognizeResult.student;
                const accuracy = (student.similarity * 100).toFixed(1);
                const accuracyEmoji = accuracy > 90 ? '🎯' : accuracy > 80 ? '✅' : '⚠️';
                
                this.updateStatus(`${accuracyEmoji} Recognized: ${student.name} (${student.roll_no}) - ${accuracy}% accuracy`);
                
                // Check if attendance already marked today
                const checkResponse = await fetch(`/api/check_attendance/${student.id}`);
                const checkResult = await checkResponse.json();
                
                if (checkResult.already_marked) {
                    this.updateStatus(`⚠️ ${student.name} already marked present today at ${new Date(checkResult.timestamp).toLocaleTimeString()}`);
                    
                    // Stop recognition for longer to avoid repeated messages
                    clearInterval(this.recognitionInterval);
                    setTimeout(() => {
                        if (this.isRecording) {
                            this.recognitionInterval = setInterval(() => {
                                this.detectAndRecognize();
                            }, 2000);
                        }
                    }, 10000);
                } else {
                    // Mark attendance
                    await this.markAttendance(student.id, 'face');
                    this.updateStatus(`🎉 ${student.name} marked present - AI Confidence: ${accuracy}%`);
                    
                    // Stop recognition for a few seconds to avoid duplicate entries
                    clearInterval(this.recognitionInterval);
                    setTimeout(() => {
                        if (this.isRecording) {
                            this.recognitionInterval = setInterval(() => {
                                this.detectAndRecognize();
                            }, 2000);
                        }
                    }, 5000);
                }
                
            } else {
                this.updateStatus(`🔍 ${recognizeResult.message || 'Face not recognized - Try different angle'}`);
            }
            
        } catch (error) {
            console.error('Recognition error:', error);
            this.updateStatus('Recognition error - Please try again');
        }
    }

    async markAttendance(studentId, method) {
        try {
            const attendanceRecord = {
                student_id: studentId,
                school_id: 'S1',
                timestamp_iso: new Date().toISOString(),
                method: method,
                device_id: 'web_' + Date.now()
            };
            
            // Store locally first
            await this.storeLocalAttendance(attendanceRecord);
            
            // Try to sync immediately
            await this.syncAttendance();
            
        } catch (error) {
            console.error('Error marking attendance:', error);
        }
    }

    async storeLocalAttendance(record) {
        try {
            const existingRecords = JSON.parse(localStorage.getItem('pendingAttendance') || '[]');
            existingRecords.push(record);
            localStorage.setItem('pendingAttendance', JSON.stringify(existingRecords));
            
            // Update UI
            this.updateAttendanceList();
            
        } catch (error) {
            console.error('Error storing local attendance:', error);
        }
    }

    async syncAttendance() {
        try {
            const pendingRecords = JSON.parse(localStorage.getItem('pendingAttendance') || '[]');
            
            if (pendingRecords.length === 0) {
                document.getElementById('syncStatus').textContent = 'All synced';
                return;
            }
            
            const token = localStorage.getItem('authToken');
            const response = await fetch('/api/sync_attendance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ records: pendingRecords })
            });
            
            if (response.ok) {
                localStorage.removeItem('pendingAttendance');
                document.getElementById('syncStatus').textContent = 'Synced';
            } else {
                document.getElementById('syncStatus').textContent = `${pendingRecords.length} pending`;
            }
            
        } catch (error) {
            console.error('Sync error:', error);
            const pendingRecords = JSON.parse(localStorage.getItem('pendingAttendance') || '[]');
            document.getElementById('syncStatus').textContent = `${pendingRecords.length} pending`;
        }
    }

    async updateAttendanceList() {
        try {
            const listElement = document.getElementById('attendanceList');
            const pendingRecords = JSON.parse(localStorage.getItem('pendingAttendance') || '[]');
            
            if (pendingRecords.length === 0) {
                listElement.innerHTML = `
                    <div class="text-center py-12">
                        <div class="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-indigo-100">
                            <svg class="w-10 h-10 text-indigo-500" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                            </svg>
                        </div>
                        <p class="text-gray-500 font-medium">No attendance marked yet</p>
                        <p class="text-gray-400 text-sm mt-1">Start scanning to see records</p>
                    </div>
                `;
                return;
            }
            
            // Get student data
            const students = await this.getStudents();
            const studentsMap = {};
            students.forEach(student => {
                studentsMap[student.id] = student;
            });
            
            listElement.innerHTML = '';
            
            // Show recent records first
            const recentRecords = pendingRecords.slice(-10).reverse();
            
            recentRecords.forEach(record => {
                const student = studentsMap[record.student_id];
                if (student) {
                    const time = new Date(record.timestamp_iso).toLocaleTimeString();
                    listElement.innerHTML += `
                        <div class="bg-gray-50 rounded-2xl p-4 flex justify-between items-center border border-gray-200">
                            <div class="flex items-center space-x-3">
                                <div class="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white font-bold">
                                    ${student.name.charAt(0)}
                                </div>
                                <div>
                                    <div class="font-semibold text-gray-900">${student.name}</div>
                                    <div class="text-sm text-gray-500">Roll: ${student.roll_no}</div>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="text-sm font-medium text-gray-900">${time}</div>
                                <div class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                    record.method === 'face' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                                }">
                                    ${record.method === 'face' ? '🤖' : '✋'} ${record.method}
                                </div>
                            </div>
                        </div>
                    `;
                }
            });
            
        } catch (error) {
            console.error('Error updating attendance list:', error);
        }
    }

    async getStudents() {
        try {
            const token = localStorage.getItem('authToken');
            const response = await fetch('/api/students/S1', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                return await response.json();
            }
            return [];
        } catch (error) {
            console.error('Error fetching students:', error);
            return [];
        }
    }

    drawFaceBox(face) {
        if (!face) return;
        
        // Create or get existing face box overlay
        let faceBox = document.getElementById('face-detection-box');
        if (!faceBox) {
            faceBox = document.createElement('div');
            faceBox.id = 'face-detection-box';
            faceBox.style.position = 'absolute';
            faceBox.style.border = '3px solid #10B981';
            faceBox.style.borderRadius = '8px';
            faceBox.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
            faceBox.style.pointerEvents = 'none';
            faceBox.style.zIndex = '10';
            faceBox.style.transition = 'all 0.3s ease';
            
            // Add face detected label
            const label = document.createElement('div');
            label.style.position = 'absolute';
            label.style.top = '-30px';
            label.style.left = '0';
            label.style.backgroundColor = '#10B981';
            label.style.color = 'white';
            label.style.padding = '4px 8px';
            label.style.borderRadius = '4px';
            label.style.fontSize = '12px';
            label.style.fontWeight = 'bold';
            label.textContent = '✓ Face Detected';
            faceBox.appendChild(label);
            
            this.video.parentElement.appendChild(faceBox);
        }
        
        // Calculate position relative to video element
        const videoRect = this.video.getBoundingClientRect();
        const videoParentRect = this.video.parentElement.getBoundingClientRect();
        
        const scaleX = videoRect.width / this.video.videoWidth;
        const scaleY = videoRect.height / this.video.videoHeight;
        
        const x = face.x * scaleX;
        const y = face.y * scaleY;
        const width = face.w * scaleX;
        const height = face.h * scaleY;
        
        faceBox.style.left = `${x}px`;
        faceBox.style.top = `${y}px`;
        faceBox.style.width = `${width}px`;
        faceBox.style.height = `${height}px`;
        faceBox.style.display = 'block';
    }
    
    async trackFace() {
        if (!this.isRecording) return;
        
        const imageData = this.captureFrame();
        if (!imageData) return;
        
        try {
            const response = await fetch('/api/detect_face', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: imageData })
            });
            
            const result = await response.json();
            
            if (result.faces_detected > 0) {
                this.drawFaceBox(result.faces[0]);
            } else {
                this.clearFaceBox();
            }
        } catch (error) {
            // Silently handle tracking errors
        }
    }
    
    clearFaceBox() {
        const faceBox = document.getElementById('face-detection-box');
        if (faceBox) {
            faceBox.style.display = 'none';
        }
    }

    updateStatus(message) {
        const statusElement = document.getElementById('recognition-status');
        if (statusElement) {
            statusElement.innerHTML = `
                <div class="flex items-center justify-center space-x-2 text-blue-700">
                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    <span class="font-medium">${message}</span>
                </div>
            `;
        }
    }
}

// Initialize face recognition
let faceRecognition;

function initializeApp() {
    faceRecognition = new FaceRecognition();
    
    // Camera controls
    document.getElementById('startCamera').addEventListener('click', async () => {
        const success = await faceRecognition.startCamera();
        if (success) {
            document.getElementById('startCamera').disabled = true;
            document.getElementById('stopCamera').disabled = false;
        }
    });
    
    document.getElementById('stopCamera').addEventListener('click', () => {
        faceRecognition.stopCamera();
        document.getElementById('startCamera').disabled = false;
        document.getElementById('stopCamera').disabled = true;
    });
    
    // Manual attendance
    document.getElementById('markManual').addEventListener('click', async () => {
        const studentSelect = document.getElementById('studentSelect');
        const studentId = studentSelect.value;
        
        if (!studentId) {
            alert('Please select a student');
            return;
        }
        
        try {
            // Check if attendance already marked today
            const checkResponse = await fetch(`/api/check_attendance/${studentId}`);
            const checkResult = await checkResponse.json();
            
            if (checkResult.already_marked) {
                const studentName = studentSelect.options[studentSelect.selectedIndex].text;
                alert(`${studentName} is already marked present today at ${new Date(checkResult.timestamp).toLocaleTimeString()}`);
                studentSelect.value = '';
                return;
            }
            
            await faceRecognition.markAttendance(studentId, 'manual');
            studentSelect.value = '';
            
        } catch (error) {
            console.error('Error checking attendance:', error);
            alert('Error checking attendance status');
        }
    });
    
    // Manual sync
    document.getElementById('manualSync').addEventListener('click', () => {
        faceRecognition.syncAttendance();
    });
    
    // Load students for manual selection
    loadStudentsForManual();
    
    // Update attendance list
    faceRecognition.updateAttendanceList();
    
    // Auto sync every 30 seconds
    setInterval(() => {
        faceRecognition.syncAttendance();
    }, 30000);
}

async function loadStudentsForManual() {
    try {
        const students = await faceRecognition.getStudents();
        const select = document.getElementById('studentSelect');
        
        select.innerHTML = '<option value="">👥 Choose a student...</option>';
        
        students.forEach(student => {
            const option = document.createElement('option');
            option.value = student.id;
            option.textContent = `${student.name} (${student.roll_no})`;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading students:', error);
    }
}