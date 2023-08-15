import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt



def extraer_caudal(file, indroea=None, start=None, end=None):
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



def extraer_estaciones(file, active=False, min_area=None, max_area=None, years=None, epsg=4326):
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



def extraer_embalses(file, active=False, epsg=4326):
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



def plot_caudal(serie, save=None, **kwargs):
    """Crea un gráfico de línea con el hidrograma de una estación de aforo.

    Parámetros:
    -----------
    serie:     pd.Series. Serie de caudal
    save:      str. Ruta donde guardar el gráfico. Por defecto es None y el gráfico no se guarda
    """
    
    fig, ax = plt.subplots(figsize=kwargs.get('figsize', (16, 4)))
    ax.plot(serie, lw=.8)
    ax.set(xlim=(serie.index.min(), serie.index.max()),
           ylim=(0, None),
           ylabel='Q (m3/s)',
           title=kwargs.get('title', None))
    
    if save is not None:
        plt.savefig(save, dpi=300, bbox_inches='tight')