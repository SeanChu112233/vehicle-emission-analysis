import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
import openpyxl  # 用于读取Excel文件

# 设置页面标题和布局
st.set_page_config(page_title="排放数据分析", layout="wide")
st.title("车辆排放数据三维可视化")

# 添加说明
st.info("""
此应用可视化车辆排放数据，展示流量、温度和三种污染物(CO、THC、NOx)转化效率之间的关系。
转化效率计算公式：(1 - 尾排/原排) × 100%，限制在0-100%范围内。
""")

# 文件上传组件
uploaded_file = st.file_uploader("上传Excel数据文件", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 读取Excel文件，跳过第一行空白，使用第二行作为列名
        df = pd.read_excel(uploaded_file, skiprows=1, engine='openpyxl')
        
        # 检查数据列数
        if len(df.columns) < 10:
            st.error("数据文件列数不足，请确保文件包含所有必需的列")
            st.stop()
        
        # 重命名列以便更容易访问
        df.columns = ['时间', 'Lambda', '催化器温度', 'CO原排', 'CO尾排', 
                     'THC原排', 'THC尾排', 'NOx原排', 'NOx尾排', '流量']
        
        st.success("数据加载成功！")
        
        # 显示数据基本信息
        st.subheader("数据概览")
        col1, col2, col3 = st.columns(3)
        col1.metric("数据点数", len(df))
        col1.metric("时间范围", f"{df['时间'].min():.1f} - {df['时间'].max():.1f}秒")
        col2.metric("流量范围", f"{df['流量'].min():.2f} - {df['流量'].max():.2f}")
        col3.metric("温度范围", f"{df['催化器温度'].min():.2f} - {df['催化器温度'].max():.2f}")
        
        # 检查数据有效性
        st.subheader("数据质量检查")
        for col in ['CO原排', 'CO尾排', 'THC原排', 'THC尾排', 'NOx原排', 'NOx尾排']:
            zero_count = (df[col] == 0).sum()
            if zero_count > 0:
                st.warning(f"列 '{col}' 中有 {zero_count} 个零值，可能会影响转化效率计算")
        
        # 计算转化效率
        def calculate_conversion(original, tail):
            # 避免除零错误
            mask = (original > 0) & (tail >= 0)
            conversion = np.zeros_like(original)
            conversion[mask] = (1 - tail[mask]/original[mask]) * 100
            
            # 限制在0-100%范围内
            conversion = np.where(conversion < 0, 0, conversion)
            conversion = np.where(conversion > 100, 100, conversion)
            return conversion
        
        # 添加进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("计算CO转化效率...")
        df['CO转化效率'] = calculate_conversion(df['CO原排'].values, df['CO尾排'].values)
        progress_bar.progress(33)
        
        status_text.text("计算THC转化效率...")
        df['THC转化效率'] = calculate_conversion(df['THC原排'].values, df['THC尾排'].values)
        progress_bar.progress(66)
        
        status_text.text("计算NOx转化效率...")
        df['NOx转化效率'] = calculate_conversion(df['NOx原排'].values, df['NOx尾排'].values)
        progress_bar.progress(100)
        
        status_text.text("计算完成!")
        
        # 创建自定义颜色刻度
        colorscale = [
            [0.0, "darkblue"],    # 0% - 深蓝色
            [0.5, "green"],       # 50% - 绿色
            [0.7, "orange"],      # 70% - 橘红色
            [0.9, "darkred"],     # 90% - 深红色
            [1.0, "darkred"]      # 100% - 深红色
        ]
        
        # 创建网格数据进行插值
        def create_interpolated_data(x, y, z, grid_points=50):
            # 过滤无效数据点
            mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(z))
            x_filtered = x[mask]
            y_filtered = y[mask]
            z_filtered = z[mask]
            
            # 确保有足够的数据点进行插值
            if len(x_filtered) < 10:
                return None, None, None
                
            # 创建网格
            xi = np.linspace(x_filtered.min(), x_filtered.max(), grid_points)
            yi = np.linspace(y_filtered.min(), y_filtered.max(), grid_points)
            xi, yi = np.meshgrid(xi, yi)
            
            try:
                # 插值
                zi = griddata((x_filtered, y_filtered), z_filtered, (xi, yi), method='linear')
                return xi, yi, zi
            except:
                return None, None, None
        
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
            
            if xi is None:
                st.error(f"无法为{pollutant}创建三维曲面，数据点不足或分布不均匀")
                continue
            
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
        st.info("请确保Excel文件格式正确：第一行为空白，第二行为列名，数据从第三行开始")
else:
    st.info("请上传Excel数据文件以开始分析。")
    
# 添加使用说明
with st.expander("使用说明"):
    st.markdown("""
    ## 数据格式要求
    - Excel文件第一行应为空白行
    - 第二行包含列名：时间、Lambda、催化器温度、CO原排、CO尾排、THC原排、THC尾排、NOx原排、NOx尾排、流量
    - 数据应从第三行开始
    
    ## 计算说明
    - 转化效率计算公式：(1 - 尾排/原排) × 100%
    - 转化效率限制在0-100%范围内
    - 使用线性插值法填补缺失数据，创建连续曲面
    
    ## 颜色映射
    - 0%: 深蓝色
    - 50%: 绿色
    - 70%: 橘红色
    - 90%及以上: 深红色
    
    ## 交互功能
    - 使用鼠标拖动可旋转三维图形
    - 使用滚轮可缩放图形
    - 点击图例可切换显示/隐藏数据系列
    """)
