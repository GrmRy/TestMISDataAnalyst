import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(page_title="Dashboard Contact Center ", layout="wide")
st.title("Dashboard Contact Center")

# ========================
# LOAD DATA
# ========================
@st.cache_data
def load_kpi_data():
    data = pd.read_csv("RAW KPI metric.csv")
    data['Date'] = pd.to_datetime(data['Date'] + '-2025', format='%d-%b-%Y')
    data['AHT (s)'] = pd.to_numeric(data['AHT (s)'].str.replace(',', '.'), errors='coerce')
    data['Avg. Latency (s)'] = pd.to_numeric(data['Avg. Latency (s)'].str.replace(',', '.'), errors='coerce')
    return data

@st.cache_data
def load_attendance_data():
    # Membaca file attendance dengan skiprows=1 agar baris pertama (nama hari) dilewati
    att = pd.read_csv("Raw Attandance.csv", skiprows=2)
    # Rename kolom pertama dan kedua
    att.rename(columns={att.columns[0]: "No", att.columns[1]: "Employee_Name"}, inplace=True)
    return att

df_kpi = load_kpi_data()
df_attendance_raw = load_attendance_data()

# ========================
# PROSES DATA ATTENDANCE
# ========================
# Ubah format data attendance dari wide ke long
attendance_melted = df_attendance_raw.melt(
    id_vars=["No", "Employee_Name"],
    var_name="Date",
    value_name="Status"
)
# Ubah kolom Date menjadi datetime dengan menambahkan tahun (2025)
attendance_melted["Date"] = pd.to_datetime(attendance_melted["Date"] + "-2025",
                                           format="%d-%b-%Y",
                                           errors="coerce")

# Definisikan kode shift kerja (hadir) dan kode leave (tidak hadir)
present_codes = ["P1", "P2", "P3", "P4", "P10", "S1", "S2", "S4", "S5", "S6", "S7", "M1", "M3", "M4", "M5", "M6", "M7"]
# leave_codes bisa dipakai jika perlu analisis terpisah, tapi untuk penandaan hadir kita cukup cek apakah status ada di present_codes
attendance_melted["Present"] = attendance_melted["Status"].apply(lambda x: 1 if x in present_codes else 0)

# Hitung total karyawan hadir per hari
df_att_daily = attendance_melted.groupby("Date", as_index=False)["Present"].sum()
df_att_daily.rename(columns={"Present": "Total_Present"}, inplace=True)

# ========================
# SIDEBAR FILTER (KPI)
# ========================
st.sidebar.header("Filter Data")

# Filter Tanggal untuk KPI
min_date = df_kpi['Date'].min()
max_date = df_kpi['Date'].max()
selected_dates = st.sidebar.date_input("Pilih rentang tanggal:", [min_date, max_date])
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    df_kpi = df_kpi[(df_kpi['Date'] >= pd.to_datetime(start_date)) & (df_kpi['Date'] <= pd.to_datetime(end_date))]
else:
    st.sidebar.error("Silakan pilih rentang tanggal dengan benar.")

# Filter Queue
queues = df_kpi['Queue'].unique().tolist()
selected_queue = st.sidebar.multiselect("Pilih Queue:", queues, default=queues)
df_kpi = df_kpi[df_kpi['Queue'].isin(selected_queue)]

# ========================
# RINGKASAN KPI
# ========================
col1, col2, col3, col4, col5 = st.columns(5)
total_input = df_kpi['Total Input'].sum()
total_output = df_kpi['Total Output'].sum()
avg_aht = df_kpi['AHT (s)'].mean()
avg_latency = df_kpi['Avg. Latency (s)'].mean()
efficiency = (total_output / total_input * 100) if total_input != 0 else 0

col1.metric("Total Input", f"{int(total_input):,}")
col2.metric("Total Output", f"{int(total_output):,}")
col3.metric("Rata-rata AHT (s)", f"{avg_aht:,.2f}")
col4.metric("Rata-rata Latency (s)", f"{avg_latency:,.2f}")
col5.metric("Efisiensi (%)", f"{efficiency:,.2f}%")
st.write("---")

# ========================
# VISUALISASI KPI
# ========================

# 1) Total Input vs. Total Output Over Time
df_date = df_kpi.groupby('Date', as_index=False).agg({
    'Total Input': 'sum',
    'Total Output': 'sum'
})
fig_input_output = px.line(
    df_date, x='Date', y=['Total Input', 'Total Output'],
    markers=True, title="Total Input vs. Total Output",
    color_discrete_sequence=px.colors.qualitative.Set2
)
fig_input_output.update_layout(xaxis_title="Date", yaxis_title="Volume")

# 2) AHT Over Time
df_aht = df_kpi.groupby('Date', as_index=False)['AHT (s)'].mean()
fig_aht = px.line(
    df_aht, x='Date', y='AHT (s)',
    markers=True, title="AHT Over Time",
    color_discrete_sequence=["#1f77b4"]
)
fig_aht.update_layout(xaxis_title="Date", yaxis_title="AHT (s)")

# 3) Latency Over Time
df_lat = df_kpi.groupby('Date', as_index=False)['Avg. Latency (s)'].mean()
fig_latency = px.line(
    df_lat, x='Date', y='Avg. Latency (s)',
    markers=True, title="Latency Over Time",
    color_discrete_sequence=["#d62728"]
)
fig_latency.update_layout(xaxis_title="Date", yaxis_title="Latency (s)")

# 4) Queue Performance
df_queue = df_kpi.groupby('Queue', as_index=False).agg({
    'Total Input': 'sum',
    'Total Output': 'sum'
})
fig_queue = px.bar(
    df_queue, x='Queue', y=['Total Input', 'Total Output'],
    barmode='group', title="Queue Performance",
    color_discrete_sequence=px.colors.qualitative.Set2
)
fig_queue.update_layout(xaxis_title="Queue", yaxis_title="Volume")

# 5) Anomaly Detection (AHT & Latency)
df_daily = df_kpi.groupby('Date', as_index=False).agg({
    'AHT (s)': 'mean',
    'Avg. Latency (s)': 'mean'
})
aht_threshold = df_daily['AHT (s)'].quantile(0.95)
latency_threshold = df_daily['Avg. Latency (s)'].quantile(0.95)
df_daily['AHT_Anomaly'] = df_daily['AHT (s)'] > aht_threshold
df_daily['Latency_Anomaly'] = df_daily['Avg. Latency (s)'] > latency_threshold
df_daily['AHT_Anomaly_Label'] = df_daily['AHT_Anomaly'].replace({True: 'Anomaly', False: 'Normal'})
df_daily['Latency_Anomaly_Label'] = df_daily['Latency_Anomaly'].replace({True: 'Anomaly', False: 'Normal'})

fig_anom = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         subplot_titles=[f"AHT (Threshold: {aht_threshold:.2f})",
                                         f"Latency (Threshold: {latency_threshold:.2f})"])
line_aht = px.line(df_daily, x='Date', y='AHT (s)').data[0]
line_aht.name = "AHT"
fig_anom.add_trace(line_aht, row=1, col=1)
scatter_aht = px.scatter(
    df_daily, x='Date', y='AHT (s)', color='AHT_Anomaly_Label',
    color_discrete_map={'Normal': 'blue', 'Anomaly': 'red'}
).data
for trace in scatter_aht:
    fig_anom.add_trace(trace, row=1, col=1)
line_lat = px.line(df_daily, x='Date', y='Avg. Latency (s)').data[0]
line_lat.name = "Latency"
fig_anom.add_trace(line_lat, row=2, col=1)
scatter_lat = px.scatter(
    df_daily, x='Date', y='Avg. Latency (s)', color='Latency_Anomaly_Label',
    color_discrete_map={'Normal': 'blue', 'Anomaly': 'red'}
).data
for trace in scatter_lat:
    fig_anom.add_trace(trace, row=2, col=1)
fig_anom.update_layout(title="Deteksi Anomali AHT & Latency", height=600)

# ========================
# ATTENDANCE ANALYSIS VISUALIZATIONS
# ========================
st.write("## Attendance Analysis")

# Bar Chart: Distribusi Status Kehadiran
status_counts = attendance_melted['Status'].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]
fig_status_dist = px.bar(
    status_counts, x='Status', y='Count',
    title="Distribusi Status Kehadiran",
    color='Status',
    color_discrete_sequence=px.colors.qualitative.Set2
)

# Line Chart: Total Karyawan Hadir per Hari
fig_att_daily = px.line(
    df_att_daily.sort_values('Date'), x='Date', y='Total_Present',
    title="Total Karyawan Hadir per Hari",
    markers=True,
    color_discrete_sequence=["#2ca02c"]
)

# Korelasi: Total Karyawan Hadir vs. Total Output (Daily)
df_kpi_daily = df_kpi.groupby('Date', as_index=False).agg({
    'Total Input': 'sum',
    'Total Output': 'sum'
})
df_merge = pd.merge(df_kpi_daily, df_att_daily, on='Date', how='left').fillna(0)
fig_corr = px.scatter(
    df_merge, x='Total_Present', y='Total Output',
    trendline="ols", title="Korelasi Karyawan Hadir vs. Output (Daily)",
    labels={'Total_Present': 'Karyawan Hadir', 'Total Output': 'Total Output'},
    color_discrete_sequence=["#d62728"]
)

colA, colB = st.columns(2)
with colA:
    st.plotly_chart(fig_status_dist, use_container_width=True)
with colB:
    st.plotly_chart(fig_att_daily, use_container_width=True)

st.plotly_chart(fig_corr, use_container_width=True)

# ========================
# TAMPILKAN KPI VISUALIZATIONS
# ========================
st.write("## KPI Visualizations")

colX, colY = st.columns(2)
with colX:
    st.plotly_chart(fig_input_output, use_container_width=True)
with colY:
    st.plotly_chart(fig_aht, use_container_width=True)

colZ, colW = st.columns(2)
with colZ:
    st.plotly_chart(fig_latency, use_container_width=True)
with colW:
    st.plotly_chart(fig_queue, use_container_width=True)

st.plotly_chart(fig_anom, use_container_width=True)

