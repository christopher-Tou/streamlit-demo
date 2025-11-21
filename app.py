import os
import json
import base64
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 配置 Gemini 客户端
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/icon.svg')
def app_icon():
    return send_from_directory('static', 'icon.svg')

@app.route('/api/analyze', methods=['POST'])
def analyze_audio():
    if not client:
        return jsonify({"error": "API Key not configured on server"}), 500

    try:
        data = request.json
        audio_base64 = data.get('audio')
        
        if not audio_base64:
            return jsonify({"error": "No audio data"}), 400

        # 构建提示词
        prompt = """
        You are an expert musicologist specializing in Chinese Traditional Music (Min Yue) and Dizi (Bamboo Flute).
        
        Your Task:
        Identify the "System Key" (1 = Do) of the provided audio.

        CRITICAL ANALYSIS RULES:
        1. The audio is a MONOPHONIC melody (single instrument). Do NOT look for chords or polyphony.
        2. Ignore background noise. Focus ONLY on the flute melody.
        3. Identify the "Resting Tone" or "Cadence Note". In Chinese music, this is often the "Gong" (Do) or "Yu" (La) note.
        4. If the melody ends on 'A' and sounds minor (Yu mode), the relative major system is 'C'. Report 'C'.
        5. If the melody ends on 'G' and sounds major (Gong mode), the system is 'G'.
        6. Listen to the ENTIRE clip to find the tonal center.

        Return ONLY a JSON object:
        {
            "root": "C", 
            "explanation": "Detected a melody resolving to A (Yu mode). In the Pentatonic system, A Minor relative is C Major. Therefore, 1 = C."
        }
        
        Standard Roots to use: C, Db, D, Eb, E, F, Gb, G, Ab, A, Bb, B.
        """

        # 调用 Gemini API
        response = client.models.generate_content(
            model='gemini-2.0-flash', # 使用最新的 Flash 模型
            contents=[
                types.Part.from_bytes(
                    data=base64.b64decode(audio_base64),
                    mime_type="audio/webm"
                ),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        if not response.text:
            return jsonify({"error": "Empty response from AI"}), 500

        result = json.loads(response.text)
        
        # 规范化 Sharp/Flat
        root = result.get('root', 'C')
        normalization_map = {
            'C#': 'Db/C#', 'Db': 'Db/C#',
            'D#': 'Eb', 
            'F#': 'Gb/F#', 'Gb': 'Gb/F#',
            'G#': 'Ab',
            'A#': 'Bb'
        }
        if root in normalization_map:
            root = normalization_map[root]
            
        return jsonify({
            "key": root,
            "explanation": result.get('explanation', 'AI Analysis complete.')
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 确保 static 文件夹存在
    if not os.path.exists('static'):
        os.makedirs('static')
        
    # 创建简单的 manifest 和 sw 文件 (如果需要)
    with open('static/manifest.json', 'w') as f:
        json.dump({
            "name": "竹笛变调大师",
            "short_name": "竹笛大师",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f0fdf4",
            "theme_color": "#064e3b",
            "icons": [{"src": "/icon.svg", "type": "image/svg+xml", "sizes": "512x512"}]
        }, f)
        
    with open('static/sw.js', 'w') as f:
        f.write("""
        self.addEventListener('install', e => e.waitUntil(caches.open('dizi-v1').then(c => c.addAll(['/', '/icon.svg']))));
        self.addEventListener('fetch', e => e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))));
        """)

    app.run(debug=True, port=5000)
