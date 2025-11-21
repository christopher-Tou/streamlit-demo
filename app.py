import os
import json
import base64
import logging
from typing import Dict, Any, Optional

from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 2. 初始化 Flask 应用
app = Flask(__name__, static_folder='static', template_folder='templates')

# 3. 配置 Gemini 客户端
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    logger.warning("GOOGLE_API_KEY not found in environment variables.")
    client = None
else:
    client = genai.Client(api_key=api_key)

# --- 常量定义 ---

SYSTEM_PROMPT = """
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

# --- 辅助函数 ---

def normalize_key(root_key: str) -> str:
    """规范化音调表示 (例如将 C# 转换为 Db/C#)"""
    normalization_map = {
        'C#': 'Db/C#', 'Db': 'Db/C#',
        'D#': 'Eb', 
        'F#': 'Gb/F#', 'Gb': 'Gb/F#',
        'G#': 'Ab',
        'A#': 'Bb'
    }
    return normalization_map.get(root_key, root_key)

# --- 路由定义 ---

@app.route('/')
def index():
    # 确保 templates/index.html 存在，否则返回提示
    try:
        return render_template('index.html')
    except Exception:
        return "Error: index.html not found. Please ensure you have a 'templates' folder with an index.html file.", 404

# 改进：动态生成 Manifest，无需在磁盘写入文件
@app.route('/manifest.json')
def manifest():
    content = {
        "name": "竹笛变调大师",
        "short_name": "竹笛大师",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f0fdf4",
        "theme_color": "#064e3b",
        "icons": [{"src": "/static/icon.svg", "type": "image/svg+xml", "sizes": "512x512"}]
    }
    return jsonify(content)

# 改进：动态生成 Service Worker，无需在磁盘写入文件
@app.route('/sw.js')
def service_worker():
    js_content = """
    self.addEventListener('install', e => e.waitUntil(caches.open('dizi-v1').then(c => c.addAll(['/', '/static/icon.svg']))));
    self.addEventListener('fetch', e => e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))));
    """
    return Response(js_content, mimetype='application/javascript')

# 如果你有真实的 icon 文件放在 static 目录，这个路由可以保留
# 如果没有，建议在 HTML 中直接用 emoji 或 base64 图片代替
@app.route('/static/icon.svg')
def app_icon():
    return send_from_directory('static', 'icon.svg')

@app.route('/api/analyze', methods=['POST'])
def analyze_audio():
    if not client:
        logger.error("API call failed: Server API Key not configured.")
        return jsonify({"error": "API Key not configured on server"}), 500

    try:
        data = request.get_json()
        if not data:
             return jsonify({"error": "Invalid JSON"}), 400

        audio_base64 = data.get('audio')
        mime_type = data.get('mime_type', 'audio/webm') # 允许前端传递 mime_type

        if not audio_base64:
            return jsonify({"error": "No audio data received"}), 400

        logger.info(f"Analyzing audio... Format: {mime_type}")

        # 调用 Gemini API
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Part.from_bytes(
                    data=base64.b64decode(audio_base64),
                    mime_type=mime_type
                ),
                SYSTEM_PROMPT
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        if not response.text:
            logger.error("Gemini returned empty response.")
            return jsonify({"error": "Empty response from AI"}), 500

        # 解析结果
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"JSON Decode Error. Raw text: {response.text}")
            return jsonify({"error": "AI returned invalid JSON"}), 500
        
        raw_root = result.get('root', 'C')
        final_key = normalize_key(raw_root)

        return jsonify({
            "key": final_key,
            "explanation": result.get('explanation', 'AI Analysis complete.')
        })

    except Exception as e:
        logger.exception("An unexpected error occurred during analysis.")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 本地开发时自动创建所需文件夹结构，避免报错
    if not os.path.exists('static'):
        os.makedirs('static')
    if not os.path.exists('templates'):
        os.makedirs('templates')
        # 创建一个占位 index.html 防止启动报错
        if not os.path.exists('templates/index.html'):
            with open('templates/index.html', 'w', encoding='utf-8') as f:
                f.write('<h1>Server is running. Please replace this with your actual HTML file.</h1>')

    # 启动应用
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
