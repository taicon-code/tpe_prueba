#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para buscar historial de personal militar
Uso: python buscar_historial.py --nombre "Juan" --paterno "García" --materno "López"
     python buscar_historial.py --ci "1234567"
     python buscar_historial.py --nombre "Juan" --completo
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import argparse
from tpe_app.queries.historial_personal import ConsultasHistorialPersonal


def main():
    parser = argparse.ArgumentParser(
        description='Busca el historial disciplinario de un personal militar',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Buscar por nombre
  python buscar_historial.py --nombre "Juan"

  # Buscar por apellido paterno
  python buscar_historial.py --paterno "García"

  # Buscar por nombre completo
  python buscar_historial.py --nombre "Juan" --paterno "García" --materno "López"

  # Buscar por cédula de identidad
  python buscar_historial.py --ci "1234567"

  # Ver historial completo formateado
  python buscar_historial.py --nombre "Juan" --completo

  # Ver solo estado actual
  python buscar_historial.py --nombre "Juan" --estado
        """
    )
    
    parser.add_argument('--nombre', help='Nombre del personal')
    parser.add_argument('--paterno', help='Apellido paterno')
    parser.add_argument('--materno', help='Apellido materno')
    parser.add_argument('--ci', help='Cédula de identidad')
    parser.add_argument('--completo', action='store_true', help='Mostrar historial completo')
    parser.add_argument('--estado', action='store_true', help='Mostrar solo estado actual')
    
    args = parser.parse_args()
    
    # Validar que se proporcionó al menos un parámetro de búsqueda
    if not any([args.nombre, args.paterno, args.materno, args.ci]):
        parser.print_help()
        return
    
    # Buscar personal
    personales = ConsultasHistorialPersonal.buscar_personal(
        nombre=args.nombre,
        apellido_paterno=args.paterno,
        apellido_materno=args.materno,
        ci=args.ci
    )
    
    if not personales.exists():
        print("❌ No se encontró ningún personal con esos datos.")
        return
    
    # Mostrar resultados
    if len(personales) == 1:
        # Si hay un solo resultado
        personal = personales.first()
        
        if args.completo:
            # Mostrar historial completo formateado
            historial_texto = ConsultasHistorialPersonal.obtener_historial_formateado(personal.id)
            print(historial_texto)
        
        elif args.estado:
            # Mostrar solo estado actual
            estado = ConsultasHistorialPersonal.obtener_estado_actual(personal.id)
            if estado:
                print("\n" + "="*70)
                print(f"  ESTADO ACTUAL - {estado['personal']}")
                print("="*70)
                print(f"\n  Cédula:              {estado['personal'].PM_CI}")
                print(f"  Grado:               {estado['personal'].get_PM_GRADO_display() or 'N/A'}")
                print(f"  Total Sumarios:      {estado['total_sumarios']}")
                print(f"  Total Resoluciones:  {estado['total_resoluciones']}")
                print(f"  Total Apelaciones:   {estado['total_apelaciones']}")
                print(f"  Total RAEE:          {estado['total_raees']}")
                print(f"  Estado Actual:       {estado['estado_actual']}")
                if estado['ultimo_sumario']:
                    print(f"  Último Sumario:      {estado['ultimo_sumario'].SIM_COD}")
                print("\n" + "="*70 + "\n")
        
        else:
            # Mostrar información resumida
            historial = ConsultasHistorialPersonal.obtener_historial_completo(personal.id)
            
            print("\n" + "="*70)
            print(f"  HISTORIAL DE: {personal.PM_NOMBRE} {personal.PM_PATERNO} {personal.PM_MATERNO}")
            print("="*70)
            
            print(f"\n  Cédula:              {personal.PM_CI}")
            print(f"  Grado:               {personal.get_PM_GRADO_display() or 'N/A'}")
            print(f"  Escalafón:           {personal.get_PM_ESCALAFON_display() or 'N/A'}")
            print(f"  Arma:                {personal.get_PM_ARMA_display() or 'N/A'}")
            print(f"  Estado:              {personal.get_PM_ESTADO_display()}")
            
            print(f"\n  SUMARIOS:            {historial['sumarios'].count()}")
            for sim in historial['sumarios']:
                print(f"    • [{sim.SIM_COD}] {sim.SIM_TIPO} - {sim.SIM_RESUM[:50]}...")
            
            print(f"\n  RESOLUCIONES:        {historial['resoluciones'].count()}")
            for res in historial['resoluciones']:
                print(f"    • [{res.RES_NUM}] {res.get_RES_TIPO_display()}")
            
            if historial['segundas_resoluciones']:
                print(f"\n  2NDAS RESOLUCIONES:  {historial['segundas_resoluciones'].count()}")
                for rr in historial['segundas_resoluciones']:
                    print(f"    • [{rr.RR_NUM}] Fecha: {rr.RR_FEC}")
            
            if historial['recursos_apelacion']:
                print(f"\n  APELACIONES:         {historial['recursos_apelacion'].count()}")
                for rap in historial['recursos_apelacion']:
                    print(f"    • [{rap.RAP_NUM}] Fecha: {rap.RAP_FEC}")
            
            if historial['raees']:
                print(f"\n  RAEES:               {historial['raees'].count()}")
                for raee in historial['raees']:
                    print(f"    • [{raee.RAE_NUM}] Fecha: {raee.RAE_FEC}")
            
            if historial['autos_tpe']:
                print(f"\n  AUTOS TPE:           {historial['autos_tpe'].count()}")
                for auto in historial['autos_tpe']:
                    print(f"    • [{auto.TPE_NUM}] {auto.get_TPE_TIPO_display()}")
            
            if historial['autos_tsp']:
                print(f"\n  AUTOS TSP:           {historial['autos_tsp'].count()}")
                for auto in historial['autos_tsp']:
                    print(f"    • [{auto.TSP_NUM}] {auto.get_TSP_TIPO_display()}")
            
            print("\n" + "="*70)
            print("  (Usa --completo para ver historial detallado)")
            print("  (Usa --estado para ver solo el estado actual)")
            print("="*70 + "\n")
    
    else:
        # Si hay múltiples resultados
        print(f"\n✓ Se encontraron {len(personales)} resultados:\n")
        
        for i, pm in enumerate(personales, 1):
            print(f"  {i}. {pm.PM_NOMBRE} {pm.PM_PATERNO} {pm.PM_MATERNO}")
            print(f"     Cédula: {pm.PM_CI}")
            print(f"     Grado: {pm.get_PM_GRADO_display() or 'N/A'}")
            
            # Contar sumarios
            from tpe_app.models import SIM
            sumarios = SIM.objects.filter(pm_sim__ID_PM__id=pm.id).distinct().count()
            print(f"     Sumarios: {sumarios}")
            print()
        
        print("  Intenta ser más específico en tu búsqueda para obtener un único resultado.")


if __name__ == '__main__':
    main()
