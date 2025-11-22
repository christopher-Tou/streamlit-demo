import streamlit as st

# --- 1. Data Structures & Constants (Ported from types.ts) ---

# Difficulty Enums
DIFF_RECOMMENDED = "RECOMMENDED"  # Green
DIFF_INTERMEDIATE = "INTERMEDIATE"  # Blue
DIFF_ADVANCED = "ADVANCED"  # Red

# Fingering Offsets: (Target Key - Dizi Key + 12) % 12
TONGYIN_OFFSETS = {
    '5': 0,   # Sol
    '2': 5,   # Re
    '3': 3,   # Mi
    '6': 10,  # La
    '1': 7,   # Do
    '7': 8    # Ti
}

# Difficulty Mapping
DIFF_MAP = {
    '5': DIFF_RECOMMENDED, '2': DIFF_RECOMMENDED,
    '3': DIFF_INTERMEDIATE, '6': DIFF_INTERMEDIATE,
    '1': DIFF_ADVANCED, '7': DIFF_ADVANCED
}

# Description Mapping
DESC_MAP = {
    '5': '最常用指法 (Most Common)',
    '2': '常用指法 (Common)',
    '3': '指法较顺 (Smooth)',
    '6': '需按半孔 (Half-hole)',
    '1': '气息控制难 (Hard Control)',
    '7': '极少使用 (Very Rare)'
}

# Musical Keys (0-11)
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

# Dizi Definitions (Qu vs Bang)
ALL_DIZIS = [
    # --- Qu Di Group (< Eb) ---
    {'id': 'A_BIG', 'name': '大A', 'value': 9, 'type': 'QU', 'isCommon': True, 'order': 6},
    {'id': 'Bb', 'name': 'Bb', 'value': 10, 'type': 'QU', 'isCommon': True, 'order': 8},
    {'id': 'B', 'name': 'B', 'value': 11, 'type': 'QU', 'isCommon': False, 'order': 20},
    {'id': 'C', 'name': 'C', 'value': 0, 'type': 'QU', 'isCommon': True, 'order': 1},
    {'id': 'Db', 'name': 'Db/C#', 'value': 1, 'type': 'QU', 'isCommon': False, 'order': 21},
    {'id': 'D', 'name': 'D', 'value': 2, 'type': 'QU', 'isCommon': True, 'order': 2},

    # --- Bang Di Group (>= Eb) ---
    {'id': 'Eb', 'name': 'Eb', 'value': 3, 'type': 'BANG', 'isCommon': False, 'order': 22},
    {'id': 'E', 'name': 'E', 'value': 4, 'type': 'BANG', 'isCommon': True, 'order': 3},
    {'id': 'F', 'name': 'F', 'value': 5, 'type': 'BANG', 'isCommon': True, 'order': 4},
    {'id': 'Gb', 'name': 'Gb/F#', 'value': 6, 'type': 'BANG', 'isCommon': False, 'order': 23},
    {'id': 'G', 'name': 'G', 'value': 7, 'type': 'BANG', 'isCommon': True, 'order': 5},
    {'id': 'Ab', 'name': 'Ab', 'value': 8, 'type': 'BANG', 'isCommon': False, 'order': 24},
    {'id': 'A_SMALL', 'name': '小A', 'value': 9, 'type': 'BANG', 'isCommon': True, 'order': 7},
]

# --- 2. Logic Helpers ---

def format_key_html(key_name):
    """Format C# to HTML superscripts"""
    if not key_name: return ""
    def fmt(k):
        if k.endswith('#'): return f"{k[:-1]}<sup>♯</sup>"
        if k.endswith('b'): return f"{k[:-1]}<sup>♭</sup>"
        return k
    if '/' in key_name:
        p = key_name.split('/')
        return f"{fmt(p[0])}<span style='opacity:0.5;font-size:0.8em'>/</span>{fmt(p[1])}"
    return fmt(key_name)

def get_recommendations(target_key_val, inventory_ids):
    """Smart Recommend Logic"""
    recs = []
    my_dizis = [d for d in ALL_DIZIS if d['id'] in inventory_ids]
    
    for dizi in my_dizis:
        interval = (target_key_val - dizi['value'] + 12) % 12
        for fingering, offset in TONGYIN_OFFSETS.items():
            if interval == offset:
                recs.append({
                    'dizi': dizi,
                    'tongyin': fingering,
                    'difficulty': DIFF_MAP[fingering],
                    'desc': DESC_MAP[fingering]
                })
    
    # Sort: Difficulty -> Common -> Order
    def sort_key(item):
        diff_score = {DIFF_RECOMMENDED: 0, DIFF_INTERMEDIATE: 1, DIFF_ADVANCED: 2}
        common_score = 0 if item['dizi']['isCommon'] else 1
        return (diff_score[item['difficulty']], common_score, item['dizi']['order'])
        
    return sorted(recs, key=sort_key)

def get_fingering_chart(fingering, inventory_ids):
    """Tab 2 Logic: Fingering -> List of resulting keys"""
    offset = TONGYIN_OFFSETS[fingering]
    results = []
    for dizi in ALL_DIZIS:
        # Result Key = (Dizi + Offset) % 12
        res_val = (dizi['value'] + offset) % 12
        res_key = next(k['name'] for k in MUSIC_KEYS if k['value'] == res_val)
        results.append({
            'dizi': dizi,
            'resultKey': res_key,
            'isOwned': dizi['id'] in inventory_ids
        })
    
    common = sorted([r for r in results if r['dizi']['isCommon']], key=lambda x: x['dizi']['order'])
    rare = sorted([r for r in results if not r['dizi']['isCommon']], key=lambda x: x['dizi']['order'])
    return common, rare

# --- 3. Streamlit UI Setup ---

st.set_page_config(
    page_title="竹笛变调大师",
    page_icon="🎋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Inject CSS
st.markdown("""
<style>
    .stApp {
        background-color: #f0fdf4;
        background-image: radial-gradient(rgba(22, 101, 52, 0.1) 1px, transparent 1px);
        background-size: 20px 20px;
    }
    h1, h2, h3 { font-family: "Noto Serif SC", serif; color: #064e3b; }
    
    /* Cards */
    .dizi-card {
        background: white; border-radius: 12px; padding: 16px; margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #ddd;
    }
    .diff-RECOMMENDED { border-left-color: #22c55e; background-color: #f0fdf4; }
    .diff-INTERMEDIATE { border-left-color: #3b82f6; background-color: #eff6ff; }
    .diff-ADVANCED { border-left-color: #ef4444; background-color: #fef2f2; }
    
    .badge { padding: 2px 8px; border-radius: 99px; font-size: 0.75rem; color: white; float: right; font-weight: bold;}
    .bg-green { background-color: #16a34a; }
    .bg-blue { background-color: #2563eb; }
    .bg-red { background-color: #dc2626; }
    
    .type-tag { font-size: 0.65rem; padding: 1px 4px; border-radius: 4px; background:#f3f4f6; color:#666; margin-left:4px; }
</style>
""", unsafe_allow_html=True)

# --- 4. State Management (Inventory) ---

if 'inventory' not in st.session_state:
    st.session_state.inventory = [d['id'] for d in ALL_DIZIS if d['isCommon']]

def toggle_inv(did):
    if did in st.session_state.inventory:
        st.session_state.inventory.remove(did)
    else:
        st.session_state.inventory.append(did)

# Sidebar
st.sidebar.header("🎒 我的笛包 (Inventory)")
with st.sidebar.expander("🎋 曲笛组 (Qu Di)", expanded=True):
    for d in [x for x in ALL_DIZIS if x['type'] == 'QU']:
        st.checkbox(f"{d['name']} 调", value=d['id'] in st.session_state.inventory, key=f"inv_{d['id']}", on_change=toggle_inv, args=(d['id'],))
with st.sidebar.expander("🎍 梆笛组 (Bang Di)", expanded=True):
    for d in [x for x in ALL_DIZIS if x['type'] == 'BANG']:
        st.checkbox(f"{d['name']} 调", value=d['id'] in st.session_state.inventory, key=f"inv_{d['id']}", on_change=toggle_inv, args=(d['id'],))

# Header
c1, c2 = st.columns([1, 5])
c1.markdown("<div style='font-size:3rem;text-align:center;'>🎋</div>", unsafe_allow_html=True)
c2.markdown("# 竹笛变调大师\n<span style='color:#065f46;font-size:0.8em'>Dizi Transposition Master</span>", unsafe_allow_html=True)

if not st.session_state.inventory:
    st.warning("⚠️ 笛包为空，请在左侧边栏添加笛子。")

# --- 5. Main Tabs ---

tab1, tab2, tab3, tab4 = st.tabs(["智能选笛", "指法反查", "单笛图鉴", "万能推算"])

# === TAB 1: Smart Recommend ===
with tab1:
    st.caption("选择乐曲调性 (Song Key)")
    key_opts = [k['name'] for k in MUSIC_KEYS]
    sel_key = st.selectbox("Key", key_opts, label_visibility="collapsed")
    target_val = next(k['value'] for k in MUSIC_KEYS if k['name'] == sel_key)
    
    st.markdown(f"### 推荐方案 ({len(st.session_state.inventory)} Dizis)")
    recs = get_recommendations(target_val, st.session_state.inventory)
    
    if not recs:
        st.info("无匹配笛子。")
    
    for r in recs:
        d, diff = r['dizi'], r['difficulty']
        b_col = "bg-green" if diff == DIFF_RECOMMENDED else "bg-blue" if diff == DIFF_INTERMEDIATE else "bg-red"
        b_txt = "推荐" if diff == DIFF_RECOMMENDED else "进阶" if diff == DIFF_INTERMEDIATE else "困难"
        
        st.markdown(f"""
        <div class="dizi-card diff-{diff}">
            <span class="badge {b_col}">{b_txt}</span>
            <div style="font-size:0.75rem;color:#666;font-weight:bold;">USE DIZI <span class="type-tag">{'曲' if d['type']=='QU' else '梆'}</span></div>
            <div style="font-size:1.8rem;font-weight:bold;color:#064e3b;">{format_key_html(d['name'])} <span style="font-size:1rem;color:black;font-weight:normal">调笛</span></div>
            <div style="border-top:1px solid #eee;margin-top:10px;padding-top:10px;display:flex;justify-content:space-between;">
                <div><span style="font-size:0.75rem;color:#999;">FINGERING</span><br><b>筒音作 {r['tongyin']}</b></div>
                <div style="font-size:0.8rem;color:#666;font-style:italic;align-self:center;">{r['desc']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# === TAB 2: Fingering Lookup (Inverted Logic) ===
with tab2:
    st.caption("采用什么指法? (Fingering)")
    fing_opts = ['5', '2', '3', '6', '1', '7']
    sel_fing = st.selectbox("Fingering", fing_opts, format_func=lambda x: f"筒音作 {x}")
    
    common, rare = get_fingering_chart(sel_fing, st.session_state.inventory)
    
    st.markdown("### 🌟 常用笛子 (Common)")
    for item in common:
        bg = "border-emerald-500 bg-white" if item['isOwned'] else "border-gray-300 bg-gray-100 opacity-80"
        st.markdown(f"""
        <div style="border-left:4px solid; padding:12px; margin-bottom:8px; border-radius:8px; display:flex; justify-content:space-between; align-items:center;" class="{bg}">
            <div>
                <span style="font-weight:bold; font-size:1.2rem; color:#064e3b;">{format_key_html(item['dizi']['name'])} 调笛</span>
                <span style="color:#666; font-size:0.9rem;"> + 筒音{sel_fing} = </span>
                <span style="font-weight:bold; font-size:1.2rem;">{format_key_html(item['resultKey'])} 调</span>
            </div>
            {'' if item['isOwned'] else '<span style="font-size:0.7rem; background:#ddd; padding:2px 4px; rounded;">未拥有</span>'}
        </div>
        """, unsafe_allow_html=True)
        
    with st.expander("查看其他笛子 (Rare)"):
        cols = st.columns(2)
        for i, item in enumerate(rare):
            with cols[i%2]:
                st.caption(f"{item['dizi']['name']}调笛 = **{item['resultKey']}调**")

# === TAB 3: Dizi Map ===
with tab3:
    inv_dizis = sorted([d for d in ALL_DIZIS if d['id'] in st.session_state.inventory], key=lambda x: x['order'])
    d_opts = [f"{d['name']} 调" for d in inv_dizis]
    
    if not d_opts:
        st.error("笛包为空。")
    else:
        sel_d_name = st.selectbox("选择笛子", d_opts).split(" ")[0]
        d_obj = next(d for d in inv_dizis if d['name'] == sel_d_name) # Simple match
        
        st.write(f"#### {sel_d_name} 调笛全指法图")
        c1, c2 = st.columns(2)
        # Order: 5, 2, 3, 6, 1, 7
        ordered_f = ['5','2','3','6','1','7']
        for i, f in enumerate(ordered_f):
            off = TONGYIN_OFFSETS[f]
            k_val = (d_obj['value'] + off) % 12
            k_name = next(k['name'] for k in MUSIC_KEYS if k['value'] == k_val)
            
            diff = DIFF_MAP[f]
            col_css = "bg-green-50 border-green-200" if diff==DIFF_RECOMMENDED else "bg-blue-50 border-blue-200" if diff==DIFF_INTERMEDIATE else "bg-red-50 border-red-200"
            
            with (c1 if i%2==0 else c2):
                st.markdown(f"""
                <div style="padding:10px; border:1px solid; border-radius:8px; margin-bottom:10px;" class="{col_css}">
                    <div style="font-size:0.8rem; color:#666;">筒音作 {f}</div>
                    <div style="font-size:1.5rem; font-weight:bold;">{format_key_html(k_name)} <span style="font-size:0.8rem">调</span></div>
                </div>
                """, unsafe_allow_html=True)

# === TAB 4: Universal Calculator ===
with tab4:
    calc_mode = st.radio("模式", ["求音高 (Find Key)", "求指法 (Find Fingering)", "求笛子 (Find Dizi)"], horizontal=True)
    
    c_dizi_opts = [d['name'] for d in sorted(ALL_DIZIS, key=lambda x: x['order'])]
    c_fing_opts = list(TONGYIN_OFFSETS.keys())
    c_key_opts = [k['name'] for k in MUSIC_KEYS]
    
    res_html = ""
    
    if "Find Key" in calc_mode:
        c1, c2 = st.columns(2)
        d_in = c1.selectbox("笛子", c_dizi_opts)
        f_in = c2.selectbox("指法", c_fing_opts, format_func=lambda x:f"筒音{x}")
        
        d_val = next(d['value'] for d in ALL_DIZIS if d['name'] == d_in)
        k_val = (d_val + TONGYIN_OFFSETS[f_in]) % 12
        k_res = next(k['name'] for k in MUSIC_KEYS if k['value'] == k_val)
        res_html = f"实际音高: <b>{format_key_html(k_res)} 调</b>"
        
    elif "Find Fingering" in calc_mode:
        c1, c2 = st.columns(2)
        d_in = c1.selectbox("笛子", c_dizi_opts)
        k_in = c2.selectbox("目标调", c_key_opts)
        
        d_val = next(d['value'] for d in ALL_DIZIS if d['name'] == d_in)
        k_val = next(k['value'] for k in MUSIC_KEYS if k['name'] == k_in)
        
        req_off = (k_val - d_val + 12) % 12
        f_res = next((f for f, o in TONGYIN_OFFSETS.items() if o == req_off), None)
        
        if f_res:
            res_html = f"应采用: <b>筒音作 {f_res}</b>"
        else:
            res_html = "<span style='color:red'>无常用指法 (Non-standard)</span>"
            
    else: # Find Dizi
        c1, c2 = st.columns(2)
        k_in = c1.selectbox("目标调", c_key_opts)
        f_in = c2.selectbox("指法", c_fing_opts, format_func=lambda x:f"筒音{x}")
        
        k_val = next(k['value'] for k in MUSIC_KEYS if k['name'] == k_in)
        req_d_val = (k_val - TONGYIN_OFFSETS[f_in] + 12) % 12
        
        found = [d['name'] for d in ALL_DIZIS if d['value'] == req_d_val]
        res_html = f"需使用: <b>{' / '.join(found)} 调笛</b>"

    st.markdown(f"""
    <div style="text-align:center; padding:20px; background:#ecfdf5; border-radius:12px; margin-top:20px; font-size:1.5rem; color:#064e3b;">
        {res_html}
    </div>
    """, unsafe_allow_html=True)

st.write("---")
st.caption("© 2025 竹笛变调大师 (Python Edition)")
