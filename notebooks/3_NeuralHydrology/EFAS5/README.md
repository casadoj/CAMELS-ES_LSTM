# LSTM-EFAS5

Los tres test que se han hecho para reproducir el caudal simulado en EFAS5 utilizan como series de entradas las meteorológicas de EMO1 (temperatura, precipitación y evapotranspiración). En cambio, se diferencian en los atributos estáticos:

* **test1**: utiliza sólo los parámetros calibrados de LISFLOOD.
* **test2**: utiliza sólo los atributos generados a partir de los mapas estáticos de LISFLOOD.
* **test3**: utiliza tanto los parámetros calibrados como los mapas estáticos de LISFLOOD.

Los resultados más convincentes de las primeras pruebas fueron los obtenidos para el **test3**, es decir, el modelo que utiliza tanto los parámetros calibrados como los mapas estáticos. Sobre este modelo se entrenaron diversos modelos para ajustar los hiperparámetros:

| Modelo  | `batch_size` | `hidden_size` | `dropout` | `clip_gradient_norm` |
| ------- | ------------ | ------------- | --------- | -------------------- |
| test3.3 |  256         | 128           | 0.5       | 0.8                  |
| **test3.4** |  512         | 128           | 0.5       | 0.8                  |
| test3.5 |  512         | 64            | 0.5       | 0.8                  |
| test3.6 |  512         | 128           | 0.4       | 1.0                  |