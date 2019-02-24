# Aplazame Wallet

Backend code challenge para Aplazame

## Readme técnico

### Requirements:
* docker
* docker-compose
* Python 3.7.2

### Tests

```bash
docker-compose up --build db backend-test
```

### Launch production environment locally

```bash
docker-compose up --build db backend
```

### Build production image

```bash
docker-compose build backend
```



## Readme de la prueba

## Overiew del proyecto

El modelo de datos esta basado en los patrones CQRS y Event Sourcing (o en mi interpretación de ambos). Se ha separado
de forma que se pueda tener un subsistema de lectura y otro de escritura. 

* El subsistema de escritura crea eventos (transacciones en este caso) en la tabla Transactions, 
que pasa a ser nuestro Event Source y unica fuente fiable del estado del sistema. La tabla Transactions es una tabla
denormalizada sin relaciones, lo que permite leer y escribir en ella rápidamente, optimizarla y en el peor de los casos
migrarla a un sistema mejor preparado para la tarea.

* El subsistema de lectura esta pensado para proveer el resto de los datos. Con un property "funds" en el modelo
de los Wallets, calculamos el saldo del wallet leyendo el historial de transacciones de la misma. Esta property
podría cachearse y así tener un modelo de sincronizacion On-Demand controlado por lo que dure la cache, para evitar
lecturas innecesarias.

Solución a las constraints de negocio planteadas: 

* Operaciones atomicas: Usar las ventajas transaccionales de tener un DBMS SQL.
* Validar fondos suficientes: Basta con calcular los fondos (método Transaction:get_wallet_funds) con un aggregate.
* Evitar cargos dobles: Usar un nonce, en este caso un Invoice, que es unico por wallet, por lo que si se envia dos
veces el mismo invoice a la misma wallet, se considera un cobro duplicado y se descarta.
* El historial de operaciones debe mostrar las operaciones fallidas: Usar un campo accepted que permita
marcar las operaciones aceptadas y fallidas por este motivo (u otro si así se quiere), y un campo comment que 
le da una razón al usuario de por que ha fallado la transacción.


## Problemas conocidos:

* El método para evitar problemas de concurrencia en el event source (Tabla Transactions), se basas en la funcion 
select_for_update de django. Teóricamente al hacer un select_for_update en la ultima transacción de una wallet
estoy bloqueando esa transacción para lectura, por lo que si dos comandos llegasen de forma concurrente, el primero
bloqueara el registro, dejando al segundo comando en espera hasta que termine la transaccion (atomic de django).

En caso de que esto no funcione como se espera, podemos irnos a un modelo mas pesimista y bloquear la tabla entera, o 
a un modelo mas optimista y utilizar una tabla auxiliar para guardar las aggregations realizadas sobre esta tabla,
al tener aggregations versionadas, siempre que exista un conflicto de versión se puede volver a intentar la transacción.

* El modelo de sincronización del subsistema de lectura esta basado en un modelo on-demand sincrono, es decir,
cada vez que el usuario llama al endpoint de estado de cuenta, los fondos de todas sus wallets se calculan atacando al
subsistema de comandos, es decir, se reconstruye el campo funds cada vez leyendo la historia entera. Esto se puede
mejorar agregando cache a ese campo si es necesario, o pensando en otro modelo de sincronización

* wallet_from no se valida en el endpoint /charge

* No se están capturando errores de base de datos, como los errores de integridad

* La documentación no muestra los parametros del body correctamente

* El campo invoice solo se guarda en transacciones exitosas para aprovechar el constraint en la DB,
se puede mejorar si en el futuro se quiere filtrar por invoice y ver las transacciones fallidas.

* Mejorar la suite de tests, crear tests unitarios, integración y mejorar los de aceptación.

* Actualmente un cliente puede cobrar a otro cliente, incluso cobrarse entre sus mismas cuentas.

* No se ha implementado ninguna validación ni autenticación mas allá de las que provee django por defecto.



## Objetivos y tareas

1.​ Desplegar el proyecto en la instancia proporcionada.
Idealmente con docker y/o despliegues automáticos, puedes incluirlo todo en el repositorio.

```text
Por cuestiones de tiempo no pude terminar el despliegue, ni automatizarlo como me hubiese gustado. He optado por
ejecutar las migraciones y ejecutar el servicio manualmente.

Hay una problemática que no tengo resuelta aun en django y es el tema de las migraciones. Con Alembic (SQLAlchemy)
era capaz de incluir en el mismo paquete las migraciones y el sistema que las ejecuta. Con Django me ha faltado
tiempo para descubrir como hacer algo similar. Esto lo que me permite es, con el mismo contenedor de 
producción del servicio, poder invocar de forma controlada o automáticamente al ejecutar el contenedor las migraciones.

Hasta donde llegue es tener un docker-compose y un dockerfile que ejecute los tests y 
cree una imagen de producción que luego se suba a algún Docker Hub. Ambas etapas en diferentes stages del Dockerfile, 
de forma que en el contenedor de producción no queden elementos del entorno de test.

Posteriormente, lo ideal seria que con ayuda de algún servicio como
Kubernetes o Swarm se gestione el despliegue y actualizacion de las imágenes.

En cuanto a automatizar el despliegue, el Dockerfile esta pensado para que una herramienta de automatización de 
tareas como Jenkins, pueda tener diferentes stages, por ejemplo, de pruebas, construcción y despliegue o subida 
de artefactos, con simplemente ejecutar los diferentes stages del Dockerfile.

Con docker-compose los targets ya están predefinidos, de forma que solo tengas que ejecutar un servicio u otro
según la etapa en la que te encuentres, y al mismo tiempo, al construir la imagen de producción, la deja ya
tageada (faltaría tener una variable de entorno para definir el tag en vez de latest).

En cuanto a como configurar el automatizador de tareas, pensaría en tener algo como las Multibranch
Pipelines que ofrece Jenkins. De forma que puedas construir ramas y tags de forma independiente y controlar que
etapas se ejecutan en cada caso.
```

2.​ Indica cómo se puede optimizar el rendimiento del servicio de listado de operaciones.

```text
El Event Source del subsistema de comandos (Tabla transacciones), es una tabla denormalizada, 
por lo que optimizar las operaciones de lectura sobre ella debería resultar trivial con 
cualquier DBMS SQL tradicional.

Cuando el rendimiento comience a ser un problema por el volumen de datos de la tabla podemos
plantearnos pasar el Event Source a un modelo de Snapshots, que consiste en compactar una serie de
comandos antiguos en un Snapshot, por lo que tanto reconstruir la historia como listar todas las
operaciones tendría una carga, tanto de almacenamiento como de procesamiento, 
en el subsistema mucho mas controlada.

Por otra parte, la solución mas trivial en el estado actual del prototipo seria paginar 
las consultas.

Finalmente, pensaría en migrar el subsistema de comandos entero a un DBMS SQL o NoSQL, 
mejor pensado para la tarea.
```

3​ . ¿Qué alternativas planteas en el caso que la base de datos relacional de la aplicación se
convierta en un cuello de botella por saturación en las operaciones de lectura? ¿Y para las de
escritura?

```text
Los DBMS permiten optimizar los modelos de datos y las operaciones para que esto no sea un problema
inmediato.

Llegado el momento, y gracias a la modularidad que nos aporta CQRS en ese sentido, migrar 
sendos subsistemas a DBMS SQL o NoSQL optimizados para dichas tareas.

El problema de que exista un cuello de botella en el subsistema de comandos bajo un modelo sincrono, concretamente en 
el Event Source, sera difícil de solucionar en cualquier caso, y mantener la integridad en un sistema 
como este es complicado en modelos asíncronos, aunque no imposible dependiendo de las reglas de negocio
que se quieran establecer.
```

4​ . Dicen que las bases de datos relacionales no escalan bien, se me ocurre montar el proyecto
con alguna NoSQL, ¿qué me recomiendas?

```text
Te recomendaría que te lo pienses dos veces antes de elegir el stack tecnológico, en resumen:

Los DBMS SQL tradicionales se pueden optimizar mucho, además de ofrecer muchas funcionalidades NoSQL. 

Yo comenzaría este desarrollo con un DBMS SQL conocido, aprovechando también que el conocimiento de los mismos 
se encuentra muy extendido, y una vez identificados los cuellos de botella pensaría en migrar a 
DBMS especializados, que pueden o no ser NoSQL.

Intentaría centrar mis esfuerzos en diseñar una arquitectura lo suficientemente modular para
permitir luego una migración sencilla.

Aunque si lo que se quiere diseñar es un MVP o un prototipo y un DBMS NoSQL te permite ahorrar 
tiempo de desarrollo, o por el contrario, estas muy seguro (basado en datos) de que la mejor solución 
a tu problema implica usar un DBMS en particular, adelante.
```

5.​ ¿Qué tipo de métricas y servicios nos pueden ayudar a comprobar que la API y el servidor
funcionan correctamente?

```text
* A nivel de aplicación, desde los logs podemos obtener métricas que aportan información valiosa, como
numero de peticiones erróneas y exitosas, trazas de error, tiempos de respuesta, y demás datos 
de contexto que se quieran monitorear.

Lo importante aquí es no sobrecargar los logs con información que no es de interés, 
respetar los niveles de logs y no impactar en el rendimiento de la aplicación.

* A nivel de sistema, el uso de CPU, memoria, espacio en disco y procesos en ejecución 
suelen ser las métricas mas comunes.

Para visualizar las métricas en forma de log existen herramientas como Prometheus y Grafana que nos
permiten recolectar, analizar e interpretar estos datos.

Por otra parte, para monitorear los DBMS suelen existir herramientas especificas en cada caso,
que nos permitirán ver cualquier cantidad de información que nos permita identificar un problema 
en este contexto.

Finalmente, existen servicios externos capaces de monitorear nuestros servicios para ofrecer (tanto a nosotros
como a nuestros clientes), el estado actual del servicio y disponibilidad.

La mayoría de los servicios disponibles de recolección de datos y monitoreo poseen funcionalidades de alertas, 
configurarlas de manera adecuada es de vital importancia.
```