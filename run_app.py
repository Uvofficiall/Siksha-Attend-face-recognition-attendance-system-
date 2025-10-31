from flask import Flask, render_template, jsonify, request
import os

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Siksha Attend</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center">
        <div class="max-w-md mx-auto bg-white rounded-3xl shadow-2xl p-8 text-center">
            <div class="w-20 h-20 bg-blue-500 rounded-full mx-auto mb-6 flex items-center justify-center">
                <span class="text-white text-2xl font-bold">SA</span>
            </div>
            <h1 class="text-3xl font-bold text-gray-800 mb-4">Siksha Attend</h1>
            <p class="text-gray-600 mb-8">Smart Attendance System</p>
            
            <div class="space-y-4">
                <button onclick="window.location.href='/setup'" class="w-full bg-blue-500 text-white py-3 rounded-2xl font-semibold hover:bg-blue-600">
                    Setup Students
                </button>
                <button onclick="window.location.href='/teacher'" class="w-full bg-green-500 text-white py-3 rounded-2xl font-semibold hover:bg-green-600">
                    Teacher Dashboard
                </button>
                <button onclick="window.location.href='/admin'" class="w-full bg-purple-500 text-white py-3 rounded-2xl font-semibold hover:bg-purple-600">
                    Admin Dashboard
                </button>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/setup')
def setup():
    return '''
    <h1>Setup Page</h1>
    <p>Students setup coming soon...</p>
    <a href="/">Back to Home</a>
    '''

@app.route('/teacher')
def teacher():
    return '''
    <h1>Teacher Dashboard</h1>
    <p>Face recognition coming soon...</p>
    <a href="/">Back to Home</a>
    '''

@app.route('/admin')
def admin():
    return '''
    <h1>Admin Dashboard</h1>
    <p>Admin features coming soon...</p>
    <a href="/">Back to Home</a>
    '''

if __name__ == '__main__':
    print("🚀 Siksha Attend starting...")
    print("📱 Open: http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080)