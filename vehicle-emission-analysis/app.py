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
    efficiency = max(0, min(1, efficiency))  # 确保在0-1范围内
    
    if efficiency <= 0.5:
        # 0-50%: 深蓝到绿色
        r = 0
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
        method='linear',  # 使用线性插值更稳定
        fill_value=0      # 缺失值填充为0
    )
    
    # 创建3D曲面
    fig = go.Figure(data=[
        go.Surface(
            x=xi, y=yi, z=zi,
            colorscale='Viridis',  # 使用内置颜色尺度
            colorbar=dict(
                title=dict(
                    text="转化效率(%)",
                    side="right"
                ),
                thickness=15,
                len=0.6
            ),
            opacity=0.8,
            hoverinfo="x+y+z+text",
            hovertext=[f"流量: {x:.2f}<br>温度: {y:.2f}<br>效率: {z:.2f}%" 
                      for x, y, z in zip(xi.flatten(), yi.flatten(), zi.flatten())],
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
        height=700,
        margin=dict(l=0, r=0, b=0, t=50)
    )
    
    return fig

# 数据预处理函数
def preprocess_data(df):
    """预处理数据，处理缺失值和异常值"""
    # 重命名列（根据描述的顺序）
    df.columns = [
        '时间', 'Lambda', '催化器温度', 
        'CO原排', 'CO尾排', 
        'THC原排', 'THC尾排',
        'NOx原排', 'NOx尾排', '流量'
    ]
    
    # 处理缺失值
    df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
    
    # 处理异常值（负值设为0）
    for col in ['CO原排', 'CO尾排', 'THC原排', 'THC尾排', 'NOx原排', 'NOx尾排']:
        df[col] = df[col].clip(lower=0)
    
    return df

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
            
            # 数据预处理
            df = preprocess_data(df)
            
            # 数据采样（10Hz数据量太大，降采样到1Hz）
            df = df.iloc[::10, :].reset_index(drop=True)
            
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
                st.subheader("CO转化效率分析")
                fig_co = create_3d_surface(
                    df['流量'], 
                    df['催化器温度'], 
                    df['CO转化率'],
                    "CO"
                )
                st.plotly_chart(fig_co, use_container_width=True)
                
                # 显示统计信息
                col1, col2, col3 = st.columns(3)
                col1.metric("平均转化率", f"{df['CO转化率'].mean():.1f}%")
                col2.metric("最大转化率", f"{df['CO转化率'].max():.1f}%")
                col3.metric("最小转化率", f"{df['CO转化率'].min():.1f}%")
                
            with tab2:
                st.subheader("THC转化效率分析")
                fig_thc = create_3d_surface(
                    df['流量'], 
                    df['催化器温度'], 
                    df['THC转化率'],
                    "THC"
                )
                st.plotly_chart(fig_thc, use_container_width=True)
                
                # 显示统计信息
                col1, col2, col3 = st.columns(3)
                col1.metric("平均转化率", f"{df['THC转化率'].mean():.1f}%")
                col2.metric("最大转化率", f"{df['THC转化率'].max():.1f}%")
                col3.metric("最小转化率", f"{df['THC转化率'].min():.1f}%")
                
            with tab3:
                st.subheader("NOx转化效率分析")
                fig_nox = create_3d_surface(
                    df['流量'], 
                    df['催化器温度'], 
                    df['NOx转化率'],
                    "NOx"
                )
                st.plotly_chart(fig_nox, use_container_width=True)
                
                # 显示统计信息
                col1, col2, col3 = st.columns(3)
                col1.metric("平均转化率", f"{df['NOx转化率'].mean():.1f}%")
                col2.metric("最大转化率", f"{df['NOx转化率'].max():.1f}%")
                col3.metric("最小转化率", f"{df['NOx转化率'].min():.1f}%")
            
            # 添加数据下载功能
            st.subheader("数据导出")
            csv = df.to_csv(index=False)
            st.download_button(
                label="下载处理后的CSV数据",
                data=csv,
                file_name="排放分析结果.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"数据处理错误: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
