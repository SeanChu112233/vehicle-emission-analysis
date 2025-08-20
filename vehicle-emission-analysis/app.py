import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata

# 页面设置
st.set_page_config(
    page_title="车辆排放分析系统",
    page_icon="🚗",
    layout="wide"
)

# 自定义颜色映射函数
def custom_colormap(efficiency):
    """创建从深蓝到深红的渐变颜色映射"""
    if efficiency <= 0.5:
        # 0-50%: 深蓝到绿色
        r = int(0)
        g = int(255 * (efficiency / 0.5))
        b = int(255 * (1 - efficiency / 0.5))
    elif efficiency <= 0.7:
        # 50-70%: 绿色到橘红
        r = int(255 * ((efficiency - 0.5) / 0.2))
        g = 255
        b = 0
    else:
        # 70-100%: 橘红到深红
        r = 255
        g = int(255 * (1 - (efficiency - 0.7) / 0.3))
        b = 0
    return f"rgb({r},{g},{b})"

# 计算转化效率
def calculate_efficiency(upstream, downstream):
    """计算转化效率并限制在0-100%之间"""
    # 处理除零错误
    with np.errstate(divide='ignore', invalid='ignore'):
        efficiency = (1 - downstream / upstream) * 100
    
    # 处理无效值
    efficiency = np.nan_to_num(efficiency, nan=0.0)
    
    # 限制在0-100%之间
    efficiency = np.clip(efficiency, 0, 100)
    return efficiency

# 创建三维曲面图
def create_3d_surface(flow, temp, efficiency, pollutant_name):
    """创建可交互的三维曲面图"""
    # 创建网格
    xi = np.linspace(min(flow), max(flow), 100)
    yi = np.linspace(min(temp), max(temp), 100)
    xi, yi = np.meshgrid(xi, yi)
    
    # 插值处理（填充缺失值）
    zi = griddata(
        (flow, temp), 
        efficiency, 
        (xi, yi), 
        method='cubic'
    )
    
    # 创建颜色映射
    colors = np.vectorize(custom_colormap)(zi/100)
    
    # 创建3D曲面
    fig = go.Figure(data=[
        go.Surface(
            x=xi, y=yi, z=zi,
            surfacecolor=colors,
            colorscale=None,
            showscale=False,
            opacity=0.9,
            hoverinfo="x+y+z+name",
            name=pollutant_name
        )
    ])
    
    # 设置图表布局
    fig.update_layout(
        title=f"{pollutant_name}转化效率分析",
        scene=dict(
            xaxis_title='流量 (m³/h)',
            yaxis_title='催化器温度 (°C)',
            zaxis_title='转化效率 (%)',
            zaxis=dict(range=[0, 100]),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        autosize=True,
        height=800,
        margin=dict(l=0, r=0, b=0, t=50)
    )
    
    return fig

# 主程序
def main():
    st.title("🚗 车辆排放三维分析系统")
    st.markdown("上传车辆10Hz排放数据Excel文件，分析CO、THC、NOx的转化效率")
    
    # 文件上传
    uploaded_file = st.file_uploader(
        "上传Excel数据文件", 
        type=["xlsx", "xls"],
        help="请确保文件格式：第一行空白，第二行为列名"
    )
    
    if uploaded_file:
        try:
            # 读取Excel文件（跳过第一行空白）
            df = pd.read_excel(uploaded_file, header=1)
            
            # 重命名列（根据描述的顺序）
            df.columns = [
                '时间', 'Lambda', '催化器温度', 
                'CO原排', 'CO尾排', 
                'THC原排', 'THC尾排',
                'NOx原排', 'NOx尾排', '流量'
            ]
            
            # 数据采样（10Hz数据量太大，降采样到1Hz）
            df = df.iloc[::10, :]
            
            # 显示数据预览
            with st.expander("数据预览（前10行）"):
                st.dataframe(df.head(10))
                
            # 计算转化效率
            df['CO转化率'] = calculate_efficiency(df['CO原排'], df['CO尾排'])
            df['THC转化率'] = calculate_efficiency(df['THC原排'], df['THC尾排'])
            df['NOx转化率'] = calculate_efficiency(df['NOx原排'], df['NOx尾排'])
            
            # 创建三个污染物图表
            pollutants = {
                "CO": df['CO转化率'],
                "THC": df['THC转化率'],
                "NOx": df['NOx转化率']
            }
            
            # 使用选项卡展示三个图表
            tab1, tab2, tab3 = st.tabs(["CO转化率", "THC转化率", "NOx转化率"])
            
            with tab1:
                fig_co = create_3d_surface(
                    df['流量'], 
                    df['催化器温度'], 
                    df['CO转化率'],
                    "CO"
                )
                st.plotly_chart(fig_co, use_container_width=True)
                
            with tab2:
                fig_thc = create_3d_surface(
                    df['流量'], 
                    df['催化器温度'], 
                    df['THC转化率'],
                    "THC"
                )
                st.plotly_chart(fig_thc, use_container_width=True)
                
            with tab3:
                fig_nox = create_3d_surface(
                    df['流量'], 
                    df['催化器温度'], 
                    df['NOx转化率'],
                    "NOx"
                )
                st.plotly_chart(fig_nox, use_container_width=True)
                
            # 添加数据统计信息
            st.subheader("转化效率统计")
            col1, col2, col3 = st.columns(3)
            col1.metric("CO平均转化率", f"{df['CO转化率'].mean():.1f}%")
            col2.metric("THC平均转化率", f"{df['THC转化率'].mean():.1f}%")
            col3.metric("NOx平均转化率", f"{df['NOx转化率'].mean():.1f}%")
            
        except Exception as e:
            st.error(f"数据处理错误: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
