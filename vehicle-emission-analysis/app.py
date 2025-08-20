import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from functools import lru_cache

# 页面设置
st.set_page_config(
    page_title="车辆排放分析系统",
    page_icon="🚗",
    layout="wide"
)

# 添加进度指示器
progress_bar = st.progress(0)
status_text = st.empty()

def update_status(step, total_steps, message):
    """更新处理状态"""
    progress = step / total_steps
    progress_bar.progress(progress)
    status_text.text(f"🔄 {message}... ({step}/{total_steps})")

# 缓存数据处理结果
@st.cache_data(show_spinner=False)
def load_and_process_data(uploaded_file):
    """加载和处理数据（带缓存）"""
    update_status(1, 6, "读取Excel文件")
    
    # 读取Excel文件
    df = pd.read_excel(uploaded_file, header=1)
    
    update_status(2, 6, "重命名列")
    # 重命名列
    df.columns = [
        '时间', 'Lambda', '催化器温度', 
        'CO原排', 'CO尾排', 
        'THC原排', 'THC尾排',
        'NOx原排', 'NOx尾排', '流量'
    ]
    
    update_status(3, 6, "处理缺失值")
    # 处理缺失值
    df = df.fillna(0)
    
    update_status(4, 6, "数据采样")
    # 数据采样（10Hz数据量太大，降采样到0.5Hz）
    df = df.iloc[::20, :].copy()  # 每20行取1行
    
    update_status(5, 6, "计算转化效率")
    # 计算转化效率
    def safe_efficiency(upstream, downstream):
        mask = (upstream > 0) & (downstream >= 0)
        result = np.zeros_like(upstream, dtype=float)
        result[mask] = (1 - downstream[mask] / upstream[mask]) * 100
        return np.clip(result, 0, 100)
    
    df['CO转化率'] = safe_efficiency(df['CO原排'], df['CO尾排'])
    df['THC转化率'] = safe_efficiency(df['THC原排'], df['THC尾排'])
    df['NOx转化率'] = safe_efficiency(df['NOx原排'], df['NOx尾排'])
    
    update_status(6, 6, "数据处理完成")
    time.sleep(0.5)  # 让用户看到完成状态
    progress_bar.empty()
    status_text.empty()
    
    return df

# 简化的网格插值函数（优化性能）
def fast_interpolation(x, y, z, grid_size=30):
    """快速网格插值实现"""
    # 使用numpy的histogram2d进行快速网格化
    zi, x_edges, y_edges = np.histogram2d(
        x, y, weights=z, bins=[grid_size, grid_size], density=True
    )
    counts, _, _ = np.histogram2d(x, y, bins=[grid_size, grid_size])
    
    # 避免除零
    counts[counts == 0] = 1
    zi = zi / counts
    
    # 创建网格坐标
    xi = (x_edges[:-1] + x_edges[1:]) / 2
    yi = (y_edges[:-1] + y_edges[1:]) / 2
    xi, yi = np.meshgrid(xi, yi)
    
    return xi, yi, zi

# 创建三维曲面图（优化版本）
def create_optimized_3d_surface(flow, temp, efficiency, pollutant_name):
    """创建优化的三维曲面图"""
    # 限制数据点数
    max_points = 1000
    if len(flow) > max_points:
        indices = np.random.choice(len(flow), max_points, replace=False)
        flow = flow[indices]
        temp = temp[indices]
        efficiency = efficiency[indices]
    
    # 使用快速插值
    xi, yi, zi = fast_interpolation(flow, temp, efficiency, grid_size=25)
    
    # 创建3D散点图代替曲面图（性能更好）
    fig = go.Figure(data=[
        go.Scatter3d(
            x=flow,
            y=temp,
            z=efficiency,
            mode='markers',
            marker=dict(
                size=4,
                color=efficiency,
                colorscale='Viridis',
                opacity=0.7,
                colorbar=dict(title="转化效率(%)")
            ),
            name=pollutant_name
        )
    ])
    
    fig.update_layout(
        title=f"{pollutant_name}转化效率分析（散点图）",
        scene=dict(
            xaxis_title='流量 (m³/h)',
            yaxis_title='催化器温度 (°C)',
            zaxis_title='转化效率 (%)',
            zaxis=dict(range=[0, 100])
        ),
        height=600
    )
    
    return fig

# 显示数据统计信息
def show_statistics(df):
    """显示数据统计信息"""
    st.subheader("📊 数据统计信息")
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("总数据点数", len(df))
    with cols[1]:
        st.metric("CO平均转化率", f"{df['CO转化率'].mean():.1f}%")
    with cols[2]:
        st.metric("THC平均转化率", f"{df['THC转化率'].mean():.1f}%")
    with cols[3]:
        st.metric("NOx平均转化率", f"{df['NOx转化率'].mean():.1f}%")
    
    # 显示数据分布
    with st.expander("查看数据分布"):
        st.dataframe(df.describe())

# 主程序
def main():
    st.title("🚗 车辆排放三维分析系统（优化版）")
    st.info("上传车辆10Hz排放数据Excel文件，系统将自动分析三种污染物的转化效率")
    
    # 文件上传
    uploaded_file = st.file_uploader(
        "选择Excel数据文件", 
        type=["xlsx", "xls"],
        help="支持.xlsx和.xls格式，请确保文件格式正确"
    )
    
    if uploaded_file:
        try:
            # 加载和处理数据
            df = load_and_process_data(uploaded_file)
            
            # 显示数据预览
            with st.expander("📋 数据预览（前10行）", expanded=False):
                st.dataframe(df.head(10), use_container_width=True)
            
            # 显示统计信息
            show_statistics(df)
            
            # 使用选项卡展示三个图表
            st.subheader("📈 三维可视化分析")
            tab1, tab2, tab3 = st.tabs(["CO转化率", "THC转化率", "NOx转化率"])
            
            with st.spinner("生成可视化图表..."):
                with tab1:
                    fig_co = create_optimized_3d_surface(
                        df['流量'].values, 
                        df['催化器温度'].values, 
                        df['CO转化率'].values, 
                        "CO"
                    )
                    st.plotly_chart(fig_co, use_container_width=True)
                
                with tab2:
                    fig_thc = create_optimized_3d_surface(
                        df['流量'].values, 
                        df['催化器温度'].values, 
                        df['THC转化率'].values, 
                        "THC"
                    )
                    st.plotly_chart(fig_thc, use_container_width=True)
                
                with tab3:
                    fig_nox = create_optimized_3d_surface(
                        df['流量'].values, 
                        df['催化器温度'].values, 
                        df['NOx转化率'].values, 
                        "NOx"
                    )
                    st.plotly_chart(fig_nox, use_container_width=True)
            
            # 添加使用说明
            with st.expander("ℹ️ 使用说明"):
                st.markdown("""
                - **数据采样**: 10Hz数据自动降采样到0.5Hz以提高性能
                - **转化效率**: 计算公式 = (1 - 尾排/原排) × 100%
                - **颜色映射**: 蓝色→绿色→红色表示效率从低到高
                - **交互操作**: 使用鼠标拖拽旋转3D视图，滚轮缩放
                """)
                
        except Exception as e:
            st.error(f"❌ 数据处理错误: {str(e)}")
            st.exception(e)
    else:
        st.info("👆 请上传Excel文件开始分析")

if __name__ == "__main__":
    main()
