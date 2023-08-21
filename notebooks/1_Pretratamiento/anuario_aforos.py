import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from shapely.geometry import Point
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Union



def extraer_caudal(file: Path, indroea: Union[str, List[str]] = None, start: Union[str, pd.Timestamp] = None, end: Union[str, pd.Timestamp] = None) -> pd.DataFrame:
    """Extrae las series diarias de caudal del archivo 'afliq.csv' del Anuario de Aforos. La serie se puede recortar al periodo y estaciones de interés
    
    Parámetros:
    -----------
    file:      str. Ruta del archivo original con las series de caudal
    indroea:   str or list. Listado con el ID de las estaciones ROEA (Red Oficial de Estaciones de Aforo) cuya serie de caudal se quiere extraer
    start:     str or datetime.date. Fecha de inicio del periodo de estudio
    end:       str or datetime.date. Fecha final del periodo de estudio

    Salida:
    -------
    caudal:    pandas.DataFrame. Tabla con las series de caudal diario
    """

    if isinstance(indroea, str):
        indroea = [indroea]
    elif isinstance(indroea, list):
        indroea = [str(x) for x in indroea]
    elif indroea is not None:
        print('ERROR. "indorea" ha de ser bien una cadena de texto, una lista o None.')
        return
    
    # cargar series
    data = pd.read_csv(file, sep=';', index_col='indroea')
    data.index = data.index.astype(str)
    data.fecha = pd.to_datetime(data.fecha, dayfirst=True)

    # recortar a la fecha de estudio
    if start is not None:
        data = data.loc[data.fecha >= start, :]
    if end is not None:
        data = data.loc[data.fecha <= end, :]

    # reformatear series de caudal y nivel
    if indroea is None:
        cols = data.index.unique()
    else:
        cols = data.index.unique().intersection(indroea)
    caudal = pd.DataFrame(index=pd.date_range(data.fecha.min(), data.fecha.max(), freq='1d'), columns=cols, dtype=float) 
    for stn in caudal.columns:
        data_stn = data.loc[stn].set_index('fecha', drop=True)
        caudal[stn] = data_stn.caudal
    
    # eliminar estaciones sin ningún dato
    caudal.dropna(axis=1, how='all', inplace=True)

    caudal.index.name = 'date'

    return caudal



def extraer_estaciones(file: Path, active: bool = False, min_area: int = None, max_area: int = None, years: int = None, epsg: int = 4326) -> gpd.GeoDataFrame:
    """Extrae la tabla de atributos de las estaciones del ROEA del archivo 'estaf.csv' del Anuario de Aforos. Se pueden filtrar las estaciones por área, por número de años con datos y si están aún activas
    
    Parámetros:
    -----------
    file:      str. Ruta del archivo original con las estaciones
    active:    boolean. Si True, se queda sólo con estaciones activas
    min_area:  int or float. Área mínima de la cuenca (km²) para incluir la estación en la extracción
    max_area:  int or float. Área máxima de la cuenca (km²) para incluir la estación en la extracción
    years:     int. Número mínimo de años con dato
    epsg:      int. Código EPSG del sistema de coordenadas en el que se quieren projectar los puntos: 4326 (WGS84) ó 25830 (ETRS89-UTM 30N)

    Salida:
    -------
    estaciones:    geopandas.GeoDataFrame. Capa de puntos con las estaciones
    """

    # cargar datos
    estaciones = pd.read_csv(file, sep=';', index_col='indroea', encoding='latin1')
    estaciones.index = estaciones.index.astype(str)
    estaciones.index.name = 'indroea'
    estaciones.lugar = estaciones.lugar.str.strip()
    estaciones.dropna(axis=1, how='all', inplace=True)
    for col in ['long', 'lat', 'longwgs84', 'latwgs84']:
        estaciones[col] /= 1e4

    # filtros
    if active:
        estaciones = estaciones[estaciones.serv == 2]
    if min_area is not None:
        if (isinstance(min_area, int) | isinstance(min_area, int)) & (min_area > 0):
            estaciones = estaciones[estaciones.suprest >= min_area]
        else:
            print('"min_area" debe ser un número entero o real positivo')
    if max_area is not None:
        if (isinstance(max_area, int) | isinstance(max_area, int)) & (max_area > 0):
            estaciones = estaciones[estaciones.suprest <= max_area]
        else:
            print('"max_area" debe ser un número entero o real positivo')
    if years is not None:
        if isinstance(years, int):
            estaciones = estaciones[estaciones.naa >= years]
        else:
            print('"years" debe ser un número entero positivo')

    # convertir en GeoDataFrame
    assert epsg in [4326, 25830], '"epsg" debe ser 4326 (WGS84) ó 25830 (ETRS89-UTM 30N)'
    geometry = [Point(x, y) for x, y in zip(estaciones.xetrs89, estaciones.yetrs89)]
    if epsg == 4326:
        estaciones = gpd.GeoDataFrame(estaciones, geometry=geometry, crs=25830).to_crs(4326)
    elif epsg == 25830:
        estaciones = gpd.GeoDataFrame(estaciones, geometry=geometry, crs=epsg)

    return estaciones



def extraer_embalses(file: Path, active: bool = False, epsg: int = 4326) -> gpd.GeoDataFrame:
    """Extrae la tabla de atributos de los embalses del archivo 'embalse.csv' del Anuario de Aforos. Se pueden filtrar para mantener sólo embalses activos
    
    Parámetros:
    -----------
    file:      str. Ruta del archivo original con los embalses
    active:    boolean. Si True, se queda sólo con estaciones activas
    epsg:      int. Código EPSG del sistema de coordenadas en el que se quieren projectar los puntos: 4326 (WGS84) ó 25830 (ETRS89-UTM 30N)

    Salida:
    -------
    data:       geopandas.GeoDataFrame. Capa de puntos con los embalses
    """

    data = pd.read_csv(file, sep=';', index_col='ref_ceh', encoding='latin1')
    data.index = data.index.astype(str)
    data.dropna(axis=1, how='all', inplace=True)
    for col in ['long', 'lat', 'longwgs84', 'latwgs84']:
        data[col] /= 1e4

    # filtros
    if active:
        data = data[data.serv == 2]

    assert epsg in [4326, 25830], '"epsg" debe ser 4326 (WGS84) ó 25830 (ETRS89-UTM 30N)'
    geometry = [Point(x, y) for x, y in zip(data.xetrs89, data.yetrs89)]
    if epsg == 4326:
        data = gpd.GeoDataFrame(data, geometry=geometry, crs=25830).to_crs(4326)
    elif epsg == 25830:
        data = gpd.GeoDataFrame(data, geometry=geometry, crs=epsg)

    return data



def plot_caudal(serie: pd.Series, inicios: List[pd.Timestamp] = None, finales: List[pd.Timestamp] = None, save: str = None, **kwargs):
    """Crea un gráfico de línea con el hidrograma de una estación de aforo.

    Parámetros:
    -----------
    serie:     pd.Series. Serie de caudal
    save:      str. Ruta donde guardar el gráfico. Por defecto es None y el gráfico no se guarda
    """

    lw = kwargs.get('lw', .8)
    
    fig, ax = plt.subplots(figsize=kwargs.get('figsize', (16, 4)))
    if (inicios is None) or (finales is None):
        ax.plot(serie, lw=lw)
        ax.set_xlim(serie.first_valid_index(), serie.last_valid_index())
    else:
        assert len(inicios) == len(finales), 'La longitud de las listas "inicios" y "finales" ha de ser la misma.'
        for ini, fin in zip(inicios, finales):
            ax.plot(serie[ini:fin], lw=lw)
        ax.set_xlim(np.min(inicios), np.max(finales))
        
    ax.set(ylim=(0, None),
           ylabel=kwargs.get('ylabel', 'Q (m3/s)'),
           title=kwargs.get('title', None))
    
    if save is not None:
        plt.savefig(save, dpi=300, bbox_inches='tight')



def periodo_estudio(series: pd.DataFrame, disponibilidad: float = .9, min_años: int = 8) -> pd.DataFrame:
    """Dadas un conjunto de series temporales, define el año de inicio y fin de la serie más larga con una disponibilidad de datos superior a la indicada

    Parámetros:
    -----------
    series: pd.DataFrame
        Tabla con las series temporales. Las filas han de ser el eje temporal y las columnas las distintas series.
    disponibilidad: float
        Proporción de datos disponibles en un año para ser considerado éste como bueno
    min_años: int
        Longitud mínima en años de la serie necesaria para considerar la serie como buena. Si no se alcanza este número de años, se descarta la serie 
    
    Devuelve:
    ---------
    pd.DataFrame
        Tabla donde el índice son las columnas de "series" y las columnas las fechas de inicio y final de la serie consecutiva más larga de dicha estación
    """

    assert 0 < disponibilidad <= 1, 'La "disponibilidad" debe de tener un valor mayor a 0 y menor o igual a 1.'
    assert min_años > 0, '"min_años" debe ser un número entero positivo'
    
    # calcular la disponibilidad de datos cada año en cada estación
    series_anual = series.groupby(series.index.year)
    n_datos = series_anual.count()
    n_dias = series_anual.size()
    for año in n_dias.index:
        n_datos.loc[año,:] /= n_dias[año]
    
    # nº de años con disponibilidad por encima de la mínima en cada estación
    disp = n_datos >= disponibilidad
    
    # quedarse con estaciones con el mínimo número de años consecutivos
    disp_diff = disp.astype(int).diff(axis=0)
    disp_diff.iloc[0,:] = disp.iloc[0,:].astype(int)

    # inicio y fin de la serie a utilizar
    periodos = {'inicio': {}, 'fin': {}}
    for stn in disp_diff.columns:
    
        # inicios y finales de cada una de las series de años que cumplen la disponibilidad
        inicios = disp_diff[disp_diff[stn] == 1].index.values
        finales = disp_diff[disp_diff[stn] == -1].index.values - 1
        if len(inicios) == len(finales) + 1:
            # finales.append(disp_diff.index[-1])
            finales = np.hstack((finales, disp_diff.index[-1]))
    
        # quedarse con el último periodo de datos completos
        duraciones = finales - inicios + 1
        i = np.where(duraciones >= min_años)[0]
        if len(i) > 0:
            periodos['fin'][stn] = finales[i[-1]]
            periodos['inicio'][stn] = inicios[i[-1]]
        else:
            continue

    return pd.DataFrame(periodos)


def dividir_periodo_estudio(serie: pd.Series, ini: int = None, fin: int = None, cal: float = .6, val: float = .2) -> xr.DataArray:
    """Dada una serie temporal, se definen las fechas de inicio y fin de los periodos de calibración ('train'), validación ('validation') y evaluación ('test').

    Parámetros:
    -----------
    serie: pd.Series
        Serie temporal a dividir
    ini: int
        Año de inicio del periodo de estudio
    fin: int
        Año de fin del periodo de estudio
    cal: float
        Proporción de los datos a incluir en el periodo de calibración. Estos datos se tomarán de la parte final de la serie.
    val: float
        Proporción de los datos a incluir en el periodo de validación. Estos datos se tomarán de los años inmediatamente anteriores al periodo de calibración. Si la suma de "cal" y "val" es menor a 1, el resto de los datos serán el periodo de evaluación 

    Devuelve:
    ---------
    xr.DataArray
        Contiene para cada periodo (calibración, validación y test) las fechas de inicio y fin.
    """

    assert cal + val <= 1, 'La suma de "entrenamiento" y "validación no puede ser mayor de 1."'

    if cal + val < 1:
        test = 1 - cal - val
    else:
        test = None

    # periodo completo de datos
    n_años = fin - ini
    ini = serie[serie.index.year == ini].first_valid_index()
    fin = serie[serie.index.year == fin].last_valid_index()

    # periodo de test
    if test is not None:
        ini_test = ini
        n_test = round(n_años * test)
        fin_test = pd.Timestamp(ini_test.year + n_test, 9, 30)

    # periodo de validación
    if test is None:
        ini_val = ini
    else:
        ini_val = fin_test + pd.Timedelta(days=1)
    n_val = round(val * n_años)
    fin_val = pd.Timestamp(ini_val.year + n_val, 9, 30)

    # periodo de calibración
    ini_cal = fin_val + pd.Timedelta(days=1)
    fin_cal = fin

    if test is None:
        # df = pd.DataFrame([[ini_cal, ini_val], [fin_cal, fin_val]], index=['inicio', 'fin'], columns=['cal', 'val'])
        da = xr.DataArray([[ini_cal, ini_val], [fin_cal, fin_val]],
                          coords={'date': ['start', 'end'],
                                  'period': ['train', 'validation']},
                          dims=['date', 'period'])
    else:
        # df = pd.DataFrame([[ini_cal, ini_val, ini_test], [fin_cal, fin_val, fin_test]], index=['inicio', 'fin'], columns=['cal', 'val', 'test'])
        da = xr.DataArray([[ini_cal, ini_val, ini_test], [fin_cal, fin_val, fin_test]],
                          coords={'date': ['start', 'end'],
                                  'period': ['train', 'validation', 'test']},
                          dims=['date', 'period'])
        
    return da