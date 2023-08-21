import os
os.environ['USE_PYGEOS'] = '0'
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping, Point
import xarray as xr
import rioxarray
from tqdm.notebook import tqdm
from typing import Union, List, Dict
from pathlib import Path


def dict2da(dictionary, dim):
    """It converts a dictionary of xarray.Datarray into a single xarray.DataArray combining the keys in the dictionary in a new dimension
    
    Inputs:
    -------
    dictionary: dict. A dictionary of xarray.DataArray
    dim:        str. Name of the new dimension in which the keys of 'dictionary' will be combined
    
    Output:
    -------
    array:      xr.DataArray.
    """
    
    if isinstance(dictionary, dict) is False:
        return 'ERROR. The input data must be a Python dictionary.'
        
    data = list(dictionary.values())
    coord = xr.DataArray(list(dictionary), dims=dim)

    return xr.concat(data, dim=coord)



def read_static_map(path: Union[Path, str], x_dim: str = 'lon', y_dim: str = 'lat', crs: str = 'epsg:4326', var: str = 'Band1') -> xr.DataArray:
    """Lee el archivo NetCDF de un mapa estático de LISFLOOD y lo carga como un xarray.DataArray.

    Parámetros:
    -----------
    path: Path
        nombre del archivo NetCDF a abrir
    x_dim: str
        nombre de la dimensión que corresponde a la coordenada X
    y_dim: str
        nombre de la dimensión que corresponde a la coordenada Y
    crs: str
        código EPSG del sistema de coordenadas de referencia. Debe ser de la forma 'epsg:4326'
    var: str
        nombre de la variable en el NetCDF que contiene el mapa a importar

    Devuelve:
    ---------
    xr.DataArray
        un mapa con coordenadas "x_dim", "y_dim" en el sistema de referencia "crs"
    """
    
    # cargar los datos
    da = xr.open_mfdataset(path, chunks=None)[var].compute()

    # definir dimensiones con las coordenadas
    da = da.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim)
    
    # definir sistema de coordenadas
    da = da.rio.write_crs(crs)

    return da



def polygon_statistics(mapa: Union[xr.DataArray, xr.Dataset], poligonos: gpd.GeoDataFrame, func: str = Union[str, List[str]], x_dim: str = 'lon', y_dim: str = 'lat', ponderacion: xr.DataArray = None) -> xr.Dataset:
    """Dado un mapa en formato Rioxarray y una capa de polígonos, calcula el estadístico agregado de cada cuenca. Es imprescindible que tanto el mapa como los polígonos estén en el mismo sistema de referencia.

    Parámetros:
    ----------
    mapa:        xarray.DataArray o xarray.Dataset
        Mapa o serie de mapas a recortar. Debe de haberse utilizado la librería Rioxarray para definir el sistema de referencia de coordenadas y las dimensiones que definen las coordenadas
    poligonos:   geopandas.GeoDataFrame
        Tabla con los polígonos.
    func:        str o list.
        Funciones estadísticas a aplicar sobre el recorte del mapa de cada polígono. Los nombres han de ser los utilizados en Xarray: 'mean', 'median', 'std', 'min', 'max'
    x_dim:       str
        Nombre de la dimensión de "mapa" correspondiente a la dimensión X
    y_dim:       str
        Nombre de la dimensión de "mapa" correspondiente a la dimensión Y
    ponderacion: xr.DataArray
        Mapa utilizado para ponderar el peso de cada celda en el cálculo del estadístico. Está específicamente pensado para ponderar las celdas por su área en el caso de que ésta no sea idéntica (coordenadas geográficas)

    Devuelve:
    ---------
    xr.Dataset
        Matriz con los estadísticos areales del mapa de entrada para cada uno de los polígonos
    """

    assert poligonos.crs == mapa.rio.crs, '"mapa" y "poligonos" han de tener el mismo sistema de coordenadas de referencia (CRS).'
    if ponderacion is not None:
        assert mapa.rio.crs == ponderacion.rio.crs, '"ponderacion" ha de ser un xarray.DataArray similar a "mapa"'

    if isinstance(mapa, xr.DataArray):
        crs = mapa.rio.crs
        mapa = xr.Dataset({mapa.name: mapa})
        mapa = mapa.rio.write_crs(crs)
        mapa = mapa.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim)

    if isinstance(func, str):
        func = {var: [func] for var in mapa}
    elif isinstance(func, list):
        func = {var: func for var in mapa}

    # definir el Dataset donde se guardarán los resultados
    dims = dict(mapa.dims)
    del dims[x_dim]
    del dims[y_dim]
    coords = {dim: mapa[dim] for dim in dims}
    coords.update({'id': poligonos.index.to_list()})
    vars = [f'{var}_{f}' for var, fs in func.items() for f in fs]
    ds = xr.Dataset({var: xr.DataArray(coords=coords, dims=coords.keys()) for var in vars})

    # calcular estadísticos areales
    for id in tqdm(ds.id.data):

        # recortar mapa al polígono
        poligono = poligonos.loc[[id]]
        recorte = mapa.rio.clip(poligono.geometry.apply(mapping), poligono.crs, drop=True)
        recorte = recorte.compute()

        # ponderar el mapa
        if ponderacion is not None:
            # recortar el mapa de ponderación
            pond_pol = ponderacion.rio.clip(poligono.geometry.apply(mapping), poligono.crs, drop=True)
            # aplicar ponderación
            recorte = recorte.weighted(pond_pol.fillna(0))

        # calcular estadísticos
        for var, fs in func.items(): 
            if var not in mapa:
                print(f'ERROR. La variable "{var}" no está en "mapa".')
            for f in fs:
                if f == 'mean':
                    x = recorte.mean([x_dim, y_dim])[var].data
                elif f == 'median':
                    x = recorte.median([x_dim, y_dim])[var].data
                elif f == 'std':
                    x = recorte.std([x_dim, y_dim])[var].data
                elif f == 'max':
                    x = recorte.max([x_dim, y_dim])[var].data
                elif f == 'min':
                    x = recorte.min([x_dim, y_dim])[var].data
                elif f == 'sum':
                    x = recorte.sum([x_dim, y_dim])[var].data
                else:
                    print(f'ERROR. La función "{f}" no está entre las que calcula esta función')
                    continue

                ds[f'{var}_{f}'].loc[{'id': id}] = x
                del x
        del poligono, recorte

    return ds



def point_polygon_statistics(puntos: gpd.GeoDataFrame, poligonos: gpd.GeoDataFrame, func: str = 'mean') -> pd.DataFrame:
    """Dadas una capa de puntos y una capa de polígonos, calcula el estadístico agregado de cada cuenca. Es imprescindible que ambas capas estén en el mismo sistema de referencia.

    Atributos:
    ----------
    puntos:      geopandas.GeoDataFrame. Tabla con los puntos.
    poligonos:   geopandas.GeoDataFrame. Tabla con los polígonos.
    func:        str o list. Funciones estadísticas a aplicar sobre la selección de puntos de cada polígono. Los nombres han de ser los utilizados en Pandas: 'mean', 'median', 'std', 'min', 'max'
    """

    try:
        if poligonos.crs != puntos.crs:
            return 'ERROR. Los puntos y los polígonos no están en el mismo sistema de referencia de coordenadas.'
    except:
        return 'ERROR. O los puntos o los polígonos no tienen definido el sistema de referencia de coordenadas.'

    if isinstance(func, str):
        func = {var: [func] for var in puntos.columns}
    elif isinstance(func, list):
        func = {var: func for var in puntos.columns}

    df = pd.DataFrame(index=poligonos.index)
    for id in tqdm(df.index):

        # extraer polígono de la cuenca
        poligono = poligonos.loc[[id]]
        # encontrar embalses en la cuenca
        puntos_sel = gpd.sjoin(puntos, poligono, how='inner', predicate='within')
        if puntos_sel.shape[0] > 0:

            for var, fs in func.items(): 
                if var not in puntos_sel.columns:
                    print(f'ERROR. La variable "{var}" no está en "puntos".')
                for f in fs:
                    # calcular estadístico
                    if f == 'mean':
                        x = puntos_sel[var].mean()
                    elif f == 'median':
                        x = puntos_sel[var].median()
                    elif f == 'std':
                        x = puntos_sel[var].std()
                    elif f == 'max':
                        x = puntos_sel[var].max()
                    elif f == 'min':
                        x = puntos_sel[var].min()
                    elif f == 'sum':
                        x = puntos_sel[var].sum()
                    elif f == 'count':
                        x = puntos_sel[var].count()
                    else:
                        print(f'ERROR. La función "{f}" no está entre las que calcula esta función')
                        continue
                    df.loc[id, f'{var}_{f}'] = x
    
    # df.replace(np.nan, 0, inplace=True)

    return df



