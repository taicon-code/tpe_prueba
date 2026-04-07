
#--------------------------------------------------------
#LISTA PARA HACER Y MEJORAR EL SISTEMA DEL TPE
#--------------------------------------------------------
# 25-03-26 'ADD AUMENTAR EL TIPO DE RESOLUCION AUMENTAR "ART. 118" y ADMINISTRATIVO (CASO DE ASCENSO, CONSIDERACION DE FRONTERA)'
# ADD EN EL TIPO DE AUTO "REHABILITACION DE DERECHOS PROFESIONALES"
# 25-03-26 "BD : FIX SACAR ID_ABOG DE LA TABLA SIM (PORQUE CADA ABOGADO NO REALIZA CADA SIM SINO RES Y AUTO)"



ADD NUMERO CORRELATIVO DEL NUMERO DE RESOLUCION EN AUTOMATICO

  
BD FIX EN LA TABLA AUTOTPE NO TODOS LOS AUTOS SON ANEXADOS AL SIM DE REPENTE SERIA AUMENTAR EN SIM UN SELECT 
        DE INGRESO DE UN SIM U OTRO Y AL LADO COLOCAR LA MOTIVACION PARA QUE SEA TRATADO EN EL TPE. 
        EJ. AMADO OSWALDO QUISPE MAMANI SU AUTO (AUTO DE VISTA 42/18 DE FECHA 19-NOV-18)
    
EN LA TABLA RES HAY QUE HABILITAR UNA SELECT PARA SIM Y OTRO ADMINISTRATIVO (POSESION TPE, ASCENSO DE GRALES)ETC.




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