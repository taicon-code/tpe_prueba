
#--------------------------------------------------------
#LISTA PARA HACER Y MEJORAR EL SISTEMA DEL TPE
#--------------------------------------------------------
# 25-03-26 'ADD AUMENTAR EL TIPO DE RESOLUCION AUMENTAR "ART. 118" y ADMINISTRATIVO (CASO DE ASCENSO, CONSIDERACION DE FRONTERA)'
# ADD EN EL TIPO DE AUTO "REHABILITACION DE DERECHOS PROFESIONALES"
# 25-03-26 "BD : FIX SACAR ID_ABOG DE LA TABLA SIM (PORQUE CADA ABOGADO NO REALIZA CADA SIM SINO RES Y AUTO)"




  



1. pm.csv          (Personal Militar - sin dependencias)
2. abog.csv        (Abogados - sin dependencias)
3. sim.csv         (Sumarios - depende de nadie)
4. pm_sim.csv      (Relación PM-SIM - depende de pm y sim)
5. abog_sim.csv    (Relación Abogado-SIM - depende de abog y sim)
6. agenda.csv      (Agendas - depende de sim)
7. res.csv         (Resoluciones - depende de sim, abog, agenda)
8. rr.csv          (Recursos RR - depende de res, sim, abog, agenda)
9. dictamen.csv    (Dictámenes - depende de abog, agenda)
10. rap.csv        (Apelaciones - depende de rr, sim)
11. autotsp.csv    (Autos TSP - depende de sim)
12. autotpe.csv    (Autos TPE - depende de sim, abog, agenda)
13. raee.csv       (Recursos RAEE - depende de rap, sim)
14. documentos_adjuntos.csv (Documentos - depende de múltiples tablas)


Modelo	Campo Python (PK)	Columna BD
PM	pm_id	                        id
ABOG	abog_id	                        id
SIM	id	                        id


Relación	Campo Python (FK)	Columna BD	        Consulta Django
SIM	                pm	        pm_id	                        .filter(pm_id=...)
RES	                sim	        sim_id	                        .filter(sim_id=...)
RES	                abog	        abog_id	                        .filter(abog_id=...)




me encanta todo ahora pasemos al siguiente nivel para el abogado. 
formulario completo de asignacion de sumario (debe aparecerle sus sumarios que le fueron asignados) 
generar un numero de dictamen (apretando solo un boton y el sistema que le otorgue un numero ej: 05/26)
a la conclusion del dictamen se debe dos opciones es decir el autope y res nace del dictamne. tomando en cuenta que para archivos pasados no requiera estos datos (como debe estar en la estructura de la base de datos) 
posterior a la agenda el abogado debe generar una resolucion o/y auto que tambien debe ser generado aprentando un boton y el sistema se encarga de guardar el numero de resolucion ej 52/26. Crear Primera Resolución (RES) - ABOGADO
Crear Segunda Resolución (RR) - ABOGADO
Crear Auto TPE (AUTOTPE) - ABOGADO
se me ocurre una idea que cuando ingrese


aumentar especialidad en el ingreso de Personal militar
aumentar el arma de logistica en armas
borrar el botin dictamen de la parte superior de abogado
al crear dictamen no debe aparecer el nombre del abogado sino 
el nombre a quien se le esta sancionando entonces 
en la parte de crear dictamen debe aparecer el nombre de los implicados

en el abogado dashboard en el panel de sumarios asignados
que se vea todos lo militares empleados