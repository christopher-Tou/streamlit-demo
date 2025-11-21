import streamlit as st
import os
import json
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- 1. 配置与初始化 ---
st.set_page_config(
    page_title="竹笛变调大师",
    page_icon="🎋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

load_dotenv()

# 获取 API Key (优先从 Streamlit Secrets 获取，其次从环境变量)
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY and "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]

# --- 2. 乐理数据与常量 (从 types.ts 和 musicLogic.ts 移植) ---

# 难度定义
DIFF_RECOMMENDED = "RECOMMENDED" # Green
DIFF_INTERMEDIATE = "INTERMEDIATE" # Blue
DIFF_ADVANCED = "ADVANCED" # Red

DIFF_MAP = {
    '5': DIFF_RECOMMENDED, '2': DIFF_RECOMMENDED,
    '3': DIFF_INTERMEDIATE, '6': DIFF_INTERMEDIATE,
    '1': DIFF_ADVANCED, '7': DIFF_ADVANCED
}

DESC_MAP = {
    '5': '最常用 (Most Common)', '2': '常用 (Common)',
    '3': '指法较顺 (Smooth)', '6': '需按半孔 (Half-hole)',
    '1': '气息控制难 (Hard)', '7': '极少使用 (Rare)'
}

# 指法偏移量 (Offset)
TONGYIN_OFFSETS = {
    '5': 0, '2': 5, '3': 3, '6': 10, '1': 7, '7': 8
}

# 音名列表 (0-11)
MUSIC_KEYS = [
    {'name': 'C', 'value': 0}, {'name': 'Db/C#', 'value': 1}, {'name': 'D', 'value': 2},
    {'name': 'Eb', 'value': 3}, {'name': 'E', 'value': 4}, {'name': 'F', 'value': 5},
    {'name': 'Gb/F#', 'value': 6}, {'name': 'G', 'value': 7}, {'name': 'Ab', 'value': 8},
    {'name': 'A', 'value': 9}, {'name': 'Bb', 'value': 10}, {'name': 'B', 'value': 11},
]

# 笛子定义 (严格区分曲笛/梆笛)
ALL_DIZIS = [
    # 曲笛组 (< Eb)
    {'id': 'C', 'name': 'C', 'value': 0, 'type': 'QU', 'isCommon': True, 'order': 1},
    {'id': 'Db', 'name': 'Db/C#', 'value': 1, 'type': 'QU', 'isCommon': False, 'order': 21},
    {'id': 'D', 'name': 'D', 'value': 2, 'type': 'QU', 'isCommon': True, 'order': 2},
    {'id': 'A_BIG', 'name': '大A', 'value': 9, 'type': 'QU', 'isCommon': True, 'order': 6},
    {'id': 'Bb', 'name': 'Bb', 'value': 10, 'type': 'QU', 'isCommon': True, 'order': 8},
    {'id': 'B', 'name': 'B', 'value': 11, 'type': 'QU', 'isCommon': False, 'order': 20},
    
    # 梆笛组 (>= Eb)
    {'id': 'Eb', 'name': 'Eb', 'value': 3, 'type': 'BANG', 'isCommon': False, 'order': 22},
    {'id': 'E', 'name': 'E', 'value': 4, 'type': 'BANG', 'isCommon': True, 'order': 3},
    {'id': 'F', 'name': 'F', 'value': 5, 'type': 'BANG', 'isCommon': True, 'order': 4},
    {'id': 'Gb', 'name': 'Gb/F#', 'value': 6, 'type': 'BANG', 'isCommon': False, 'order': 23},
    {'id': 'G', 'name': 'G', 'value': 7, 'type': 'BANG', 'isCommon': True, 'order': 5},
    {'id': 'Ab', 'name': 'Ab', 'value': 8, 'type': 'BANG', 'isCommon': False, 'order': 24},
    {'id': 'A_SMALL', 'name': '小A', 'value': 9, 'type': 'BANG', 'isCommon': True, 'order': 7},
]

# --- 3. 核心逻辑函数 ---

def format_key_html(key_name):
    """将 C# 转换为 HTML 格式的 C<sup>♯</sup>"""
    if not key_name: return ""
    
    def format_single(k):
        if k.endswith('#'): return f"{k[:-1]}<sup>♯</sup>"
        if k.endswith('b'): return f"{k[:-1]}<sup>♭</sup>"
        return k

    if '/' in key_name:
        parts = key_name.split('/')
        return f"{format_single(parts[0])}<span style='opacity:0.5;font-size:0.8em'>/</span>{format_single(parts[1])}"
    return format_single(key_name)

def get_recommendations(target_key_val, inventory_ids):
    """核心推荐算法"""
    recs = []
    my_dizis = [d for d in ALL_DIZIS if d['id'] in inventory_ids]
    
    for dizi in my_dizis:
        # 计算音程差: (目标调 - 笛子调 + 12) % 12
        interval = (target_key_val - dizi['value'] + 12) % 12
        
        # 查找对应的筒音指法
        for fingering, offset in TONGYIN_OFFSETS.items():
            if interval == offset:
                recs.append({
                    'dizi': dizi,
                    'tongyin': fingering,
                    'difficulty': DIFF_MAP[fingering],
                    'desc': DESC_MAP[fingering]
                })
    
    # 排序: 难度优先 -> 常用优先 -> 自定义顺序
    def sort_key(item):
        diff_score = {DIFF_RECOMMENDED: 0, DIFF_INTERMEDIATE: 1, DIFF_ADVANCED: 2}
        common_score = 0 if item['dizi']['isCommon'] else 1
        return (diff_score[item['difficulty']], common_score, item['dizi']['order'])
        
    return sorted(recs, key=sort_key)

# --- 4. 样式 CSS ---
st.markdown("""
<style>
    /* App Background */
    .stApp {
        background-color: #f0fdf4;
        background-image: radial-gradient(rgba(22, 101, 52, 0.1) 1px, transparent 1px);
        background-size: 20px 20px;
    }
    
    /* Headers */
    h1, h2, h3 { font-family: 'Serif'; color: #064e3b; }
    
    /* Card Styles */
    .dizi-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #ddd;
        transition: transform 0.2s;
    }
    .dizi-card:hover { transform: scale(1.01); }
    
    .diff-RECOMMENDED { border-left-color: #22c55e; background-color: #f0fdf4; }
    .diff-INTERMEDIATE { border-left-color: #3b82f6; background-color: #eff6ff; }
    .diff-ADVANCED { border-left-color: #ef4444; background-color: #fef2f2; }
    
    .badge {
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: bold;
        color: white;
        float: right;
    }
    .bg-green { background-color: #16a34a; }
    .bg-blue { background-color: #2563eb; }
    .bg-red { background-color: #dc2626; }

    .type-tag {
        display: inline-block;
        font-size: 0.65rem;
        padding: 1px 4px;
        border-radius: 4px;
        border: 1px solid #ccc;
        color: #666;
        margin-left: 4px;
        vertical-align: middle;
    }
</style>
""", unsafe_allow_html=True)

# --- 5. 侧边栏：我的笛包 ---
st.sidebar.header("🎒 我的笛包 (Inventory)")
st.sidebar.markdown("请勾选您拥有的笛子：")

# 初始化 Session State
if 'inventory' not in st.session_state:
    # 默认选中常用笛子
    st.session_state.inventory = [d['id'] for d in ALL_DIZIS if d['isCommon']]

# 库存分类显示
cols_qu = st.sidebar.expander("🎋 曲笛组 (Qu Di)", expanded=True)
cols_bang = st.sidebar.expander("🎍 梆笛组 (Bang Di)", expanded=True)

def checkbox_callback():
    """强制刷新页面以更新推荐列表"""
    pass

with cols_qu:
    for d in [x for x in ALL_DIZIS if x['type'] == 'QU']:
        is_checked = d['id'] in st.session_state.inventory
        if st.checkbox(f"{d['name']} 调", value=is_checked, key=f"chk_{d['id']}", on_change=checkbox_callback):
            if d['id'] not in st.session_state.inventory: st.session_state.inventory.append(d['id'])
        else:
            if d['id'] in st.session_state.inventory: st.session_state.inventory.remove(d['id'])

with cols_bang:
    for d in [x for x in ALL_DIZIS if x['type'] == 'BANG']:
        is_checked = d['id'] in st.session_state.inventory
        if st.checkbox(f"{d['name']} 调", value=is_checked, key=f"chk_{d['id']}", on_change=checkbox_callback):
            if d['id'] not in st.session_state.inventory: st.session_state.inventory.append(d['id'])
        else:
            if d['id'] in st.session_state.inventory: st.session_state.inventory.remove(d['id'])

# --- 6. 主界面 Header ---
col_h1, col_h2 = st.columns([1, 4])
with col_h1:
    st.markdown("<div style='font-size:3rem; text-align:center;'>🎋</div>", unsafe_allow_html=True)
with col_h2:
    st.markdown("# 竹笛变调大师\n<span style='color:#065f46; font-size:0.8em'>Dizi Transposition Master</span>", unsafe_allow_html=True)

# --- 7. AI 听音识调模块 ---
st.markdown("### 🎵 AI 听音识调")
with st.container(border=True):
    audio_input = st.audio_input("点击录音，吹奏完整乐句 (Record)")
    
    if audio_input:
        if not API_KEY:
            st.error("未配置 API Key，无法使用 AI 功能。")
        else:
            with st.spinner("AI 正在分析旋律调性..."):
                try:
                    # 读取音频并转 Base64
                    audio_bytes = audio_input.read()
                    
                    client = genai.Client(api_key=API_KEY)
                    prompt = """
                    You are an expert in Chinese Traditional Music (Dizi).
                    Task: Identify the "System Key" (1 = Do) of the audio.
                    Rules: Monophonic melody. Ignore chords. Find the resting tone (Gong or Yu).
                    Return JSON ONLY: {"root": "C", "explanation": "..."}
                    Standard Roots: C, Db, D, Eb, E, F, Gb, G, Ab, A, Bb, B.
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=[
                            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                            prompt
                        ],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    
                    result = json.loads(response.text)
                    detected_key = result.get('root', 'C')
                    explanation = result.get('explanation', '')
                    
                    # 规范化 Key 名称
                    norm_map = {'C#':'Db/C#', 'Db':'Db/C#', 'D#':'Eb', 'F#':'Gb/F#', 'Gb':'Gb/F#', 'G#':'Ab', 'A#':'Bb'}
                    final_key = norm_map.get(detected_key, detected_key)
                    
                    st.success(f"识别结果: **{final_key} 调**")
                    st.info(f"AI 分析: {explanation}")
                    
                    # 自动设置 Session State 供 Tab 使用
                    st.session_state.detected_key = final_key
                    
                except Exception as e:
                    st.error(f"分析失败: {str(e)}")

# --- 8. 功能标签页 ---
tab1, tab2, tab3 = st.tabs(["智能选笛", "指法反查", "调性推算"])

# === Tab 1: 智能选笛 ===
with tab1:
    st.write("#### 1. 选择乐曲调性 (Song Key)")
    
    # 如果 AI 识别了 Key，自动选中
    default_idx = 0
    if 'detected_key' in st.session_state:
        for i, k in enumerate(MUSIC_KEYS):
            if k['name'] == st.session_state.detected_key:
                default_idx = i
                break
                
    # 使用 Pills 选择器 (Streamlit 1.40+)
    key_names = [k['name'] for k in MUSIC_KEYS]
    selected_key_name = st.pills("Keys", key_names, default=key_names[default_idx], selection_mode="single", label_visibility="collapsed")
    
    if not selected_key_name: selected_key_name = "C"
    target_key_val = next(k['value'] for k in MUSIC_KEYS if k['name'] == selected_key_name)

    st.write("---")
    st.write(f"#### 推荐方案 (基于 {len(st.session_state.inventory)} 根库存竹笛)")
    
    recs = get_recommendations(target_key_val, st.session_state.inventory)
    
    if not recs:
        st.warning("您的笛包中没有合适的笛子，请在左侧侧边栏添加更多笛子。")
    else:
        for rec in recs:
            dizi = rec['dizi']
            diff = rec['difficulty']
            badge_color = "bg-green" if diff == DIFF_RECOMMENDED else "bg-blue" if diff == DIFF_INTERMEDIATE else "bg-red"
            badge_text = "推荐" if diff == DIFF_RECOMMENDED else "进阶" if diff == DIFF_INTERMEDIATE else "困难"
            type_text = "曲笛" if dizi['type'] == 'QU' else "梆笛"
            
            html = f"""
            <div class="dizi-card diff-{diff}">
                <span class="badge {badge_color}">{badge_text}</span>
                <div style="font-size: 0.75rem; color: #666; text-transform: uppercase; font-weight: bold;">
                    Use Dizi <span class="type-tag">{type_text}</span>
                </div>
                <div style="font-size: 1.5rem; font-weight: bold; color: #064e3b; margin: 4px 0;">
                    {format_key_html(dizi['name'])} <span style="font-size:1rem; font-weight:normal; color:black;">调笛</span>
                </div>
                <div style="border-top: 1px solid #eee; margin-top: 12px; padding-top: 12px; display:flex; justify-content:space-between;">
                    <div>
                        <div style="font-size: 0.75rem; color: #888; font-weight:bold;">Fingering</div>
                        <div style="font-size: 1.1rem; font-weight: 500;">筒音作 {rec['tongyin']}</div>
                    </div>
                    <div style="font-size: 0.8rem; color: #888; font-style: italic; align-self: center;">
                        {rec['desc']}
                    </div>
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

# === Tab 2: 指法反查 ===
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        s_song_key = st.selectbox("乐曲是什么调?", key_names, index=0)
    with c2:
        # 笛子列表包括 '任意' 选项
        my_dizi_objs = sorted([d for d in ALL_DIZIS if d['id'] in st.session_state.inventory], key=lambda x: x['order'])
        dizi_opts = ["🔍 不限 (Recommend)"] + [f"{d['name']} 调笛" for d in my_dizi_objs]
        s_dizi_label = st.selectbox("你手里是什么笛子?", dizi_opts)

    st.info("计算结果：")
    
    t_val = next(k['value'] for k in MUSIC_KEYS if k['name'] == s_song_key)
    
    if "🔍" in s_dizi_label:
        # 类似 Tab 1 的列表
        recs2 = get_recommendations(t_val, st.session_state.inventory)
        if not recs2: st.write("无匹配。")
        for r in recs2:
            st.caption(f"{r['dizi']['name']} 调笛 -> 筒音作 {r['tongyin']} ({r['difficulty']})")
    else:
        # 单个计算
        d_name = s_dizi_label.split(" ")[0]
        d_obj = next(d for d in ALL_DIZIS if d['name'] == d_name) # 注意：这里假设 Name 唯一，如果有大A小A同名需处理
        # 为简便，这里通过名字反查可能不严谨，但在 multiselect 语境下尚可。更严谨应用 ID。
        # 修正：在 Option 里带上 ID 或唯一标识会更好。这里做简单逻辑：
        
        # 计算
        interval = (t_val - d_obj['value'] + 12) % 12
        found = False
        for k, v in TONGYIN_OFFSETS.items():
            if v == interval:
                found = True
                st.markdown(f"""
                <div style="text-align:center; padding: 20px; background:#f0fdf4; border-radius:10px; border:1px solid #bbf7d0;">
                    <h2 style="margin:0; color:#166534;">筒音作 {k}</h2>
                    <p style="color:#666; margin-top:5px;">{DESC_MAP[k]}</p>
                </div>
                """, unsafe_allow_html=True)
        
        if not found:
            st.error("该笛子无法通过常用指法吹奏此调。")

# === Tab 3: 调性推算 ===
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        # 所有笛子 (排序)
        all_sorted = sorted(ALL_DIZIS, key=lambda x: x['order'])
        d_opts = [f"{d['name']} ({'曲' if d['type']=='QU' else '梆'})" for d in all_sorted]
        sel_d_idx = st.selectbox("笛子调性", d_opts)
    with c2:
        sel_fingering = st.selectbox("指法 (筒音作...)", list(TONGYIN_OFFSETS.keys()))

    # 提取选中的 Dizi Value
    sel_d_name = sel_d_idx.split(" ")[0]
    d_val = next(d['value'] for d in ALL_DIZIS if d['name'] == sel_d_name) # 简化匹配
    
    # 计算
    offset = TONGYIN_OFFSETS[sel_fingering]
    res_val = (d_val + offset) % 12
    res_key = next(k['name'] for k in MUSIC_KEYS if k['value'] == res_val)
    
    st.markdown(f"""
    <div style="text-align:center; margin-top:20px;">
        <div style="font-size:0.9rem; color:#666;">实际发出的音高是</div>
        <div style="font-size:3rem; font-weight:bold; color:#064e3b;">{format_key_html(res_key)} 调</div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.write("---")
st.caption("© 2025 竹笛变调大师 (Python Streamlit Edition)")
