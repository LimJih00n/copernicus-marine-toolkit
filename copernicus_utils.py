#!/usr/bin/env python3
"""
Copernicus Marine Data Utilities
코페르니쿠스 해양 데이터 분석을 위한 재사용 가능한 함수 모음
"""

import os
import warnings
from typing import Union, List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import json

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy import stats, signal
import netCDF4 as nc4

warnings.filterwarnings('ignore')


def load_dataset(
    filepath: str,
    engine: str = 'netcdf4',
    decode_times: bool = True,
    chunks: Optional[Dict] = None
) -> xr.Dataset:
    """
    NetCDF 데이터셋 로딩
    
    Parameters:
        filepath: NetCDF 파일 경로
        engine: xarray 엔진 ('netcdf4', 'h5netcdf', 'scipy')
        decode_times: 시간 디코딩 여부
        chunks: Dask 청킹 설정 (대용량 데이터용)
        
    Returns:
        xarray Dataset 객체
        
    Example:
        >>> ds = load_dataset('data.nc')
        >>> ds = load_dataset('large_data.nc', chunks={'time': 100, 'lat': 50, 'lon': 50})
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")
        
    try:
        ds = xr.open_dataset(
            filepath,
            engine=engine,
            decode_times=decode_times,
            chunks=chunks
        )
        
        # 기본 정보 출력
        print(f"데이터셋 로드 완료: {filepath}")
        print(f"차원: {list(ds.dims.keys())}")
        print(f"변수: {list(ds.data_vars.keys())}")
        print(f"시간 범위: {ds.time.min().values} ~ {ds.time.max().values}" if 'time' in ds else "")
        
        return ds
        
    except Exception as e:
        raise RuntimeError(f"데이터셋 로딩 실패: {str(e)}")


def subset_region(
    ds: xr.Dataset,
    lon_range: Tuple[float, float],
    lat_range: Tuple[float, float],
    lon_dim: str = 'longitude',
    lat_dim: str = 'latitude'
) -> xr.Dataset:
    """
    지역별 데이터 추출
    
    Parameters:
        ds: xarray Dataset
        lon_range: 경도 범위 (min, max)
        lat_range: 위도 범위 (min, max)
        lon_dim: 경도 차원 이름
        lat_dim: 위도 차원 이름
        
    Returns:
        지역이 추출된 Dataset
        
    Example:
        >>> ds_subset = subset_region(ds, (120, 135), (30, 45))  # 동해 지역
    """
    # 차원 이름 확인 및 자동 매칭
    possible_lon = ['longitude', 'lon', 'x']
    possible_lat = ['latitude', 'lat', 'y']
    
    for dim in possible_lon:
        if dim in ds.dims:
            lon_dim = dim
            break
            
    for dim in possible_lat:
        if dim in ds.dims:
            lat_dim = dim
            break
    
    # 경도가 0-360 범위인 경우 처리
    if ds[lon_dim].max() > 180:
        lon_range = tuple(lon if lon >= 0 else lon + 360 for lon in lon_range)
    
    # 지역 추출
    ds_subset = ds.sel(
        {
            lon_dim: slice(lon_range[0], lon_range[1]),
            lat_dim: slice(lat_range[0], lat_range[1])
        }
    )
    
    print(f"지역 추출 완료: 경도 {lon_range}, 위도 {lat_range}")
    print(f"추출된 크기: {dict(ds_subset.dims)}")
    
    return ds_subset


def subset_time(
    ds: xr.Dataset,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    time_dim: str = 'time'
) -> xr.Dataset:
    """
    시간대별 데이터 추출
    
    Parameters:
        ds: xarray Dataset
        start_date: 시작 날짜
        end_date: 종료 날짜
        time_dim: 시간 차원 이름
        
    Returns:
        시간이 추출된 Dataset
        
    Example:
        >>> ds_subset = subset_time(ds, '2020-01-01', '2020-12-31')
    """
    # 문자열을 datetime으로 변환
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    # 시간 차원 확인
    if time_dim not in ds.dims:
        for dim in ['time', 't', 'date']:
            if dim in ds.dims:
                time_dim = dim
                break
        else:
            raise ValueError(f"시간 차원을 찾을 수 없습니다. 사용 가능한 차원: {list(ds.dims.keys())}")
    
    # 시간 추출
    ds_subset = ds.sel({time_dim: slice(start_date, end_date)})
    
    print(f"시간 추출 완료: {start_date} ~ {end_date}")
    print(f"추출된 시간 스텝: {len(ds_subset[time_dim])}")
    
    return ds_subset


def calculate_spatial_mean(
    ds: xr.Dataset,
    var_name: str,
    weighted: bool = True,
    lat_dim: str = 'latitude'
) -> xr.DataArray:
    """
    공간 평균 계산 (위도 가중치 옵션)
    
    Parameters:
        ds: xarray Dataset
        var_name: 변수 이름
        weighted: 위도 가중치 적용 여부
        lat_dim: 위도 차원 이름
        
    Returns:
        공간 평균된 DataArray
        
    Example:
        >>> sst_mean = calculate_spatial_mean(ds, 'sst', weighted=True)
    """
    if var_name not in ds.data_vars:
        raise ValueError(f"변수 '{var_name}'를 찾을 수 없습니다. 사용 가능한 변수: {list(ds.data_vars.keys())}")
    
    data = ds[var_name]
    
    if weighted:
        # 위도 가중치 계산
        weights = np.cos(np.deg2rad(ds[lat_dim]))
        weights = weights / weights.sum()
        
        # 가중 평균 계산
        weighted_data = data.weighted(weights)
        mean_data = weighted_data.mean(dim=[lat_dim, 'longitude'], skipna=True)
    else:
        # 단순 평균
        mean_data = data.mean(dim=['latitude', 'longitude'], skipna=True)
    
    print(f"공간 평균 계산 완료: {var_name}")
    
    return mean_data


def create_timeseries(
    ds: xr.Dataset,
    var_name: str,
    lon_point: Optional[float] = None,
    lat_point: Optional[float] = None,
    spatial_mean: bool = False
) -> pd.Series:
    """
    시계열 데이터 생성
    
    Parameters:
        ds: xarray Dataset
        var_name: 변수 이름
        lon_point: 특정 경도 (None이면 공간 평균)
        lat_point: 특정 위도 (None이면 공간 평균)
        spatial_mean: 공간 평균 계산 여부
        
    Returns:
        시계열 pandas Series
        
    Example:
        >>> ts = create_timeseries(ds, 'sst', spatial_mean=True)
        >>> ts_point = create_timeseries(ds, 'sst', lon_point=130, lat_point=38)
    """
    if var_name not in ds.data_vars:
        raise ValueError(f"변수 '{var_name}'를 찾을 수 없습니다.")
    
    if spatial_mean or (lon_point is None and lat_point is None):
        # 공간 평균 시계열
        data = calculate_spatial_mean(ds, var_name)
        ts = data.to_pandas()
    else:
        # 특정 지점 시계열
        data = ds[var_name].sel(
            longitude=lon_point,
            latitude=lat_point,
            method='nearest'
        )
        ts = data.to_pandas()
    
    # Series로 변환
    if isinstance(ts, pd.DataFrame):
        ts = ts.squeeze()
    
    ts.name = var_name
    print(f"시계열 생성 완료: {len(ts)} 시간 스텝")
    
    return ts


def plot_map(
    ds: xr.Dataset,
    var_name: str,
    time_idx: Union[int, str, datetime] = 0,
    figsize: Tuple[int, int] = (12, 8),
    cmap: str = 'viridis',
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    title: Optional[str] = None,
    projection: ccrs.Projection = ccrs.PlateCarree(),
    add_coastlines: bool = True,
    add_gridlines: bool = True,
    save_path: Optional[str] = None
) -> Tuple[Figure, Axes]:
    """
    지도 시각화
    
    Parameters:
        ds: xarray Dataset
        var_name: 변수 이름
        time_idx: 시간 인덱스 또는 날짜
        figsize: 그림 크기
        cmap: 컬러맵
        vmin, vmax: 컬러바 범위
        title: 그림 제목
        projection: 지도 투영법
        add_coastlines: 해안선 추가 여부
        add_gridlines: 격자선 추가 여부
        save_path: 저장 경로
        
    Returns:
        Figure, Axes 객체
        
    Example:
        >>> fig, ax = plot_map(ds, 'sst', time_idx='2020-01-01')
    """
    # 데이터 선택
    if 'time' in ds.dims:
        if isinstance(time_idx, (int, np.integer)):
            data = ds[var_name].isel(time=time_idx)
            time_str = str(ds.time.isel(time=time_idx).values)
        else:
            data = ds[var_name].sel(time=time_idx, method='nearest')
            time_str = str(time_idx)
    else:
        data = ds[var_name]
        time_str = ""
    
    # 그림 생성
    fig = plt.figure(figsize=figsize)
    ax = plt.axes(projection=projection)
    
    # 데이터 플롯
    lon = ds.longitude.values
    lat = ds.latitude.values
    
    im = ax.pcolormesh(
        lon, lat, data,
        transform=ccrs.PlateCarree(),
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        shading='auto'
    )
    
    # 해안선 추가
    if add_coastlines:
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.LAND, alpha=0.3)
        ax.add_feature(cfeature.OCEAN, alpha=0.1)
    
    # 격자선 추가
    if add_gridlines:
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
        gl.top_labels = False
        gl.right_labels = False
    
    # 컬러바
    cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.05, shrink=0.8)
    cbar.set_label(var_name, fontsize=10)
    
    # 제목
    if title:
        ax.set_title(title, fontsize=14)
    else:
        ax.set_title(f"{var_name} - {time_str}", fontsize=14)
    
    # 저장
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"그림 저장: {save_path}")
    
    return fig, ax


def plot_timeseries(
    ts_data: Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]],
    figsize: Tuple[int, int] = (12, 6),
    title: Optional[str] = None,
    ylabel: Optional[str] = None,
    xlabel: str = 'Time',
    grid: bool = True,
    legend: bool = True,
    save_path: Optional[str] = None
) -> Tuple[Figure, Axes]:
    """
    시계열 그래프
    
    Parameters:
        ts_data: 시계열 데이터 (Series, DataFrame, 또는 Dict)
        figsize: 그림 크기
        title: 그림 제목
        ylabel: y축 레이블
        xlabel: x축 레이블
        grid: 격자 표시 여부
        legend: 범례 표시 여부
        save_path: 저장 경로
        
    Returns:
        Figure, Axes 객체
        
    Example:
        >>> fig, ax = plot_timeseries(ts, title='SST Time Series')
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # 데이터 타입에 따라 처리
    if isinstance(ts_data, pd.Series):
        ax.plot(ts_data.index, ts_data.values, label=ts_data.name or 'Data')
    elif isinstance(ts_data, pd.DataFrame):
        for col in ts_data.columns:
            ax.plot(ts_data.index, ts_data[col], label=col)
    elif isinstance(ts_data, dict):
        for name, ts in ts_data.items():
            ax.plot(ts.index, ts.values, label=name)
    
    # 포맷팅
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel or 'Value', fontsize=12)
    
    if title:
        ax.set_title(title, fontsize=14)
    
    if grid:
        ax.grid(True, alpha=0.3)
    
    if legend:
        ax.legend(loc='best')
    
    # x축 날짜 포맷
    if isinstance(ts_data, pd.Series):
        if isinstance(ts_data.index, pd.DatetimeIndex):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # 저장
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"그림 저장: {save_path}")
    
    return fig, ax


def export_to_csv(
    data: Union[xr.Dataset, xr.DataArray, pd.DataFrame, pd.Series],
    filepath: str,
    var_names: Optional[List[str]] = None
) -> None:
    """
    CSV 파일로 내보내기
    
    Parameters:
        data: 내보낼 데이터
        filepath: 저장 경로
        var_names: Dataset인 경우 내보낼 변수 이름 리스트
        
    Example:
        >>> export_to_csv(ds, 'output.csv', var_names=['sst', 'salinity'])
    """
    # 데이터 타입에 따라 처리
    if isinstance(data, xr.Dataset):
        if var_names:
            df = data[var_names].to_dataframe()
        else:
            df = data.to_dataframe()
    elif isinstance(data, xr.DataArray):
        df = data.to_dataframe(name=data.name or 'data')
    elif isinstance(data, (pd.DataFrame, pd.Series)):
        df = data
    else:
        raise TypeError(f"지원하지 않는 데이터 타입: {type(data)}")
    
    # CSV 저장
    df.to_csv(filepath)
    print(f"CSV 파일 저장: {filepath}")


def calculate_anomaly(
    ds: xr.Dataset,
    var_name: str,
    reference_period: Optional[Tuple[str, str]] = None,
    method: str = 'subtract'
) -> xr.DataArray:
    """
    이상치(anomaly) 계산
    
    Parameters:
        ds: xarray Dataset
        var_name: 변수 이름
        reference_period: 기준 기간 (None이면 전체 기간)
        method: 계산 방법 ('subtract' 또는 'percentage')
        
    Returns:
        이상치 DataArray
        
    Example:
        >>> anomaly = calculate_anomaly(ds, 'sst', reference_period=('2000-01-01', '2010-12-31'))
    """
    data = ds[var_name]
    
    # 기준 기간 설정
    if reference_period:
        ref_data = subset_time(ds, reference_period[0], reference_period[1])[var_name]
    else:
        ref_data = data
    
    # 월별 평균 계산 (계절성 제거)
    if 'time' in ref_data.dims:
        climatology = ref_data.groupby('time.month').mean('time')
        
        # 이상치 계산
        if method == 'subtract':
            anomaly = data.groupby('time.month') - climatology
        elif method == 'percentage':
            anomaly = ((data.groupby('time.month') - climatology) / climatology) * 100
        else:
            raise ValueError(f"알 수 없는 방법: {method}")
    else:
        # 시간 차원이 없는 경우
        mean_val = ref_data.mean()
        if method == 'subtract':
            anomaly = data - mean_val
        else:
            anomaly = ((data - mean_val) / mean_val) * 100
    
    anomaly.name = f"{var_name}_anomaly"
    print(f"이상치 계산 완료: {var_name}")
    
    return anomaly


def apply_moving_average(
    data: Union[pd.Series, xr.DataArray],
    window: int,
    center: bool = True,
    min_periods: Optional[int] = None
) -> Union[pd.Series, xr.DataArray]:
    """
    이동평균 적용
    
    Parameters:
        data: 입력 데이터
        window: 윈도우 크기
        center: 중앙 정렬 여부
        min_periods: 최소 데이터 개수
        
    Returns:
        이동평균이 적용된 데이터
        
    Example:
        >>> smoothed = apply_moving_average(ts, window=12)
    """
    if isinstance(data, pd.Series):
        smoothed = data.rolling(
            window=window,
            center=center,
            min_periods=min_periods or 1
        ).mean()
    elif isinstance(data, xr.DataArray):
        if 'time' in data.dims:
            smoothed = data.rolling(
                time=window,
                center=center,
                min_periods=min_periods or 1
            ).mean()
        else:
            raise ValueError("시간 차원이 필요합니다.")
    else:
        raise TypeError(f"지원하지 않는 데이터 타입: {type(data)}")
    
    print(f"이동평균 적용 완료: window={window}")
    
    return smoothed


def calculate_trend(
    ts: pd.Series,
    method: str = 'linear',
    return_stats: bool = True
) -> Dict[str, Any]:
    """
    시계열 트렌드 계산
    
    Parameters:
        ts: 시계열 데이터
        method: 트렌드 계산 방법 ('linear', 'polynomial', 'sen')
        return_stats: 통계 정보 반환 여부
        
    Returns:
        트렌드 정보 딕셔너리
        
    Example:
        >>> trend = calculate_trend(ts, method='linear')
    """
    # NaN 제거
    ts_clean = ts.dropna()
    
    if len(ts_clean) < 3:
        raise ValueError("트렌드 계산을 위해 최소 3개의 데이터가 필요합니다.")
    
    # 시간 인덱스를 숫자로 변환
    x = np.arange(len(ts_clean))
    y = ts_clean.values
    
    result = {}
    
    if method == 'linear':
        # 선형 회귀
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        result['slope'] = slope
        result['intercept'] = intercept
        result['r_squared'] = r_value**2
        result['p_value'] = p_value
        result['std_error'] = std_err
        result['trend_line'] = pd.Series(
            slope * x + intercept,
            index=ts_clean.index
        )
        
        # 연간 트렌드 (일 데이터 기준)
        if isinstance(ts_clean.index, pd.DatetimeIndex):
            days_per_year = 365.25
            samples_per_year = len(ts_clean) / ((ts_clean.index[-1] - ts_clean.index[0]).days / days_per_year)
            result['annual_trend'] = slope * samples_per_year
            
    elif method == 'polynomial':
        # 2차 다항식 피팅
        coeffs = np.polyfit(x, y, 2)
        result['coefficients'] = coeffs
        result['trend_line'] = pd.Series(
            np.polyval(coeffs, x),
            index=ts_clean.index
        )
        
    elif method == 'sen':
        # Sen's slope (비모수 방법)
        n = len(y)
        slopes = []
        for i in range(n):
            for j in range(i+1, n):
                slopes.append((y[j] - y[i]) / (j - i))
        
        result['slope'] = np.median(slopes)
        result['trend_line'] = pd.Series(
            result['slope'] * x + np.median(y - result['slope'] * x),
            index=ts_clean.index
        )
    
    else:
        raise ValueError(f"알 수 없는 방법: {method}")
    
    print(f"트렌드 계산 완료: {method}")
    
    return result


def calculate_correlation(
    data1: Union[pd.Series, xr.DataArray],
    data2: Union[pd.Series, xr.DataArray],
    lag: int = 0,
    method: str = 'pearson'
) -> Tuple[float, float]:
    """
    상관관계 계산
    
    Parameters:
        data1: 첫 번째 데이터
        data2: 두 번째 데이터
        lag: 시차 (lag)
        method: 상관 계산 방법 ('pearson', 'spearman', 'kendall')
        
    Returns:
        상관계수, p-value
        
    Example:
        >>> corr, pval = calculate_correlation(sst, wind_speed, lag=3)
    """
    # xarray를 pandas로 변환
    if isinstance(data1, xr.DataArray):
        data1 = data1.to_pandas()
    if isinstance(data2, xr.DataArray):
        data2 = data2.to_pandas()
    
    # Series로 변환
    if isinstance(data1, pd.DataFrame):
        data1 = data1.squeeze()
    if isinstance(data2, pd.DataFrame):
        data2 = data2.squeeze()
    
    # 시차 적용
    if lag != 0:
        data2 = data2.shift(lag)
    
    # NaN 제거
    valid_idx = ~(data1.isna() | data2.isna())
    d1 = data1[valid_idx]
    d2 = data2[valid_idx]
    
    if len(d1) < 3:
        raise ValueError("상관관계 계산을 위해 최소 3개의 데이터가 필요합니다.")
    
    # 상관관계 계산
    if method == 'pearson':
        corr, pval = stats.pearsonr(d1, d2)
    elif method == 'spearman':
        corr, pval = stats.spearmanr(d1, d2)
    elif method == 'kendall':
        corr, pval = stats.kendalltau(d1, d2)
    else:
        raise ValueError(f"알 수 없는 방법: {method}")
    
    print(f"상관관계: {corr:.3f} (p-value: {pval:.4f}, lag: {lag})")
    
    return corr, pval


def apply_filter(
    data: Union[pd.Series, xr.DataArray],
    filter_type: str = 'lowpass',
    cutoff_freq: float = 0.1,
    order: int = 5
) -> Union[pd.Series, xr.DataArray]:
    """
    시계열 필터링 (고주파/저주파 필터)
    
    Parameters:
        data: 입력 데이터
        filter_type: 필터 타입 ('lowpass', 'highpass', 'bandpass')
        cutoff_freq: 차단 주파수
        order: 필터 차수
        
    Returns:
        필터링된 데이터
        
    Example:
        >>> filtered = apply_filter(ts, filter_type='lowpass', cutoff_freq=0.1)
    """
    # xarray를 numpy로 변환
    if isinstance(data, xr.DataArray):
        values = data.values
        is_xarray = True
    elif isinstance(data, pd.Series):
        values = data.values
        is_xarray = False
    else:
        values = np.array(data)
        is_xarray = False
    
    # NaN 처리
    nan_mask = np.isnan(values)
    values_clean = values[~nan_mask]
    
    if len(values_clean) < order * 2:
        raise ValueError(f"데이터가 너무 짧습니다. 최소 {order * 2}개 필요")
    
    # Butterworth 필터 설계
    from scipy.signal import butter, filtfilt
    
    if filter_type == 'lowpass':
        b, a = butter(order, cutoff_freq, btype='low')
    elif filter_type == 'highpass':
        b, a = butter(order, cutoff_freq, btype='high')
    elif filter_type == 'bandpass':
        if not isinstance(cutoff_freq, (list, tuple)) or len(cutoff_freq) != 2:
            raise ValueError("bandpass 필터는 2개의 차단 주파수가 필요합니다.")
        b, a = butter(order, cutoff_freq, btype='band')
    else:
        raise ValueError(f"알 수 없는 필터 타입: {filter_type}")
    
    # 필터 적용
    filtered_clean = filtfilt(b, a, values_clean)
    
    # NaN 위치 복원
    filtered = np.full_like(values, np.nan)
    filtered[~nan_mask] = filtered_clean
    
    # 원래 형식으로 변환
    if is_xarray:
        result = data.copy()
        result.values = filtered
    elif isinstance(data, pd.Series):
        result = pd.Series(filtered, index=data.index, name=data.name)
    else:
        result = filtered
    
    print(f"필터링 완료: {filter_type} (cutoff: {cutoff_freq})")
    
    return result


def detect_extremes(
    data: Union[pd.Series, xr.DataArray],
    threshold_type: str = 'percentile',
    threshold_value: float = 95,
    duration: Optional[int] = None
) -> pd.DataFrame:
    """
    극값 이벤트 탐지
    
    Parameters:
        data: 입력 데이터
        threshold_type: 임계값 타입 ('percentile', 'absolute', 'std')
        threshold_value: 임계값
        duration: 최소 지속 기간
        
    Returns:
        극값 이벤트 정보 DataFrame
        
    Example:
        >>> extremes = detect_extremes(sst, threshold_type='percentile', threshold_value=95)
    """
    # pandas Series로 변환
    if isinstance(data, xr.DataArray):
        ts = data.to_pandas()
    elif isinstance(data, pd.Series):
        ts = data
    else:
        ts = pd.Series(data)
    
    # 임계값 계산
    if threshold_type == 'percentile':
        threshold = np.percentile(ts.dropna(), threshold_value)
    elif threshold_type == 'absolute':
        threshold = threshold_value
    elif threshold_type == 'std':
        mean = ts.mean()
        std = ts.std()
        threshold = mean + threshold_value * std
    else:
        raise ValueError(f"알 수 없는 임계값 타입: {threshold_type}")
    
    # 극값 탐지
    extreme_mask = ts > threshold
    
    # 이벤트 그룹화
    events = []
    in_event = False
    event_start = None
    
    for i, (idx, val) in enumerate(ts.items()):
        if extreme_mask.iloc[i] and not in_event:
            # 이벤트 시작
            in_event = True
            event_start = idx
        elif not extreme_mask.iloc[i] and in_event:
            # 이벤트 종료
            in_event = False
            event_end = ts.index[i-1]
            event_data = ts[event_start:event_end]
            
            # 지속 기간 체크
            if duration is None or len(event_data) >= duration:
                events.append({
                    'start': event_start,
                    'end': event_end,
                    'duration': len(event_data),
                    'max_value': event_data.max(),
                    'mean_value': event_data.mean(),
                    'sum_excess': (event_data - threshold).sum()
                })
    
    # 마지막 이벤트 처리
    if in_event:
        event_end = ts.index[-1]
        event_data = ts[event_start:event_end]
        if duration is None or len(event_data) >= duration:
            events.append({
                'start': event_start,
                'end': event_end,
                'duration': len(event_data),
                'max_value': event_data.max(),
                'mean_value': event_data.mean(),
                'sum_excess': (event_data - threshold).sum()
            })
    
    result = pd.DataFrame(events)
    print(f"극값 이벤트 탐지 완료: {len(events)}개 이벤트 (임계값: {threshold:.2f})")
    
    return result


def merge_datasets(
    datasets: List[xr.Dataset],
    dim: str = 'time',
    method: str = 'outer'
) -> xr.Dataset:
    """
    여러 데이터셋 병합
    
    Parameters:
        datasets: Dataset 리스트
        dim: 병합할 차원
        method: 병합 방법 ('outer', 'inner', 'left', 'right')
        
    Returns:
        병합된 Dataset
        
    Example:
        >>> merged = merge_datasets([ds1, ds2, ds3], dim='time')
    """
    if len(datasets) < 2:
        raise ValueError("최소 2개의 데이터셋이 필요합니다.")
    
    # 첫 번째 데이터셋을 기준으로 시작
    merged = datasets[0]
    
    # 순차적으로 병합
    for ds in datasets[1:]:
        if dim == 'time':
            merged = xr.concat([merged, ds], dim=dim)
        else:
            merged = xr.merge([merged, ds], join=method)
    
    # 중복 제거 및 정렬
    if dim in merged.dims:
        merged = merged.sortby(dim)
        if dim == 'time':
            merged = merged.drop_duplicates(dim=dim)
    
    print(f"데이터셋 병합 완료: {len(datasets)}개 → 1개")
    print(f"최종 크기: {dict(merged.dims)}")
    
    return merged


def quality_check(
    ds: xr.Dataset,
    var_name: str,
    valid_range: Optional[Tuple[float, float]] = None,
    max_gap: Optional[int] = None,
    min_coverage: float = 0.8
) -> Dict[str, Any]:
    """
    데이터 품질 검사
    
    Parameters:
        ds: xarray Dataset
        var_name: 변수 이름
        valid_range: 유효 범위 (min, max)
        max_gap: 최대 연속 결측 허용 개수
        min_coverage: 최소 데이터 커버리지 비율
        
    Returns:
        품질 검사 결과 딕셔너리
        
    Example:
        >>> qc = quality_check(ds, 'sst', valid_range=(0, 40))
    """
    data = ds[var_name]
    
    result = {
        'variable': var_name,
        'total_points': data.size,
        'shape': data.shape,
        'dtype': str(data.dtype)
    }
    
    # 결측값 통계
    nan_count = np.isnan(data).sum().item()
    result['missing_count'] = nan_count
    result['missing_percent'] = (nan_count / data.size) * 100
    result['coverage'] = 1 - (nan_count / data.size)
    
    # 범위 검사
    if valid_range:
        valid_mask = (data >= valid_range[0]) & (data <= valid_range[1])
        invalid_count = (~valid_mask).sum().item() - nan_count
        result['out_of_range_count'] = invalid_count
        result['out_of_range_percent'] = (invalid_count / data.size) * 100
    
    # 기본 통계
    result['min'] = float(np.nanmin(data))
    result['max'] = float(np.nanmax(data))
    result['mean'] = float(np.nanmean(data))
    result['std'] = float(np.nanstd(data))
    
    # 시간 차원이 있는 경우 연속 결측 검사
    if 'time' in data.dims and max_gap:
        time_series = data.mean(dim=[d for d in data.dims if d != 'time'])
        nan_mask = np.isnan(time_series)
        
        # 연속 결측 구간 찾기
        gaps = []
        in_gap = False
        gap_start = 0
        
        for i, is_nan in enumerate(nan_mask.values):
            if is_nan and not in_gap:
                in_gap = True
                gap_start = i
            elif not is_nan and in_gap:
                in_gap = False
                gap_length = i - gap_start
                if gap_length > max_gap:
                    gaps.append((gap_start, i, gap_length))
        
        result['long_gaps'] = gaps
        result['max_gap_length'] = max(g[2] for g in gaps) if gaps else 0
    
    # 품질 평가
    result['quality_pass'] = (
        result['coverage'] >= min_coverage and
        result.get('out_of_range_percent', 0) < 5 and
        result.get('max_gap_length', 0) <= (max_gap or float('inf'))
    )
    
    print(f"품질 검사 완료: {var_name}")
    print(f"  - 커버리지: {result['coverage']:.1%}")
    print(f"  - 품질 통과: {'✓' if result['quality_pass'] else '✗'}")
    
    return result


# 유틸리티 함수들

def list_variables(ds: xr.Dataset) -> pd.DataFrame:
    """
    데이터셋의 변수 목록과 정보 출력
    
    Parameters:
        ds: xarray Dataset
        
    Returns:
        변수 정보 DataFrame
    """
    info = []
    for var in ds.data_vars:
        var_data = ds[var]
        info.append({
            'variable': var,
            'dimensions': list(var_data.dims),
            'shape': var_data.shape,
            'dtype': str(var_data.dtype),
            'units': var_data.attrs.get('units', ''),
            'long_name': var_data.attrs.get('long_name', ''),
            'missing_values': np.isnan(var_data).sum().item()
        })
    
    df = pd.DataFrame(info)
    return df


def save_config(config: Dict, filepath: str) -> None:
    """분석 설정 저장"""
    with open(filepath, 'w') as f:
        json.dump(config, f, indent=2, default=str)
    print(f"설정 저장: {filepath}")


def load_config(filepath: str) -> Dict:
    """분석 설정 로드"""
    with open(filepath, 'r') as f:
        config = json.load(f)
    print(f"설정 로드: {filepath}")
    return config


print("Copernicus Utils 모듈 로드 완료!")
print("사용 가능한 함수:", [
    'load_dataset', 'subset_region', 'subset_time', 
    'calculate_spatial_mean', 'create_timeseries',
    'plot_map', 'plot_timeseries', 'export_to_csv',
    'calculate_anomaly', 'apply_moving_average',
    'calculate_trend', 'calculate_correlation',
    'apply_filter', 'detect_extremes', 'merge_datasets',
    'quality_check'
])