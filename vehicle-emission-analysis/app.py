import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
import openpyxl  # 用于读取Excel文件

# 设置页面标题和布局
st.set_page_config(page_title="排放数据分析", layout="wide")
st.title("车辆排放数据三维可视化")

# 文件上传组件
uploaded_file = st.file_uploader("上传Excel数据文件", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 读取Excel文件，跳过第一行空白，使用第二行作为列名
        df = pd.read_excel(uploaded_file, skiprows=1)
        
        # 重命名列以便更容易访问
        df.columns = ['时间', 'Lambda', '催化器温度', 'CO原排', 'CO尾排', 
                     'THC原排', 'THC尾排', 'NOx原排', 'NOx尾排', '流量']
        
        st.success("数据加载成功！")
        
        # 显示数据基本信息
        st.subheader("数据概览")
        col1, col2, col3 = st.columns(3)
        col1.metric("数据点数", len(df))
        col2.metric("时间范围", f"{df['时间'].min():.1f} - {df['时间'].max():.1f}秒")
        col3.metric("流量范围", f"{df['流量'].min():.2f} - {df['流量'].max():.2f}")
        
        # 计算转化效率
        def calculate_conversion(original, tail):
            conversion = (1 - tail/original) * 100
            conversion = np.where(conversion < 0, 0, conversion)
            conversion = np.where(conversion > 100, 100, conversion)
            return conversion
        
        df['CO转化效率'] = calculate_conversion(df['CO原排'], df['CO尾排'])
        df['THC转化效率'] = calculate_conversion(df['THC原排'], df['THC尾排'])
        df['NOx转化效率'] = calculate_conversion(df['NOx原排'], df['NOx尾排'])
        
        # 创建自定义颜色刻度
        colorscale = [
            [0.0, "darkblue"],    # 0% - 深蓝色
            [0.5, "green"],       # 50% - 绿色
            [0.7, "orange"],      # 70% - 橘红色
            [0.9, "darkred"],     # 90% - 深红色
            [1.0, "darkred"]      # 100% - 深红色
        ]
        
        # 创建网格数据进行插值
        def create_interpolated_data(x, y, z, grid_points=100):
            # 创建网格
            xi = np.linspace(x.min(), x.max(), grid_points)
            yi = np.linspace(y.min(), y.max(), grid_points)
            xi, yi = np.meshgrid(xi, yi)
            
            # 插值
            zi = griddata((x, y), z, (xi, yi), method='linear')
            
            return xi, yi, zi
        
        # 为每种污染物创建图表
        pollutants = ['CO', 'THC', 'NOx']
        
        for pollutant in pollutants:
            st.subheader(f"{pollutant}转化效率三维可视化")
            
            # 获取数据
            x = df['流量'].values
            y = df['催化器温度'].values
            z = df[f'{pollutant}转化效率'].values
            
            # 创建插值数据
            xi, yi, zi = create_interpolated_data(x, y, z)
            
            # 创建3D曲面图
            fig = go.Figure(data=[go.Surface(
                x=xi, 
                y=yi, 
                z=zi,
                colorscale=colorscale,
                colorbar=dict(title='转化效率 (%)', titleside='right'),
                hovertemplate='<b>流量</b>: %{x:.2f}<br>' +
                            '<b>温度</b>: %{y:.2f}<br>' +
                            '<b>转化效率</b>: %{z:.2f}%<extra></extra>'
            )])
            
            fig.update_layout(
                title=f'{pollutant}转化效率 vs 流量 vs 温度',
                scene=dict(
                    xaxis_title='流量',
                    yaxis_title='催化器温度',
                    zaxis_title='转化效率 (%)',
                    zaxis=dict(range=[0, 100])
                ),
                autosize=True,
                height=600,
                margin=dict(l=65, r=50, b=65, t=90)
            )
            
            # 显示图表
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示统计信息
            col1, col2, col3 = st.columns(3)
            col1.metric(f"{pollutant}平均转化效率", f"{df[f'{pollutant}转化效率'].mean():.2f}%")
            col2.metric(f"{pollutant}最大转化效率", f"{df[f'{pollutant}转化效率'].max():.2f}%")
            col3.metric(f"{pollutant}最小转化效率", f"{df[f'{pollutant}转化效率'].min():.2f}%")
        
    except Exception as e:
        st.error(f"处理数据时出错: {str(e)}")
else:
    st.info("请上传Excel数据文件以开始分析。")
    
# 添加使用说明
with st.expander("使用说明"):
    st.markdown("""
    1. 上传Excel数据文件，格式要求：
       - 第一行应为空白行
       - 第二行包含列名：时间、Lambda、催化器温度、CO原排、CO尾排、THC原排、THC尾排、NOx原排、NOx尾排、流量
       - 数据应从第三行开始
    2. 应用将自动计算三种污染物(CO、THC、NOx)的转化效率
    3. 转化效率计算公式：(1 - 尾排/原排) × 100%
    4. 转化效率限制在0-100%范围内
    5. 使用插值法填补缺失数据，创建连续曲面
    6. 颜色映射：
       - 0%: 深蓝色
       - 50%: 绿色
       - 70%: 橘红色
       - 90%及以上: 深红色
    """)
