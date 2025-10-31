# Face Recognition Models

Download the following face-api.js model files and place them in this directory:

## Required Models

1. **Tiny Face Detector**
   - `tiny_face_detector_model-weights_manifest.json`
   - `tiny_face_detector_model-shard1.bin`

2. **Face Landmark 68 Point**
   - `face_landmark_68_model-weights_manifest.json`
   - `face_landmark_68_model-shard1.bin`

3. **Face Recognition**
   - `face_recognition_model-weights_manifest.json`
   - `face_recognition_model-shard1.bin`
   - `face_recognition_model-shard2.bin`

## Download Links

You can download these models from the face-api.js GitHub repository:
https://github.com/justadudewhohacks/face-api.js/tree/master/weights

## Alternative CDN Loading

If you prefer to load models from CDN, update the model loading path in `face_recog.js`:

```javascript
await faceapi.nets.tinyFaceDetector.loadFromUri('https://cdn.jsdelivr.net/gh/justadudewhohacks/face-api.js@master/weights');
```