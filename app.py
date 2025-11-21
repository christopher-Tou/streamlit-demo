import streamlit as st

# --- 1. 数据结构与乐理常量 (从 types.ts 和 musicLogic.ts 移植) ---

# 难度枚举
DIFF_RECOMMENDED = "RECOMMENDED" # Green
DIFF_INTERMEDIATE = "INTERMEDIATE" # Blue
DIFF_ADVANCED = "ADVANCED" # Red

# 指法枚举与偏移量 (从 Dizi Key 到 Target Key 的半音差)
# Target = (Dizi + Offset) % 12
TONGYIN_OFFSETS = {
    '5': 0,   # 筒音作5 (Sol) -> 调性相同
    '2': 5,   # 筒音作2 (Re)  -> +5 Semitones (e.g. C -> F)
    '3': 3,   # 筒音作3 (Mi)  -> +3 Semitones (e.g. C -> Eb)
    '6': 10,  # 筒音作6 (La)  -> +10 Semitones (e.g. C -> Bb)
    '1': 7,   # 筒音作1 (Do)  -> +7 Semitones (e.g. C -> G)
    '7': 8    # 筒音作7 (Ti)  -> +8 Semitones (e.g. C -> Ab)
}

# 难度映射
DIFF_MAP = {
    '5': DIFF_RECOMMENDED, '2': DIFF_RECOMMENDED,
    '3': DIFF_INTERMEDIATE, '6': DIFF_INTERMEDIATE,
    '1': DIFF_ADVANCED, '7': DIFF_ADVANCED
}

# 描述映射
DESC_MAP = {
    '5': '最常用指法 (Most Common)',
    '2': '常用指法 (Common)',
    '3': '指法较顺 (Smooth)',
    '6': '需按半孔 (Half-hole)',
    '1': '气息控制难 (Hard Control)',
    '7': '极少使用 (Very Rare)'
}

# 12个调性定义
MUSIC_KEYS = [
    {'name': 'C', 'value': 0},
    {'name': 'Db/C#', 'value': 1},
    {'name': 'D', 'value': 2},
    {'name': 'Eb', 'value': 3},
    {'name': 'E', 'value': 4},
    {'name': 'F', 'value': 5},
    {'name': 'Gb/F#', 'value': 6},
    {'name': 'G', 'value': 7},
    {'name': 'Ab', 'value': 8},
    {'name': 'A', 'value': 9},
    {'name': 'Bb', 'value': 10},
    {'name': 'B', 'value': 11},
]

# 所有笛子定义 (ALL_DIZIS)
# 包含 曲笛(Qu) 和 梆笛(Bang) 的分类逻辑
ALL_DIZIS = [
    # --- 曲笛 Group (< Eb) ---
    {'id': 'A_BIG', 'name': '大A', 'value': 9, 'type': 'QU', 'isCommon': True, 'order': 6},
    {'id': 'Bb', 'name': 'Bb', 'value': 10, 'type': 'QU', 'isCommon': True, 'order': 8},
    {'id': 'B', 'name': 'B', 'value': 11, 'type': 'QU', 'isCommon': False, 'order': 20},
    {'id': 'C', 'name': 'C', 'value': 0, 'type': 'QU', 'isCommon': True, 'order': 1},
    {'id': 'Db', 'name': 'Db/C#', 'value': 1, 'type': 'QU', 'isCommon': False, 'order': 21},
    {'id': 'D', 'name': 'D', 'value': 2, 'type': 'QU', 'isCommon': True, 'order': 2},

    # --- 梆笛 Group (>= Eb) ---
    {'id': 'Eb', 'name': 'Eb', 'value': 3, 'type': 'BANG', 'isCommon': False, 'order': 22},
    {'id': 'E', 'name': 'E', 'value': 4, 'type': 'BANG', 'isCommon': True, 'order': 3},
    {'id': 'F', 'name': 'F', 'value': 5, 'type': 'BANG', 'isCommon': True, 'order': 4},
    {'id': 'Gb', 'name': 'Gb/F#', 'value': 6, 'type': 'BANG', 'isCommon': False, 'order': 23},
    {'id': 'G', 'name': 'G', 'value': 7, 'type': 'BANG', 'isCommon': True, 'order': 5},
    {'id': 'Ab', 'name': 'Ab', 'value': 8, 'type': 'BANG', 'isCommon': False, 'order': 24},
    {'id': 'A_SMALL', 'name': '小A', 'value': 9, 'type': 'BANG', 'isCommon': True, 'order': 7},
]

# --- 2. 辅助函数 ---

def format_key_html(key_name):
    """将 C# 显示为漂亮的 HTML C<sup>♯</sup>"""
    if not key_name: return ""
    
    def format_single(k):
        if k.endswith('#'): return f"{k[:-1]}<sup>♯</sup>"
        if k.endswith('b'): return f"{k[:-1]}<sup>♭</sup>"
        return k

    if '/' in key_name:
        parts = key_name.split('/')
        # 渲染类似 Db/C#
        return f"{format_single(parts[0])}<span style='opacity:0.5; font-size:0.8em; margin:0 2px;'>/</span>{format_single(parts[1])}"
    return format_single(key_name)

def get_recommendations(target_key_val, inventory_ids):
    """核心算法：根据目标调和库存，计算推荐指法"""
    recs = []
    # 1. 筛选用户有的笛子
    my_dizis = [d for d in ALL_DIZIS if d['id'] in inventory_ids]
    
    for dizi in my_dizis:
        # 2. 计算音程差: (Target - Dizi + 12) % 12
        interval = (target_key_val - dizi['value'] + 12) % 12
        
        # 3. 匹配指法
        for fingering, offset in TONGYIN_OFFSETS.items():
            if interval == offset:
                recs.append({
                    'dizi': dizi,
                    'tongyin': fingering,
                    'difficulty': DIFF_MAP[fingering],
                    'desc': DESC_MAP[fingering]
                })
    
    # 4. 排序逻辑 (React 版复刻)
    # 优先级: 难度 (绿>蓝>红) -> 常用笛子 -> 自定义排序
    def sort_key(item):
        diff_score = {DIFF_RECOMMENDED: 0, DIFF_INTERMEDIATE: 1, DIFF_ADVANCED: 2}
        common_score = 0 if item['dizi']['isCommon'] else 1
        return (diff_score[item['difficulty']], common_score, item['dizi']['order'])
        
    return sorted(recs, key=sort_key)

# --- 3. Streamlit 页面配置与样式 ---

st.set_page_config(
    page_title="竹笛变调大师",
    page_icon="🎋",
    layout="centered",
    initial_sidebar_state="collapsed" # 默认收起笛包
)

# 注入 CSS (复刻 index.html 和 App.tsx 的样式)
st.markdown("""
<style>
    /* 全局背景 - 竹林绿纹理 */
    .stApp {
        background-color: #f0fdf4;
        background-image: radial-gradient(rgba(22, 101, 52, 0.1) 1px, transparent 1px);
        background-size: 20px 20px;
    }
    
    /* 字体 */
    h1, h2, h3 { font-family: "Noto Serif SC", serif; color: #064e3b; }
    
    /* 隐藏 Streamlit 默认菜单 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 卡片样式 */
    .dizi-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #ddd;
        transition: transform 0.2s;
        position: relative;
        overflow: hidden;
    }
    .dizi-card:hover { transform: scale(1.01); }
    
    /* 难度颜色 */
    .diff-RECOMMENDED { border-left-color: #22c55e; background-color: #f0fdf4; }
    .diff-INTERMEDIATE { border-left-color: #3b82f6; background-color: #eff6ff; }
    .diff-ADVANCED { border-left-color: #ef4444; background-color: #fef2f2; }
    
    /* 徽章 */
    .badge {
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: bold;
        color: white;
        float: right;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .bg-green { background-color: #16a34a; }
    .bg-blue { background-color: #2563eb; }
    .bg-red { background-color: #dc2626; }

    /* 类型标签 (曲/梆) */
    .type-tag {
        display: inline-block;
        font-size: 0.65rem;
        padding: 1px 6px;
        border-radius: 4px;
        background-color: #f3f4f6;
        border: 1px solid #e5e7eb;
        color: #666;
        margin-left: 6px;
        vertical-align: middle;
        text-transform: uppercase;
    }
    
    /* Key 显示优化 */
    .key-display { font-family: "Noto Serif SC", serif; }
    sup { font-size: 0.6em; }
</style>
""", unsafe_allow_html=True)

# --- 4. 状态管理 (Inventory) ---

if 'inventory' not in st.session_state:
    # 默认勾选常用笛子
    st.session_state.inventory = [d['id'] for d in ALL_DIZIS if d['isCommon']]

def toggle_inventory(dizi_id):
    if dizi_id in st.session_state.inventory:
        st.session_state.inventory.remove(dizi_id)
    else:
        st.session_state.inventory.append(dizi_id)

# --- 5. 侧边栏：我的笛包 ---

st.sidebar.header("🎒 我的笛包 (Inventory)")
st.sidebar.info("请勾选您拥有的笛子，系统将根据库存为您推荐。")

# 渲染曲笛组
with st.sidebar.expander("🎋 曲笛组 (Qu Di)", expanded=True):
    for d in [x for x in ALL_DIZIS if x['type'] == 'QU']:
        st.checkbox(
            f"{d['name']} 调", 
            value=(d['id'] in st.session_state.inventory),
            key=f"inv_{d['id']}",
            on_change=toggle_inventory, args=(d['id'],)
        )

# 渲染梆笛组
with st.sidebar.expander("🎍 梆笛组 (Bang Di)", expanded=True):
    for d in [x for x in ALL_DIZIS if x['type'] == 'BANG']:
        st.checkbox(
            f"{d['name']} 调", 
            value=(d['id'] in st.session_state.inventory),
            key=f"inv_{d['id']}",
            on_change=toggle_inventory, args=(d['id'],)
        )

# --- 6. 主界面 Header ---

col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.markdown("<div style='font-size:3rem; text-align:center; line-height:1.2;'>🎋</div>", unsafe_allow_html=True)
with col_title:
    st.markdown("""
    <h1 style='margin-bottom:0; padding-bottom:0;'>竹笛变调大师</h1>
    <p style='color:#065f46; font-size:0.8rem; text-transform:uppercase; letter-spacing:1px; margin-top:0;'>
        Dizi Transposition Master
    </p>
    """, unsafe_allow_html=True)

if len(st.session_state.inventory) == 0:
    st.warning("⚠️ 您的笛包为空，请点击左上角 **>** 展开侧边栏添加笛子。")

# --- 7. 功能标签页 ---

tab1, tab2, tab3 = st.tabs(["智能选笛", "指法反查", "调性推算"])

# === Tab 1: 智能选笛 (Smart Recommend) ===
with tab1:
    st.markdown("### 1. 选择乐曲调性 (Song Key)")
    
    # Key 选择器
    cols = st.columns(6)
    # 简单的 Key 状态
    if 'selected_key_idx' not in st.session_state:
        st.session_state.selected_key_idx = 0 # C Major

    # 使用 Streamlit 的 Selectbox 或者 按钮组
    # 这里为了美观，使用 Selectbox
    key_options = [k['name'] for k in MUSIC_KEYS]
    selected_key_name = st.selectbox(
        "请选择谱子上的调号：", 
        key_options, 
        index=st.session_state.selected_key_idx
    )
    
    # 更新 Index
    target_key_val = next(k['value'] for k in MUSIC_KEYS if k['name'] == selected_key_name)
    st.session_state.selected_key_idx = target_key_val # Sync

    st.markdown("---")
    st.markdown(f"### 推荐方案 <span style='font-size:0.8em; color:#666; font-weight:normal'>(基于 {len(st.session_state.inventory)} 根库存笛子)</span>", unsafe_allow_html=True)
    
    recommendations = get_recommendations(target_key_val, st.session_state.inventory)
    
    if not recommendations:
        st.info("没有匹配的笛子。请尝试在侧边栏添加更多调的笛子，或检查是否选择了极少见的转调。")
    
    for rec in recommendations:
        dizi = rec['dizi']
        diff = rec['difficulty']
        
        # 样式变量
        badge_color = "bg-green" if diff == DIFF_RECOMMENDED else "bg-blue" if diff == DIFF_INTERMEDIATE else "bg-red"
        badge_text = "推荐" if diff == DIFF_RECOMMENDED else "进阶" if diff == DIFF_INTERMEDIATE else "困难"
        type_text = "曲笛" if dizi['type'] == 'QU' else "梆笛"
        
        # 构建 HTML 卡片
        card_html = f"""
        <div class="dizi-card diff-{diff}">
            <span class="badge {badge_color}">{badge_text}</span>
            <div style="font-size: 0.75rem; color: #666; text-transform: uppercase; font-weight: bold; display:flex; align-items:center;">
                Use Dizi <span class="type-tag">{type_text}</span>
            </div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #064e3b; margin: 4px 0;" class="key-display">
                {format_key_html(dizi['name'])} <span style="font-size:1.2rem; font-weight:normal; color:black; opacity:0.6">调笛</span>
            </div>
            <div style="border-top: 1px solid rgba(0,0,0,0.05); margin-top: 12px; padding-top: 12px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size: 0.75rem; color: #9ca3af; font-weight:bold; text-transform:uppercase;">Fingering</div>
                    <div style="font-size: 1.2rem; font-weight: 500; color:#1f2937;">筒音作 {rec['tongyin']}</div>
                </div>
                <div style="font-size: 0.85rem; color: #6b7280; font-style: italic;">
                    {rec['desc']}
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

# === Tab 2: 指法反查 (Reverse Lookup) ===
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        s_song_key = st.selectbox("1. 乐曲是什么调?", key_options, index=0, key="tab2_key")
    with c2:
        # 笛子下拉框：包含 "不限" 和 库存中的笛子
        my_sorted_dizis = sorted([d for d in ALL_DIZIS if d['id'] in st.session_state.inventory], key=lambda x: x['order'])
        
        # 选项 Label 映射
        dizi_opts_labels = ["🔍 帮我推荐 (Recommend)"] + [f"{d['name']} 调笛" for d in my_sorted_dizis]
        s_dizi_label = st.selectbox("2. 你手里是什么笛子?", dizi_opts_labels)

    target_val = next(k['value'] for k in MUSIC_KEYS if k['name'] == s_song_key)
    
    st.info("计算结果：")

    if "🔍" in s_dizi_label:
        # 逻辑同 Tab 1
        recs2 = get_recommendations(target_val, st.session_state.inventory)
        if not recs2:
            st.write("无可用推荐。")
        else:
            for r in recs2:
                st.caption(f"✅ 用 **{r['dizi']['name']}调笛** -> 筒音作 **{r['tongyin']}** ({r['difficulty']})")
    else:
        # 单个计算
        d_name = s_dizi_label.split(" ")[0]
        # 注意：通过 Name 反查 ID 可能有歧义（大A/小A），这里严谨起见，在实际项目中应通过 index 映射
        # 简单处理：优先匹配库存里的
        d_obj = next((d for d in my_sorted_dizis if d['name'] == d_name), None)
        
        if d_obj:
            interval = (target_val - d_obj['value'] + 12) % 12
            
            found_fingering = None
            for f, off in TONGYIN_OFFSETS.items():
                if off == interval:
                    found_fingering = f
                    break
            
            if found_fingering:
                st.markdown(f"""
                <div style="text-align:center; padding: 30px; background:white; border-radius:16px; border:1px solid #d1fae5; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1);">
                    <div style="color:#666; font-size:0.9rem; margin-bottom:10px;">应使用的指法是</div>
                    <h2 style="margin:0; color:#064e3b; font-size:2.5rem;">筒音作 {found_fingering}</h2>
                    <p style="color:#10b981; font-weight:bold; margin-top:10px;">{DESC_MAP[found_fingering]}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("该笛子无法通过常用指法吹奏此调（属于极难偏门转调）。")

# === Tab 3: 调性推算 (Key Calculation) ===
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        # 显示所有笛子（区分大A小A）
        all_opts = [f"{d['name']} ({'曲' if d['type']=='QU' else '梆'})" for d in sorted(ALL_DIZIS, key=lambda x: x['order'])]
        sel_d_idx = st.selectbox("1. 笛子调性", all_opts)
    with c2:
        sel_fingering = st.selectbox("2. 指法 (筒音作...)", list(TONGYIN_OFFSETS.keys()))

    # 解析选择
    sel_d_name = sel_d_idx.split(" ")[0]
    # 查找 value
    d_val = next(d['value'] for d in ALL_DIZIS if d['name'] == sel_d_name)
    
    # 计算
    offset = TONGYIN_OFFSETS[sel_fingering]
    res_val = (d_val + offset) % 12
    res_key = next(k['name'] for k in MUSIC_KEYS if k['value'] == res_val)
    
    st.markdown(f"""
    <div style="text-align:center; margin-top:20px; padding:20px; background:linear-gradient(to bottom right, #ecfdf5, #fff); border-radius:16px; border:1px solid #a7f3d0;">
        <div style="font-size:0.9rem; color:#666;">实际发出的音高是</div>
        <div style="font-size:3.5rem; font-weight:bold; color:#064e3b; margin:10px 0;">
            {format_key_html(res_key)} <span style="font-size:1.5rem; color:#059669;">调</span>
        </div>
        <div style="font-size:0.8rem; color:#9ca3af;">
            (笛子: {sel_d_name} + 指法: {sel_fingering})
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("© 2025 竹笛变调大师 (Python Streamlit Edition)")
