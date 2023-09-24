Apart from the usual attributes that CARAVAN computes, CAMELS-ES includes another two CSV files with attributes generated from the EFAS meteorological input (EMO1) and static maps:

attributes_efas_hydrometeorology_es.csv
---------------------------------------

Hydrometeorological statistics generated from the EMO1 data set and the discharge simulated in the EFASv5 long run.
The attributes include mean monthly and annual values for three meteorological variables (pr, precipitation; ta, air temperature; e0, reference evapotranspiration)
and mean, maximum and minimum annual simulated discharge.

attributes_efas_static_maps_es.csv
----------------------------------

Zonal statitics derived from the LISFLOOD input static maps.
The name given to the attributes is the same as that used in the LISFLOOD model, see the model documentation (https://ec-jrc.github.io/lisflood-model/4_1_annex_input-files/)
for detailed informtaion. Depending on the attribute, diverse statistics were computed (mean, sum, standard deviation, count). In the case of the
water demands and LAI, the only dynamic attributes, monthtly and annual means were computed.


References:
* EMO1: http://data.europa.eu/89h/0bd84be4-cec8-4180-97a6-8b3adaac4d26 
* EFAS5: https://www.efas.eu/en
* LISFLOOD static maps: http://data.europa.eu/89h/f572c443-7466-4adf-87aa-c0847a169f23