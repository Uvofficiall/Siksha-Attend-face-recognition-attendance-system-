from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>Siksha Attend Test</h1><p>App is working!</p>'

if __name__ == '__main__':
    print("Starting test app on http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080)