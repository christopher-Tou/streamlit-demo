import os
import json
import logging
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. 配置页面 (这必须是第一个 Streamlit 命令)
st.set_page_config(
    page_title="竹笛变调大师",
    page_icon="🎵",
    layout="centered"
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# --- 核心逻辑区 ---

# 常量定义：专家提示词
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

def normalize_key(root_key):
    """规范化音调表示"""
    normalization_map = {
        'C#': 'Db/C#', 'Db': 'Db/C#',
        'D#': 'Eb', 
        'F#': 'Gb/F#', 'Gb': 'Gb/F#',
        'G#': 'Ab', 'A#': 'Bb'
    }
    return normalization_map.get(root_key, root_key)

def analyze_with_gemini(audio_bytes):
    """调用 Gemini API 进行分析"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ 未检测到 API Key。请在 Streamlit 后台设置 GOOGLE_API_KEY。")
        return None

    client = genai.Client(api_key=api_key)
    
    try:
        with st.spinner('🤖 AI 正在聆听并分析您的曲调...'):
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[
                    types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type="audio/webm"  # Streamlit 录音通常是 webm/wav
                    ),
                    SYSTEM_PROMPT
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if not response.text:
                st.error("AI 没有返回结果，请重试。")
                return None
                
            return json.loads(response.text)
            
    except Exception as e:
        st.error(f"分析出错: {str(e)}")
        logger.error(f"Gemini API Error: {e}")
        return None

# --- UI 界面区 ---

st.title("🎵 竹笛变调大师")
st.markdown("### AI 智能听音识调")
st.info("请吹奏一段旋律（建议包含结尾的主音），AI 将帮您分析这首曲子的**筒音（1=Do）**是什么调。")

# Streamlit 自带的录音组件 (这是最关键的替换，不用自己写 JS 了)
audio_input = st.audio_input("点击麦克风开始录音")

if audio_input is not None:
    # 获取录音数据的二进制内容
    audio_bytes = audio_input.read()
    
    # 直接显示音频播放器供用户回听
    # st.audio(audio_bytes) 
    
    # 开始分析
    result = analyze_with_gemini(audio_bytes)
    
    if result:
        raw_root = result.get('root', 'Unknown')
        final_key = normalize_key(raw_root)
        explanation = result.get('explanation', '无详细解释')
        
        # 显示结果卡片
        st.success(f"✅ 分析完成！")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(label="检测到的调性 (System Key)", value=f"1 = {final_key}")
        with col2:
            st.markdown(f"**AI 分析思路：**\n\n{explanation}")
            
        st.balloons()

# 页脚
st.markdown("---")
st.caption("Powered by Google Gemini 2.0 Flash & Streamlit")
