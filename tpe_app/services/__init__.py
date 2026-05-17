"""
Capa de servicios del TPE.

Cada servicio encapsula una operacion de dominio que cruza modelos y debe
ser invocable desde vistas, comandos, tests o tareas programadas sin duplicar
logica. Las vistas DELEGAN aqui en lugar de implementar.

Convenciones:
  - Funciones puras o de proceso (no clases salvo excepciones).
  - Levantan ValidationError o subclases (excepciones de dominio) cuando la
    operacion no es valida; NUNCA usan messages.error directamente.
  - Cuando emiten side-effects auditables, lo registran en logger
    'tpe_app.security' y/o tabla AccesoLog.
"""
