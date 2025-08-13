#!/usr/bin/env python3
"""
Advanced Oceanographic Visualizations
해양학 전용 고급 시각화 함수 모음
"""

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.gridspec import GridSpec
from matplotlib.collections import LineCollection
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy import interpolate, signal
from typing import Union, List, Dict, Tuple, Optional, Any
import warnings

warnings.filterwarnings('ignore')


def plot_ts_diagram(
    temperature: Union[np.ndarray, xr.DataArray],
    salinity: Union[np.ndarray, xr.DataArray],
    depth: Optional[Union[np.ndarray, xr.DataArray]] = None,
    density_lines: bool = True,
    colorbar_label: str = 'Depth (m)',
    title: str = 'T-S Diagram',
    figsize: Tuple[float, float] = (10, 8),
    cmap: str = 'viridis_r',
    marker_size: int = 20,
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Temperature-Salinity (T-S) Diagram 생성
    해수의 온도-염분 관계를 보여주는 해양학의 기본 다이어그램
    
    Parameters:
        temperature: 온도 데이터 (°C)
        salinity: 염분 데이터 (PSU)
        depth: 깊이 데이터 (m) - 색상 매핑용
        density_lines: 등밀도선 표시 여부
        colorbar_label: 컬러바 레이블
        title: 그래프 제목
        figsize: 그래프 크기
        cmap: 컬러맵
        marker_size: 마커 크기
        save_path: 저장 경로
        
    Returns:
        Figure와 Axes 객체
        
    Example:
        >>> fig, ax = plot_ts_diagram(temp, sal, depth, density_lines=True)
    """
    # 데이터 변환
    if isinstance(temperature, xr.DataArray):
        temperature = temperature.values.flatten()
    if isinstance(salinity, xr.DataArray):
        salinity = salinity.values.flatten()
    if depth is not None and isinstance(depth, xr.DataArray):
        depth = depth.values.flatten()
        
    # NaN 값 제거
    mask = ~(np.isnan(temperature) | np.isnan(salinity))
    temperature = temperature[mask]
    salinity = salinity[mask]
    if depth is not None:
        depth = depth[mask]
        
    # 그래프 생성
    fig, ax = plt.subplots(figsize=figsize)
    
    # 깊이에 따른 색상 매핑
    if depth is not None:
        scatter = ax.scatter(salinity, temperature, c=depth, s=marker_size,
                           cmap=cmap, alpha=0.6, edgecolors='k', linewidth=0.5)
        cbar = plt.colorbar(scatter, ax=ax, label=colorbar_label)
    else:
        ax.scatter(salinity, temperature, s=marker_size, alpha=0.6,
                  edgecolors='k', linewidth=0.5)
        
    # 등밀도선 추가
    if density_lines:
        # Simplified UNESCO 1983 equation for density anomaly
        sal_grid = np.linspace(salinity.min(), salinity.max(), 100)
        temp_grid = np.linspace(temperature.min(), temperature.max(), 100)
        sal_mesh, temp_mesh = np.meshgrid(sal_grid, temp_grid)
        
        # 간단한 밀도 계산 (sigma-t)
        density = calculate_density_simple(temp_mesh, sal_mesh)
        
        # 등밀도선 그리기
        cs = ax.contour(sal_mesh, temp_mesh, density, levels=15,
                       colors='gray', alpha=0.4, linewidths=0.8)
        ax.clabel(cs, inline=True, fontsize=8, fmt='%.1f')
        
    # 레이블 및 제목
    ax.set_xlabel('Salinity (PSU)', fontsize=12)
    ax.set_ylabel('Temperature (°C)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 축 범위 조정
    ax.set_xlim(salinity.min() - 0.1, salinity.max() + 0.1)
    ax.set_ylim(temperature.min() - 0.5, temperature.max() + 0.5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"T-S Diagram 저장: {save_path}")
        
    return fig, ax


def plot_hovmoller(
    data: Union[xr.DataArray, xr.Dataset],
    x_dim: str = 'time',
    y_dim: str = 'depth',
    variable: Optional[str] = None,
    title: str = 'Hovmöller Diagram',
    cmap: str = 'RdBu_r',
    figsize: Tuple[float, float] = (14, 8),
    contour_levels: Optional[int] = None,
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Hovmöller Diagram 생성
    시간-공간 또는 시간-깊이 변화를 보여주는 2D 다이어그램
    
    Parameters:
        data: xarray DataArray 또는 Dataset
        x_dim: x축 차원 (보통 'time')
        y_dim: y축 차원 (보통 'depth' 또는 'latitude')
        variable: Dataset인 경우 변수명
        title: 그래프 제목
        cmap: 컬러맵
        figsize: 그래프 크기
        contour_levels: 등고선 레벨 수
        save_path: 저장 경로
        
    Returns:
        Figure와 Axes 객체
        
    Example:
        >>> fig, ax = plot_hovmoller(ds['temperature'], x_dim='time', y_dim='depth')
    """
    # 데이터 준비
    if isinstance(data, xr.Dataset):
        if variable is None:
            variable = list(data.data_vars)[0]
            print(f"변수 자동 선택: {variable}")
        plot_data = data[variable]
    else:
        plot_data = data
        
    # 2D로 변환
    if len(plot_data.dims) > 2:
        # 다른 차원들의 평균
        other_dims = [d for d in plot_data.dims if d not in [x_dim, y_dim]]
        plot_data = plot_data.mean(dim=other_dims)
        
    # 시간 축이 x축인 경우 포맷 조정
    if x_dim == 'time' or 'time' in x_dim.lower():
        plot_data = plot_data.transpose(y_dim, x_dim)
        
    # 그래프 생성
    fig, ax = plt.subplots(figsize=figsize)
    
    # Pcolormesh 플롯
    im = ax.pcolormesh(plot_data[x_dim], plot_data[y_dim], plot_data,
                      cmap=cmap, shading='auto')
    
    # 등고선 추가
    if contour_levels:
        cs = ax.contour(plot_data[x_dim], plot_data[y_dim], plot_data,
                       levels=contour_levels, colors='k', alpha=0.3, linewidths=0.5)
        ax.clabel(cs, inline=True, fontsize=8)
        
    # 컬러바
    cbar = plt.colorbar(im, ax=ax, label=plot_data.attrs.get('units', 'Values'))
    
    # 레이블 및 제목
    ax.set_xlabel(x_dim.capitalize(), fontsize=12)
    ax.set_ylabel(y_dim.capitalize(), fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # y축 반전 (깊이의 경우)
    if 'depth' in y_dim.lower():
        ax.invert_yaxis()
        
    # x축이 시간인 경우 포맷 조정
    if x_dim == 'time' or 'time' in x_dim.lower():
        import matplotlib.dates as mdates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Hovmöller Diagram 저장: {save_path}")
        
    return fig, ax


def plot_vertical_profile(
    data: Union[xr.DataArray, np.ndarray],
    depth: Union[xr.DataArray, np.ndarray],
    variables: Optional[List[str]] = None,
    title: str = 'Vertical Profile',
    figsize: Tuple[float, float] = (8, 10),
    colors: Optional[List[str]] = None,
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    수직 프로파일 플롯
    깊이에 따른 해양 변수의 변화를 표시
    
    Parameters:
        data: 프로파일 데이터
        depth: 깊이 데이터
        variables: 변수명 리스트 (다중 프로파일용)
        title: 그래프 제목
        figsize: 그래프 크기
        colors: 색상 리스트
        save_path: 저장 경로
        
    Returns:
        Figure와 Axes 객체
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # 데이터 변환
    if isinstance(data, xr.DataArray):
        data_values = data.values
    else:
        data_values = data
        
    if isinstance(depth, xr.DataArray):
        depth_values = depth.values
    else:
        depth_values = depth
        
    # 다중 프로파일 처리
    if data_values.ndim > 1:
        if colors is None:
            colors = plt.cm.tab10(np.linspace(0, 1, data_values.shape[1]))
            
        for i in range(data_values.shape[1]):
            label = variables[i] if variables else f'Profile {i+1}'
            ax.plot(data_values[:, i], depth_values, label=label,
                   color=colors[i], linewidth=2)
        ax.legend()
    else:
        ax.plot(data_values, depth_values, linewidth=2, color='b')
        
    # 깊이 축 반전 (해수면이 위)
    ax.invert_yaxis()
    
    # 그리드와 레이블
    ax.grid(True, alpha=0.3)
    ax.set_ylabel('Depth (m)', fontsize=12)
    ax.set_xlabel('Value', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Vertical Profile 저장: {save_path}")
        
    return fig, ax


def plot_ocean_section(
    data: xr.DataArray,
    x_coord: str = 'longitude',
    y_coord: str = 'depth',
    title: str = 'Ocean Section',
    cmap: str = 'RdBu_r',
    figsize: Tuple[float, float] = (14, 8),
    bathymetry: Optional[np.ndarray] = None,
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    해양 단면도 플롯
    경도/위도-깊이 단면의 해양 변수 분포 표시
    
    Parameters:
        data: 단면 데이터
        x_coord: x축 좌표 (longitude 또는 latitude)
        y_coord: y축 좌표 (보통 depth)
        title: 그래프 제목
        cmap: 컬러맵
        figsize: 그래프 크기
        bathymetry: 해저 지형 데이터
        save_path: 저장 경로
        
    Returns:
        Figure와 Axes 객체
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # 데이터 플롯
    im = ax.pcolormesh(data[x_coord], data[y_coord], data,
                      cmap=cmap, shading='auto')
    
    # 해저 지형 추가
    if bathymetry is not None:
        ax.fill_between(data[x_coord], bathymetry, data[y_coord].max(),
                       color='gray', alpha=0.5)
        
    # 컬러바
    cbar = plt.colorbar(im, ax=ax, label=data.attrs.get('units', 'Values'))
    
    # 깊이 축 반전
    if 'depth' in y_coord.lower():
        ax.invert_yaxis()
        
    # 레이블과 제목
    ax.set_xlabel(x_coord.capitalize(), fontsize=12)
    ax.set_ylabel(y_coord.capitalize(), fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Ocean Section 저장: {save_path}")
        
    return fig, ax


def plot_vector_field(
    u: xr.DataArray,
    v: xr.DataArray,
    magnitude: Optional[xr.DataArray] = None,
    x_coord: str = 'longitude',
    y_coord: str = 'latitude',
    title: str = 'Ocean Currents',
    figsize: Tuple[float, float] = (12, 10),
    arrow_scale: int = 10,
    arrow_density: int = 5,
    cmap: str = 'viridis',
    projection: Optional[ccrs.Projection] = None,
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    해류 벡터장 시각화
    
    Parameters:
        u: 동서 방향 속도 성분
        v: 남북 방향 속도 성분
        magnitude: 속도 크기 (배경색용)
        x_coord: x 좌표명
        y_coord: y 좌표명
        title: 그래프 제목
        figsize: 그래프 크기
        arrow_scale: 화살표 스케일
        arrow_density: 화살표 밀도 (n번째마다 표시)
        cmap: 컬러맵
        projection: 지도 투영법
        save_path: 저장 경로
        
    Returns:
        Figure와 Axes 객체
    """
    if projection is None:
        projection = ccrs.PlateCarree()
        
    fig = plt.figure(figsize=figsize)
    ax = plt.axes(projection=projection)
    
    # 해안선 추가
    ax.add_feature(cfeature.LAND, color='lightgray')
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.gridlines(draw_labels=True, alpha=0.3)
    
    # 속도 크기 계산
    if magnitude is None:
        magnitude = np.sqrt(u**2 + v**2)
        
    # 배경 컬러맵
    im = ax.pcolormesh(u[x_coord], u[y_coord], magnitude,
                      transform=ccrs.PlateCarree(),
                      cmap=cmap, shading='auto', alpha=0.7)
    
    # 벡터 화살표
    skip = (slice(None, None, arrow_density), slice(None, None, arrow_density))
    ax.quiver(u[x_coord][skip[1]], u[y_coord][skip[0]],
             u.values[skip], v.values[skip],
             transform=ccrs.PlateCarree(),
             scale=arrow_scale, scale_units='inches',
             color='black', alpha=0.6)
    
    # 컬러바
    cbar = plt.colorbar(im, ax=ax, label='Current Speed (m/s)',
                       orientation='horizontal', pad=0.05)
    
    # 제목
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Vector Field 저장: {save_path}")
        
    return fig, ax


def plot_mixed_layer_evolution(
    mld_data: xr.DataArray,
    time_dim: str = 'time',
    lat_dim: str = 'latitude',
    lon_dim: str = 'longitude',
    location: Optional[Tuple[float, float]] = None,
    title: str = 'Mixed Layer Depth Evolution',
    figsize: Tuple[float, float] = (14, 6),
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    혼합층 깊이의 시간 변화 플롯
    
    Parameters:
        mld_data: 혼합층 깊이 데이터
        time_dim: 시간 차원명
        lat_dim: 위도 차원명
        lon_dim: 경도 차원명
        location: 특정 위치 (lat, lon) 튜플
        title: 그래프 제목
        figsize: 그래프 크기
        save_path: 저장 경로
        
    Returns:
        Figure와 Axes 객체
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[2, 1])
    
    # 특정 위치 또는 평균
    if location:
        lat, lon = location
        mld_series = mld_data.sel({lat_dim: lat, lon_dim: lon}, method='nearest')
        subtitle = f' at ({lat:.1f}°, {lon:.1f}°)'
    else:
        mld_series = mld_data.mean(dim=[lat_dim, lon_dim])
        subtitle = ' (Spatial Average)'
        
    # 시계열 플롯
    time = mld_series[time_dim]
    ax1.plot(time, mld_series, 'b-', linewidth=2, label='MLD')
    ax1.fill_between(time, 0, mld_series, alpha=0.3)
    
    # 계절 평균 추가
    if hasattr(mld_series, 'groupby'):
        seasonal = mld_series.groupby(f'{time_dim}.season').mean()
        ax2.bar(range(4), seasonal.values, tick_label=['DJF', 'MAM', 'JJA', 'SON'])
        ax2.set_ylabel('MLD (m)')
        ax2.set_title('Seasonal Average')
        ax2.grid(True, alpha=0.3)
        
    # 주 플롯 설정
    ax1.set_ylabel('Mixed Layer Depth (m)', fontsize=12)
    ax1.set_title(title + subtitle, fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.invert_yaxis()  # 깊이는 아래로
    
    # x축 포맷
    import matplotlib.dates as mdates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"MLD Evolution 저장: {save_path}")
        
    return fig, (ax1, ax2)


def plot_water_mass_analysis(
    temperature: xr.DataArray,
    salinity: xr.DataArray,
    depth: xr.DataArray,
    water_mass_definitions: Dict[str, Dict[str, Tuple[float, float]]],
    title: str = 'Water Mass Analysis',
    figsize: Tuple[float, float] = (14, 10),
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    수괴 분석 다이어그램
    T-S 다이어그램에 수괴 경계 표시
    
    Parameters:
        temperature: 온도 데이터
        salinity: 염분 데이터
        depth: 깊이 데이터
        water_mass_definitions: 수괴 정의 딕셔너리
            예: {'NPIW': {'T': (2, 7), 'S': (33.8, 34.2)}}
        title: 그래프 제목
        figsize: 그래프 크기
        save_path: 저장 경로
        
    Returns:
        Figure와 Axes 객체
    """
    fig = plt.figure(figsize=figsize)
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)
    
    # T-S 다이어그램
    ax1 = fig.add_subplot(gs[0, :])
    scatter = ax1.scatter(salinity.values.flatten(), 
                         temperature.values.flatten(),
                         c=depth.values.flatten(), 
                         s=10, cmap='viridis_r', alpha=0.5)
    
    # 수괴 경계 표시
    colors = plt.cm.Set1(np.linspace(0, 1, len(water_mass_definitions)))
    for i, (name, bounds) in enumerate(water_mass_definitions.items()):
        t_min, t_max = bounds['T']
        s_min, s_max = bounds['S']
        
        # 사각형 그리기
        from matplotlib.patches import Rectangle
        rect = Rectangle((s_min, t_min), s_max-s_min, t_max-t_min,
                        fill=False, edgecolor=colors[i], linewidth=2,
                        linestyle='--', label=name)
        ax1.add_patch(rect)
        
    ax1.set_xlabel('Salinity (PSU)', fontsize=12)
    ax1.set_ylabel('Temperature (°C)', fontsize=12)
    ax1.set_title('T-S Diagram with Water Masses', fontsize=14)
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    cbar = plt.colorbar(scatter, ax=ax1, label='Depth (m)')
    
    # 온도 프로파일
    ax2 = fig.add_subplot(gs[1, 0])
    mean_temp = temperature.mean(dim=['longitude', 'latitude'])
    ax2.plot(mean_temp, depth, 'r-', linewidth=2)
    ax2.set_xlabel('Temperature (°C)')
    ax2.set_ylabel('Depth (m)')
    ax2.set_title('Mean Temperature Profile')
    ax2.invert_yaxis()
    ax2.grid(True, alpha=0.3)
    
    # 염분 프로파일
    ax3 = fig.add_subplot(gs[1, 1])
    mean_sal = salinity.mean(dim=['longitude', 'latitude'])
    ax3.plot(mean_sal, depth, 'b-', linewidth=2)
    ax3.set_xlabel('Salinity (PSU)')
    ax3.set_ylabel('Depth (m)')
    ax3.set_title('Mean Salinity Profile')
    ax3.invert_yaxis()
    ax3.grid(True, alpha=0.3)
    
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Water Mass Analysis 저장: {save_path}")
        
    return fig, [ax1, ax2, ax3]


def calculate_density_simple(temperature: np.ndarray, salinity: np.ndarray) -> np.ndarray:
    """
    간단한 해수 밀도 계산 (sigma-t)
    UNESCO 1983 간소화 버전
    
    Parameters:
        temperature: 온도 (°C)
        salinity: 염분 (PSU)
        
    Returns:
        밀도 anomaly (sigma-t, kg/m³)
    """
    # 간단한 선형 근사
    rho0 = 1000.0  # 기준 밀도
    alpha = 0.2  # 열팽창 계수 근사
    beta = 0.78  # 염분 수축 계수 근사
    
    sigma_t = -alpha * temperature + beta * salinity
    return sigma_t


def plot_seasonal_climatology(
    data: xr.DataArray,
    variable_name: str = 'Variable',
    title: str = 'Seasonal Climatology',
    figsize: Tuple[float, float] = (16, 10),
    cmap: str = 'RdBu_r',
    projection: Optional[ccrs.Projection] = None,
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, List[plt.Axes]]:
    """
    계절별 기후값 지도
    
    Parameters:
        data: 시계열 데이터
        variable_name: 변수명
        title: 그래프 제목
        figsize: 그래프 크기
        cmap: 컬러맵
        projection: 지도 투영법
        save_path: 저장 경로
        
    Returns:
        Figure와 Axes 리스트
    """
    if projection is None:
        projection = ccrs.PlateCarree()
        
    # 계절별 평균 계산
    seasonal_data = data.groupby('time.season').mean()
    seasons = ['DJF', 'MAM', 'JJA', 'SON']
    
    fig, axes = plt.subplots(2, 2, figsize=figsize,
                            subplot_kw={'projection': projection})
    axes = axes.flatten()
    
    # 전체 데이터 범위로 컬러바 범위 설정
    vmin = seasonal_data.min().values
    vmax = seasonal_data.max().values
    
    for i, season in enumerate(seasons):
        ax = axes[i]
        
        # 해안선 추가
        ax.add_feature(cfeature.LAND, color='lightgray')
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.gridlines(draw_labels=True, alpha=0.3)
        
        # 데이터 플롯
        season_data = seasonal_data.sel(season=season)
        im = ax.pcolormesh(season_data.longitude, season_data.latitude,
                          season_data, transform=ccrs.PlateCarree(),
                          cmap=cmap, vmin=vmin, vmax=vmax, shading='auto')
        
        ax.set_title(f'{season}', fontsize=12, fontweight='bold')
        
    # 공통 컬러바
    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(im, cax=cbar_ax, label=variable_name)
    
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Seasonal Climatology 저장: {save_path}")
        
    return fig, axes


# 유틸리티 함수들
def create_animation_frames(
    data: xr.DataArray,
    time_dim: str = 'time',
    output_dir: str = 'animation_frames',
    title_template: str = 'Frame {frame}',
    cmap: str = 'RdBu_r',
    **kwargs
) -> List[str]:
    """
    애니메이션용 프레임 생성
    
    Parameters:
        data: 시계열 데이터
        time_dim: 시간 차원명
        output_dir: 프레임 저장 디렉토리
        title_template: 제목 템플릿
        cmap: 컬러맵
        **kwargs: 추가 플롯 옵션
        
    Returns:
        생성된 프레임 파일 경로 리스트
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    frame_paths = []
    times = data[time_dim].values
    
    # 전체 데이터 범위로 컬러바 범위 고정
    vmin = data.min().values
    vmax = data.max().values
    
    for i, t in enumerate(times):
        fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 8)))
        
        frame_data = data.sel({time_dim: t})
        im = ax.pcolormesh(frame_data.longitude, frame_data.latitude,
                          frame_data, cmap=cmap, vmin=vmin, vmax=vmax,
                          shading='auto')
        
        plt.colorbar(im, ax=ax)
        ax.set_title(title_template.format(frame=i, time=t))
        
        frame_path = os.path.join(output_dir, f'frame_{i:04d}.png')
        plt.savefig(frame_path, dpi=100)
        plt.close()
        
        frame_paths.append(frame_path)
        
    print(f"{len(frame_paths)}개 프레임 생성 완료: {output_dir}")
    return frame_paths


if __name__ == "__main__":
    # 테스트 코드
    print("Advanced Oceanographic Visualization Module Loaded")
    print("Available functions:")
    print("- plot_ts_diagram: T-S Diagram")
    print("- plot_hovmoller: Hovmöller Diagram")
    print("- plot_vertical_profile: Vertical Profile")
    print("- plot_ocean_section: Ocean Section")
    print("- plot_vector_field: Ocean Currents")
    print("- plot_mixed_layer_evolution: MLD Evolution")
    print("- plot_water_mass_analysis: Water Mass Analysis")
    print("- plot_seasonal_climatology: Seasonal Maps")
    print("- create_animation_frames: Animation Helper")