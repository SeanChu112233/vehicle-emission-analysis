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

# 计算转化效率
def calculate_efficiency(upstream, downstream):
    """计算转化效率并限制在0-100%之间"""
    # 处理除零错误和无效值
    efficiency = np.zeros_like(upstream, dtype=float)
    valid_mask = (upstream > 0) & (downstream >= 0)
    
    efficiency[valid_mask] = (1 - downstream[valid_mask] / upstream[valid_mask]) * 100
    efficiency = np.clip(efficiency, 0, 100)
    
    return efficiency

# 创建三维曲面图
def create_3d_surface(flow, temp, efficiency, pollutant_name):
    """创建可交互的三维曲面图"""
    # 创建网格
    xi = np.linspace(min(flow), max(flow), 50)
    yi = np.linspace(min(temp), max(temp), 50)
    xi, yi = np.meshgrid(xi, yi)
    
    # 插值处理（填充缺失值）
    zi = griddata(
        (flow, temp), 
        efficiency, 
        (xi, yi), 
        method='linear',
        fill_value=0
    )
    
    # 创建3D曲面
    fig = go.Figure(data=[
        go.Surface(
            x=xi, y=yi, z=zi,
            colorscale='Viridis',
            colorbar=dict(
                title=dict(text="转化效率(%)", side="right"),
                thickness=15,
                len=0.6
            ),
            opacity=0.8,
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
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
        ),
        height=700
    )
    
    return fig

# 主程序
def main():
    st.title("🚗 车辆排放三维分析系统")
    st.markdown("上传车辆10Hz排放数据Excel文件，分析CO、THC、NOx的转化效率")
    
    # 文件上传
    uploaded_file = st.file_uploader(
        "上传Excel数据文件", 
        type=["xlsx", "xls"]
    )
    
    if uploaded_file:
        try:
            # 读取Excel文件
            df = pd.read_excel(uploaded_file, header=1)
            
            # 重命名列
            df.columns = [
                '时间', 'Lambda', '催化器温度', 
                'CO原排', 'CO尾排', 
                'THC原排', 'THC尾排',
                'NOx原排', 'NOx尾排', '流量'
            ]
            
            # 处理缺失值
            df = df.fillna(0)
            
            # 数据采样
            df = df.iloc[::10, :]
            
            # 计算转化效率
            df['CO转化率'] = calculate_efficiency(df['CO原排'], df['CO尾排'])
            df['THC转化率'] = calculate_efficiency(df['THC原排'], df['THC尾排'])
            df['NOx转化率'] = calculate_efficiency(df['NOx原排'], df['NOx尾排'])
            
            # 使用选项卡展示三个图表
            tab1, tab2, tab3 = st.tabs(["CO转化率", "THC转化率", "NOx转化率"])
            
            with tab1:
                fig_co = create_3d_surface(
                    df['流量'], df['催化器温度'], df['CO转化率'], "CO"
                )
                st.plotly_chart(fig_co, use_container_width=True)
                
            with tab2:
                fig_thc = create_3d_surface(
                    df['流量'], df['催化器温度'], df['THC转化率'], "THC"
                )
                st.plotly_chart(fig_thc, use_container_width=True)
                
            with tab3:
                fig_nox = create_3d_surface(
                    df['流量'], df['催化器温度'], df['NOx转化率'], "NOx"
                )
                st.plotly_chart(fig_nox, use_container_width=True)
            
        except Exception as e:
            st.error(f"数据处理错误: {str(e)}")

if __name__ == "__main__":
    main()
