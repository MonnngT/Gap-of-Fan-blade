import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
import re
import time

# ==========================================
# 1. 基础配置 & 谷歌表格连接
# ==========================================
st.set_page_config(page_title="扇叶间隙录入系统", page_icon="📏", layout="wide")

# 谷歌表格名称
SHEET_NAME = "Gap_Data"

# --- [加速锁 1] 缓存连接资源 ---
@st.cache_resource(ttl=3600)
def get_google_sheet():
    """连接到 Google Sheets"""
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 未找到 Secrets 配置。")
            return None
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ 连接失败: {str(e)}")
        return None

# --- [加速锁 2] 缓存数据读取 ---
@st.cache_data(ttl=10)
def load_data(_sheet):
    """读取所有数据并转换为 DataFrame"""
    try:
        data = _sheet.get_all_records()
        if not data: return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

# ==========================================
# A. 扇叶型号数据库
# ==========================================
Z_SERIES_FANS = {
    "1ZL/PAG/GREY Fan blade": "11100200027", "1ZL/PAGI Fan blade": "11100500027", "1ZR/PPG Fan blade": "11130100027",
    "1ZR/PAG/GREY Fan blade": "11130200027", "1ZR/PAG/Black Fan blade": "11131300027", "2ZL/PPG Fan blade": "12100100027",
    "2ZL/PAG/GREY Fan blade": "12100200027", "2ZL/PAGAS Fan blade": "12100300027", "2ZL/PAGI Fan blade": "12100500027",
    "2ZL/AL Fan blade": "12100700058", "2Z2L/PAG/GREY Fan blade": "12102400227", "2ZL/PAGV1 Fan blade": "12102500027",
    "2ZR/PAG/BLACK Fan blade": "12131300027", "2Z2R/PAG/BLACK Fan blade": "12131300227", "3ZL/AL Fan blade": "13100700091",
    "3ZL/PAGI Fan Blade": "13101500012", "4ZL/PPG Fan Blade": "14100100049", "4ZL/PAG Fan Blade": "14100200049",
    "4ZL/PAGAS Fan Blade": "14100300049", "4ZL/PAG/BLACK Fan Blade": "14100500049", "4ZL/AL Fan Blade": "14100700064",
    "4ZL/PAGV1 Fan Blade": "14102500049", "4ZR/PPG Fan Blade": "14130100050", "4ZR/PAG Fan Blade": "14130200050",
    "4ZR/PAGAS Fan Blade": "14130300050", "4ZR/PAG/BLACK Fan Blade": "14130500050", "4ZR/PAGI Fan Blade": "14130600050",
    "4ZR/AL Fan Blade": "14130700065", "4ZR/PAGV1 Fan blade": "14132500050", "5ZL/PPG Fan Blade": "15100100018",
    "5ZL/PAG Fan Blade": "15100200018", "5ZL/PAGAS Fan Blade": "15100300018", "5ZL/PAGI Fan blade": "15100500018",
    "5ZL/AL Fan blade": "15100700023", "5ZR/PPG Fan Blade": "15130100036", "5ZR/PAG Fan Blade": "15130200036",
    "5ZR/PAGAS Fan Blade": "15130300036", "5ZR/PAGST Fan Blade": "15130400036", "5ZR/PAGI Fan Blade": "15130500036",
    "5ZR/AL Fan Blade": "15130700066", "7ZL/PPG Fan Blade": "17100100008", "7ZL/PAG/GREY Fan blade": "17102400008",
    "7ZL/PAGAS Fan Blade": "17103100008", "7ZR/PPG Fan blade": "17130100009", "7ZR/PAG/GREY Fan blade": "17132400009",
    "TR7ZL/AL Fan Blade": "17170700078", "TR7ZR/AL Fan Blade": "17170700087",
    "6ZL/PPG Fan blade": "16180100081", "6ZR/PPG Fan blade": "16180100081", "6ZL/PAG Fan blade": "16180200081",
    "6ZR/PAG Fan blade": "16180200081", "6ZL/PAG/BLACK Fan blade": "16181300081", "6ZR/PAG/BLACK Fan blade": "16181300081",
    "TR7ZL/PPG Fan blade": "17170100087", "TR7ZR/PPG Fan blade": "17170100087", "TR8ZL/AL Fan Blade": "18170700094",
    "TR8ZR/AL Fan Blade": "18170700094"
}
EMAX_SERIES_FANS = {"EMAX 4L/PAG Fan Blade": "14400200059", "EMAX 4R/PAG Fan Blade": "14430200060"}
W_SERIES_FANS = {
    "1WL/PPG/LP Fan Blade": "11700100084", "1WL/PAG/LP Fan blade": "11700200084", "1WL/PAGAS/LP Fan blade": "11700300084",
    "1WL/PAG/BLACK/LP Fan blade": "11701300084", "1WL/PAGV1/LP Fan blade": "11702500084", "1WR/PPG/LP Fan Blade": "11730100062",
    "1WR/PAG/LP Fan blade": "11730200062", "1WR/PAG/BLACK/LP Fan blade": "11731300062", "6WL/PPG/LP Fan blade": "16700100043",
    "6WL/PPG/L=390/LP Fan blade": "16700100049", "6WL/PAG/LP Fan blade": "16700200043", "6WL/PAGAS/LP Fan blade": "16700300043",
    "6WL/PAG/BLACK/LP Fan blade": "16700500043", "6WR/PPG/LP Fan blade": "16730100037", "6WR/PAG/LP Fan blade": "16730200037",
    "6WR/PAGAS/LP Fan blade": "16730300037", "7WL/PPG/LP Fan blade": "17700100084", "9W2L/PPG/LP Fan blade": "19700100084",
    "9W2L/PAG/LP Fan blade": "19700200084", "1WL/PAG Fan Blade": "11700200095", "1WR/PAG Fan Blade": "11730200096",
    "2WL/PPG Fan blade": "12700100021", "2WL/PAG Fan blade": "12700200021", "3WL/PAG Fan blade": "13700200056",
    "5WL/PAG Fan blade": "15700200095", "5WL/AL Fan blade": "15700700014", "5WR/PAG Fan blade": "15730200096",
    "5WR/AL Fan blade": "15730700061", "6WL/PAG Fan blade": "16700200095", "6WL/AL Fan Blade": "16700700026",
    "6WR/PAG Fan blade": "16730200096", "6WR/AL Fan Blade": "16730700085", "7WL/PPG Fan blade": "17700100039",
    "7WL/PAG Fan blade": "17700200039", "7WL/PAGAS Fan blade": "17700300039", "7WR/PPG Fan blade": "17730100038",
    "7WR/PAG Fan blade": "17730200038", "9WL/PPG Fan blade": "19700100063", "9W2L/PPG Fan blade": "19700100064",
    "9WL/PAG Fan blade": "19700200063", "9W2L/PAG Fan blade": "19700200064", "9W2L/PAG/LP Fan blade": "19700200084",
    "9WL/AL Fan blade": "19700700033", "9W2R/PPG Fan blade": "19730100030", "9W2R/PAG Fan blade": "19730200030",
    "9WR/PAG Fan blade": "19730200031", "9WR/PAGAS Fan blade": "19730300031", "9W2R/PAG/BLACK Fan blade": "19730500030",
    "9WR/AL Fan blade": "19730700034", "9W2R/PAG6-C Fan Blade": "19733700030", "3WTR/PAG50/GREY-UV Fan blade": "19951200029",
    "3WTR/PAG50/BLACK Fan blade": "19951300029", "8WL/PPG Fan blade": "18780100019", "8WR/PPG Fan blade": "18780100019",
    "8WL/PAG Fan blade": "18780200019", "8WR/PAG Fan blade": "18780200019", "8WL/PAGAS Fan blade": "18780300019",
    "8WR/PAGAS Fan blade": "18780300019", "8WL/PAGV1/L=355 Fan blade": "18782500024", "8WR/PAGV1/L=355 Fan blade": "18782500024",
    "TR11WL/AL Fan Blade": "19770700086", "TR11WR/AL Fan Blade": "19770700086"
}
W_SERIES_YELLOW_KEYS = {
    "1WL/PPG/LP Fan Blade", "1WL/PAG/LP Fan blade", "1WL/PAGAS/LP Fan blade", "1WL/PAG/BLACK/LP Fan blade", "1WL/PAGV1/LP Fan blade",
    "1WR/PPG/LP Fan Blade", "1WR/PAG/LP Fan blade", "1WR/PAG/BLACK/LP Fan blade", "6WL/PPG/LP Fan blade", "6WL/PPG/L=390/LP Fan blade",
    "6WL/PAG/LP Fan blade", "6WL/PAGAS/LP Fan blade", "6WL/PAG/BLACK/LP Fan blade", "6WR/PPG/LP Fan blade", "6WR/PAG/LP Fan blade",
    "6WR/PAGAS/LP Fan blade", "7WL/PPG/LP Fan blade", "9W2L/PPG/LP Fan blade", "9W2L/PAG/LP Fan blade"
}
G_SERIES_FANS = {"1GL/PPG Fan blade": "11710100089", "1GL/PAG/BLACK Fan blade": "11710200089", "10GL/PAG/BLACK Fan blade": "11801300088", "10GR/PAG/BLACK Fan Blade": "11831300042"}
P_SERIES_Z_USE = {"PMAX4L/PAG/GREY Fan Blade": "14702400093", "PMAX4R/PAG/GREY Fan Blade": "14732400094", "PressureMAX 6L/PAG Fan Blade": "16900200079", "PressureMAX 6R/PAG Fan Blade": "16930200074"}
P_SERIES_W_USE = {"PMAX5L/PAG/BLACK Fan Blade": "15601300045", "PMAX5R/PAG/BLACK Fan Blade": "15631300047"}
P_SERIES_ORIGINAL = {"PMAX3L/PAG/GREY Fan Blade": "13900200059", "PMAX3R/PAG/GREY Fan Blade": "13932400060"}
ALL_FANS_DB = {**Z_SERIES_FANS, **EMAX_SERIES_FANS, **W_SERIES_FANS, **G_SERIES_FANS, **P_SERIES_Z_USE, **P_SERIES_W_USE, **P_SERIES_ORIGINAL}

# ==========================================
# B. 盘配置数据库
# ==========================================
DISC_CONFIG_Z = {
    "Z5盘": ["Retaining plate/5 (PN: 21050700103) X2", "Retaining plate/5 + Hub plate/5/184018 (Ret:21050700103, Hub:21050700603)", "Retaining plate/5 + Hub plate/5/000010 (Ret:21050700103, Hub:21050702503)", "Retaining plate/5 + Hub plate/5/424412 (Ret:21050700103, Hub:21050702603)", "Retaining plate/5 + Hub plate/5/625212 (Ret:21050700103, Hub:21050704403)", "Retaining plate/5 + Hub plate/5/625223 (Ret:21050700103, Hub:21050708503)", "Retaining plate/5 + Hub Plate/5/825215 (Ret:21050700103, Hub:21050709403)"],
    "Z6盘": ["Retaining plate/6 + Hub plate/6/000015 (Ret:21060702406, Hub:21060702506)", "Retaining plate/6/000075 (PN: 21060708106) X2"],
    "Z6L盘": ["Retaining plate/6L + Hub Plate/6L/000075 (Ret:21060709211, Hub:21060708111)", "Retaining plate/6L + Hub Plate/6L/000015 (Ret:21060709211, Hub:21060709311)"],
    "Z7盘": ["Retaining plate/7/100 + Hub Plate/7/000015/100 (Ret:21070702806, Hub:21070703006)", "Retaining plate/7/000075 (PN: 21070708109) X2"],
    "Z8盘": ["Retaining plate/8/140 + Hub plate/8/000015/140 (Ret:21080702806, Hub:21080703006)", "Retaining plate/8/000075 (PN: 21080708109) X2"],
    "Z9盘": ["Retaining plate/9/110 + Hub plate/9/000015/110 (Ret:21090702806, Hub:21090703006)", "Retaining plate/9/000075 (PN: 21090708103) X2"],
    "Z9L盘": ["Retaining Plate/9L/000015 (PN: 21096703011) X2"],
    "Z12盘": ["Retaining plate/12 + Hub plate/12/000019 (Ret:21120702403, Hub:21120702503)", "Retaining plate/12 + Hub Plate/12/000070 (Ret:21120702403, Hub:21120706503)", "Retaining plate/12/000075 (PN: 21120708103) X2"],
    "Z16盘": ["Retaining plate/16 + Hub plate/16/000040 (Ret:21160702403, Hub:21160711903)", "Retaining plate/16 + Hub plate/16/000075 (Ret:21160702403, Hub:21160712103)"]
}
DISC_CONFIG_W_YELLOW = {"W3盘": ["W-Retaining plate/3/LP (PN: 27030701203) X2"], "W4盘": ["W-Retaining plate/4/LP (PN: 27040701303) X2"], "W5盘": ["W-Retaining plate/5/LP (PN: 27050701403) X2"]}
DISC_CONFIG_W_OTHER = {
    "W5盘": ["W-Retaining plate/5 (PN: 27050704606) X2", "W-Retaining plate/5/Flange + W-Hub Plate/5/Flange (Ret: 27050714006, Hub: 27050714106)", "W-Retaining plate/5/HP (PN: 27050904606) X2"],
    "W6盘": ["W-Retaining plate/6 (PN: 27060704606) X2", "W-Retaining plate/6/Flange + W-Hub Plate/6/Flange (Ret: 27060714006, Hub: 27060714106)", "W-Retaining plate/6/HP (PN: 27060904606) X2"],
    "W7盘": ["W-Retaining Plate/7/40/312 (PN: 27070702511) X2", "W-Retaining Plate/7/312 (PN: 27070740011) X2"],
    "W8盘": ["W-Retaining plate/8 (PN: 27080704606) X2", "W-Retaining plate/8/Flange + W-Hub plate/8/Flange (Ret: 27080714006, Hub: 27080714106)", "W-Retaining plate/8/HP (PN: 27080904606) X2"],
    "W9盘": ["W-Retaining plate/9/Flange + W-Hub plate/9/Flange (Ret: 27090714006, Hub: 27090714106)"],
    "W10盘": ["W-Retaining plate/10 (PN: 27100704606) X2", "W-Retaining plate/10/Flange + W-Hub plate/10/Flange (Ret: 27100714006, Hub: 27100714106)", "W-Retaining plate/10/HP (PN: 27100804606) X2"],
    "W11盘": ["W-Retaining Plate/11 (PN: 27110704606) X2"],
    "W13盘": ["W-Retaining plate/13/HP/110 (PN: 27130804800) X2", "W-Retaining plate/13/HP/136,6 (PN: 27130804900) X2"]
}
DISC_CONFIG_G = {"G3盘": ["G-Retaining plate/3 (PN: 28030805500) X2"], "G5盘": ["G-Retaining plate/5 (PN: 28050805500) X2"], "G6盘": ["G-Retaining Plate/6 (PN: 28060805500) X2"], "G8盘": ["G-Retaining Plate/8 (PN: 28080805500) X2"]}
DISC_CONFIG_P = {"PMAX9盘 (PMAX40系列)": ["PMAX40-Retaining Plate/9 + Hub Plate/9/Flange (Ret: 23090702801, Hub: 23090714101)", "PMAX40-Retaining Plate/9 + Hub Plate/9/T13 (Ret: 23090702801, Hub: 23090779001)"]}
ANGLES_LIST = [16.5, 20, 21.5, 22.5, 23.5, 24, 25, 26.5, 27.5, 28.5, 29, 30, 31, 31.5, 32.5, 33.5, 34, 35, 36, 36.5, 37.5, 38.5, 40, 41, 41.5, 42.5, 43.5, 44, 45, 46.5, 47.5, 48.5, 50, 53.5]

def calculate_gap_count(disc_type_str):
    numbers = re.findall(r'\d+', disc_type_str)
    if not numbers: return 0
    num = int(numbers[0])
    if "Z" in disc_type_str:
        if num == 12: return 12
        elif num == 16: return 16
        else: return num * 2
    else:
        return num * 2

# ==========================================
# 2. 侧边栏 & 连接测试
# ==========================================
sheet = get_google_sheet()
is_connected = sheet is not None
with st.sidebar:
    st.header("⚙️ 系统状态")
    if is_connected:
        st.success("✅ 已连接到 Google Sheets")
    else:
        st.error("❌ 未连接到云端数据库")
        st.info("请检查 Secrets 配置")
        st.stop() 

# ==========================================
# 3. 交互区域
# ==========================================
st.title("📏 间隙测量数据记录系统")

st.markdown("##### 1️⃣ 请选择扇叶大类")
category_filter = st.radio("Series Filter", ["Z系列", "W系列", "G系列", "EMAX系列", "P系列"], horizontal=True, label_visibility="collapsed")

if category_filter == "Z系列":
    current_fan_db = Z_SERIES_FANS; current_default_disc_db = DISC_CONFIG_Z; series_hint = "Z系列 (标准盘)"
elif category_filter == "W系列":
    current_fan_db = W_SERIES_FANS; current_default_disc_db = DISC_CONFIG_W_OTHER; series_hint = "W系列 (3种专用盘 或 18种通用盘)"
elif category_filter == "G系列":
    current_fan_db = G_SERIES_FANS; current_default_disc_db = DISC_CONFIG_G; series_hint = "G系列 (专用盘)"
elif category_filter == "EMAX系列":
    current_fan_db = EMAX_SERIES_FANS; current_default_disc_db = DISC_CONFIG_Z; series_hint = "EMAX系列 (使用 Z 盘)"
elif category_filter == "P系列":
    current_fan_db = {**P_SERIES_Z_USE, **P_SERIES_W_USE, **P_SERIES_ORIGINAL}; series_hint = "P系列 (自动匹配 Z盘/W盘/P盘)"; current_default_disc_db = DISC_CONFIG_P 

st.write("---")
f1, f2 = st.columns([2, 1])
with f1:
    fan_options = sorted(list(current_fan_db.keys()))
    selected_fan_model = st.selectbox("2️⃣ 选择扇叶型号", fan_options)
with f2:
    fan_pn = current_fan_db[selected_fan_model]
    st.text_input("对应扇叶料号", value=fan_pn, disabled=True)

if category_filter == "W系列":
    if selected_fan_model in W_SERIES_YELLOW_KEYS:
        current_disc_db = DISC_CONFIG_W_YELLOW; db_type_hint = "W系列 (3种专用盘)"
    else:
        current_disc_db = DISC_CONFIG_W_OTHER; db_type_hint = "W系列 (18种通用盘)"
elif category_filter == "P系列":
    if selected_fan_model in P_SERIES_Z_USE: current_disc_db = DISC_CONFIG_Z; db_type_hint = "P系列 (配置为 Z 盘)"
    elif selected_fan_model in P_SERIES_W_USE: current_disc_db = DISC_CONFIG_W_OTHER; db_type_hint = "P系列 (配置为 W 盘)"
    else: current_disc_db = DISC_CONFIG_P; db_type_hint = "P系列 (配置为 PMAX40 盘)"
else:
    current_disc_db = current_default_disc_db; db_type_hint = series_hint

st.caption(f"当前加载盘库: {db_type_hint}")
c1, c2 = st.columns(2)
with c1: selected_disc_type = st.selectbox("3️⃣ 选择盘型号", list(current_disc_db.keys()))
with c2: selected_angle = st.selectbox("4️⃣ 选择角度", ANGLES_LIST)

available_configs = current_disc_db[selected_disc_type]
st.write("---")
selected_config_detail = st.selectbox("5️⃣ 选择具体组合/料号 (完整信息)", available_configs, key=f"combo_{selected_disc_type}")

# ==========================================
# 核心逻辑：云端计数检查 (强壮模式)
# ==========================================
current_count = 0
if is_connected:
    df_cloud = load_data(sheet)
    if not df_cloud.empty:
        required_cols = ["详细配置/料号", "扇叶型号", "盘型号", "角度"]
        if all(col in df_cloud.columns for col in required_cols):
            df_cloud["扇叶型号_clean"] = df_cloud["扇叶型号"].astype(str).str.strip()
            df_cloud["盘型号_clean"] = df_cloud["盘型号"].astype(str).str.strip()
            df_cloud["配置_clean"] = df_cloud["详细配置/料号"].astype(str).str.strip()
            
            target_fan = selected_fan_model.strip(); target_disc = selected_disc_type.strip(); target_config = selected_config_detail.strip()
            df_cloud["角度_val"] = pd.to_numeric(df_cloud["角度"], errors='coerce')
            target_angle_val = float(selected_angle)
            match_df = df_cloud[
                (df_cloud["扇叶型号_clean"] == target_fan) & (df_cloud["盘型号_clean"] == target_disc) &
                (df_cloud["配置_clean"] == target_config) & (abs(df_cloud["角度_val"] - target_angle_val) < 0.01)
            ]
            current_count = len(match_df)

is_limit_reached = current_count >= 3
if is_limit_reached: st.error(f"⚠️ **已达上限！** 该组合已录入 **{current_count}/3** 次。")
else: st.success(f"✅ **状态正常：** 该组合已录入 **{current_count}/3** 次。")

has_hub = "hub" in selected_config_detail.lower()

# ==========================================
# 4. 模具与环境信息录入
# ==========================================
st.write("---")
if has_hub:
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1: work_order = st.text_input("📝 工单号", placeholder="输入工单号...")
    with m_col2: blade_mold = st.text_input("叶片模具号", placeholder="输入模号...")
    with m_col3: plate_mold_1 = st.text_input("Retaining盘模具号", placeholder="输入模号...")
    with m_col4: plate_mold_2 = st.text_input("Hub盘模具号", placeholder="输入模号...")
else:
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: work_order = st.text_input("📝 工单号", placeholder="输入工单号...")
    with m_col2: blade_mold = st.text_input("叶片模具号", placeholder="输入模号...")
    with m_col3: plate_mold_1 = st.text_input("盘模具号 (共用)", placeholder="输入模号...")
    plate_mold_2 = None
st.write("") 
e1, e2, e3 = st.columns(3)
with e1: start_pos = st.selectbox("起始位置说明", ["有刻字", "无刻字"])
with e2: input_temp = st.number_input("🌡️ 温度 (°C)", min_value=-50.0, max_value=100.0, step=0.1, value=None, placeholder="例如: 26.5")
with e3: input_humidity = st.number_input("💧 湿度 (%)", min_value=0, max_value=100, step=1, value=None, placeholder="例如: 55")

# ==========================================
# 5. 数据录入表单
# ==========================================
st.write("---")
data_points_count = calculate_gap_count(selected_disc_type)
st.subheader(f"📝 录入数据: {selected_disc_type} (需录入 {data_points_count} 组)")
with st.form("data_entry_form", clear_on_submit=True):
    input_values = {}
    cols_per_row = 4
    current_cols = None
    for i in range(1, data_points_count + 1):
        col_index = (i - 1) % cols_per_row
        if col_index == 0: current_cols = st.columns(cols_per_row)
        with current_cols[col_index]:
            input_values[f"Pos_{i}"] = st.number_input(f"位置 {i}", min_value=0.0, step=0.01, format="%.2f", key=f"val_{selected_disc_type}_{i}", value=None, placeholder="0.00")
    st.write("")
    btn_label = "💾 提交并保存到云端" if not is_limit_reached else "⛔️ 次数已满"
    submitted = st.form_submit_button(btn_label, type="primary", disabled=is_limit_reached)

# ==========================================
# 6. 保存逻辑
# ==========================================
if submitted:
    if current_count >= 3: st.error("❌ 提交被拒绝：已达上限。")
    else:
        utc_now = datetime.now(timezone.utc)
        beijing_now = utc_now.astimezone(timezone(timedelta(hours=8)))
        current_time_str = beijing_now.strftime("%Y-%m-%d %H:%M:%S")
        vals_list = [v for k, v in input_values.items() if v is not None]
        val_max = max(vals_list) if vals_list else 0
        val_min = min(vals_list) if vals_list else 0
        val_avg = round(sum(vals_list) / len(vals_list), 3) if vals_list else 0
        base_headers = ["录入时间", "工单号", "扇叶型号", "扇叶料号", "盘型号", "详细配置/料号", "角度", "叶片模具号", "盘模具号", "Hub模具号", "起始位置", "温度(°C)", "湿度(%)", "数据量", "最大值", "最小值", "平均值"]
        max_possible_data_cols = 50 
        data_headers = [f"数据_{i}" for i in range(1, max_possible_data_cols + 1)]
        all_headers = base_headers + data_headers
        row_data = [current_time_str, work_order, selected_fan_model, fan_pn, selected_disc_type, selected_config_detail, selected_angle, blade_mold, plate_mold_1, plate_mold_2, start_pos, input_temp, input_humidity, data_points_count, val_max, val_min, val_avg]
        for i in range(1, max_possible_data_cols + 1):
            if i <= data_points_count: row_data.append(input_values.get(f"Pos_{i}", ""))
            else: row_data.append("") 
        try:
            first_row = sheet.row_values(1)
            if not first_row: sheet.append_row(all_headers)
            sheet.append_row(row_data)
            st.success(f"✅ 云端保存成功！{current_time_str}")
            st.cache_data.clear()
            time.sleep(1)
            st.rerun()
        except Exception as e: st.error(f"❌ 云端保存失败: {e}")

# ==========================================
# 7. 历史记录 & 筛选 & 管理 (顶部筛选+可编辑版)
# ==========================================
st.divider()
if is_connected:
    st.subheader("📊 云端历史记录管理")
    
    # 1. 基础数据读取
    df_history = load_data(sheet)
    
    if not df_history.empty:
        # A. 数据清洗
        data_cols = [col for col in df_history.columns if col.startswith("数据_")]
        try: data_cols.sort(key=lambda x: int(x.split('_')[1]))
        except: pass 
        
        valid_data_cols = []
        for col in data_cols:
            temp_col = df_history[col].replace("", pd.NA)
            if not temp_col.dropna().empty: valid_data_cols.append(col)

        base_cols = ["录入时间", "工单号", "扇叶型号", "扇叶料号", "盘型号", "详细配置/料号", "角度", "叶片模具号", "盘模具号", "Hub模具号", "起始位置", "温度(°C)", "湿度(%)", "数据量", "最大值", "最小值", "平均值"]
        final_cols = [c for c in base_cols if c in df_history.columns] + valid_data_cols
        
        # B. 核心步骤：记录原始行号 (删除/修改操作必须依赖它)
        df_history["_original_row_index"] = df_history.index + 2
        
        # --- 🔍 筛选控制面板 ---
        with st.container(border=True):
            st.markdown("##### 🔍 筛选条件")
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                try:
                    df_history["录入时间_dt"] = pd.to_datetime(df_history["录入时间"])
                    min_date = df_history["录入时间_dt"].min().date()
                    max_date = df_history["录入时间_dt"].max().date()
                    date_range = st.date_input("📅 按录入日期筛选", [])
                except:
                    date_range = []
                    st.warning("⚠️ 日期格式解析失败")
            with f_col2:
                unique_fans = sorted(df_history["扇叶型号"].astype(str).unique().tolist())
                selected_fans = st.multiselect("🌀 按扇叶型号筛选", unique_fans, placeholder="默认显示所有")
            with f_col3:
                search_kw = st.text_input("🔍 关键词搜索 (工单/模具号/任意内容)", placeholder="例如：333525")

        # --- C. 应用筛选逻辑 ---
        df_filtered = df_history.copy()
        if len(date_range) == 2:
            start_d, end_d = date_range
            df_filtered = df_filtered[(df_filtered["录入时间_dt"].dt.date >= start_d) & (df_filtered["录入时间_dt"].dt.date <= end_d)]
        if selected_fans: df_filtered = df_filtered[df_filtered["扇叶型号"].isin(selected_fans)]
        if search_kw:
            mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_kw, case=False, na=False)).any(axis=1)
            df_filtered = df_filtered[mask]

        # --- D. 准备显示数据 ---
        df_show = df_filtered[final_cols + ["_original_row_index"]].iloc[::-1].copy()
        df_show.insert(0, "删除?", False)
        
        # 🔥🔥🔥 关键修复：强制转换数值列，防止 StreamlitAPIException 🔥🔥🔥
        numeric_cols = ["温度(°C)", "湿度(%)", "角度"] + valid_data_cols
        for col in numeric_cols:
            if col in df_show.columns:
                df_show[col] = pd.to_numeric(df_show[col], errors='coerce')
        # 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥

        st.caption(f"📊 当前筛选结果：共 **{len(df_show)}** 条 | ✏️ **双击表格内容可直接修改，改完请点击下方【保存修改】按钮**")

        # --- E. 动态构建 column_config ---
        
        # 1. 基础列配置
        my_column_config = {
            "删除?": st.column_config.CheckboxColumn("删除?", help="勾选后点击下方红色按钮删除", default=False, width="small"),
            "_original_row_index": None, # 隐藏
            "录入时间_dt": None, # 隐藏
            "录入时间": st.column_config.TextColumn(disabled=True), # 锁定
            # 文本列
            "工单号": st.column_config.TextColumn(width="medium"),
            "扇叶型号": st.column_config.TextColumn(width="large"),
            "扇叶料号": st.column_config.TextColumn(),
            "盘型号": st.column_config.TextColumn(),
            "详细配置/料号": st.column_config.TextColumn(),
            "叶片模具号": st.column_config.TextColumn(),
            "盘模具号": st.column_config.TextColumn(),
            "Hub模具号": st.column_config.TextColumn(),
            "起始位置": st.column_config.TextColumn(),
            # 数值列 (强制转成 NumberColumn 才能编辑数字)
            "温度(°C)": st.column_config.NumberColumn(format="%.1f", step=0.1),
            "湿度(%)": st.column_config.NumberColumn(format="%d%%", step=1),
            "角度": st.column_config.NumberColumn(format="%.1f", step=0.1),
            "数据量": st.column_config.NumberColumn(disabled=True),
            "最大值": st.column_config.NumberColumn(disabled=True),
            "最小值": st.column_config.NumberColumn(disabled=True),
            "平均值": st.column_config.NumberColumn(disabled=True),
        }

        # 2. 动态添加所有数据列
        for d_col in valid_data_cols:
            my_column_config[d_col] = st.column_config.NumberColumn(required=False, step=0.01)

        # --- 渲染表格 ---
        edited_df = st.data_editor(
            df_show,
            column_config=my_column_config,
            hide_index=True,
            use_container_width=True,
            key="history_editor"
        )

        # --- F. 操作按钮区域 ---
        has_edits = False
        if "history_editor" in st.session_state:
            edits = st.session_state["history_editor"].get("edited_rows", {})
            if edits: has_edits = True

        col_save, col_del, col_dl = st.columns([1.5, 1.5, 3])
        
        # 1. 保存修改
        with col_save:
            if has_edits:
                if st.button("💾 保存修改", type="primary"):
                    try:
                        header_list = sheet.row_values(1)
                        header_map = {name: i+1 for i, name in enumerate(header_list)}
                        status_msg = st.empty()
                        status_msg.info("⏳ 正在保存修改...")
                        
                        edited_rows = st.session_state["history_editor"]["edited_rows"]
                        for row_idx_in_display, changes in edited_rows.items():
                            real_sheet_row = df_show.iloc[row_idx_in_display]["_original_row_index"]
                            for col_name, new_value in changes.items():
                                if col_name in header_map:
                                    col_idx = header_map[col_name]
                                    sheet.update_cell(real_sheet_row, col_idx, new_value)
                        
                        st.success("✅ 修改已保存！")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 保存失败: {e}")
            else:
                st.button("💾 保存修改", disabled=True, help="请先在表格中修改数据")

        # 2. 删除逻辑
        with col_del:
            if st.button("🗑️ 删除选中行"):
                rows_to_delete = edited_df[edited_df["删除?"] == True]
                if rows_to_delete.empty:
                    st.warning("请先勾选需要删除的数据！")
                else:
                    try:
                        sheet_rows = sorted(rows_to_delete["_original_row_index"].tolist(), reverse=True)
                        status_msg = st.empty()
                        status_msg.info(f"⏳ 正在删除 {len(sheet_rows)} 条数据...")
                        for row_idx in sheet_rows: sheet.delete_rows(row_idx)
                        st.success(f"✅ 删除成功！")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"❌ 删除失败: {e}")
        
        # 3. 下载逻辑
        with col_dl:
            st.write("") 
            csv = df_show.drop(columns=["删除?", "_original_row_index"]).to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 导出筛选结果 (Excel)",
                data=csv,
                file_name=f"间隙数据_筛选导出_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

    else:
        st.info("👋 云端暂无数据")
