# ════════════════════════════════════════════════════════════════════════════
#  ARCHIVO: tpe_app/widgets.py
#  
#  INSTRUCCIONES:
#  1. Crea un archivo nuevo: tpe_app/widgets.py
#  2. Copia TODO este contenido
#  3. Guarda el archivo
#  4. ¡LISTO!
# ════════════════════════════════════════════════════════════════════════════

from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe


class ResumenConOpcionesWidget(forms.Widget):
    """
    Widget que muestra:
    - Un SELECT con opciones predefinidas (lado izquierdo)
    - Un TEXTAREA para escribir personalizado (lado derecho)
    
    Cuando el usuario selecciona una opción en el SELECT,
    se copia automáticamente al TEXTAREA.
    
    El usuario puede editar el TEXTAREA después.
    
    Lo que se guarda en la BD es el contenido del TEXTAREA.
    """
    
    def __init__(self, opciones=None, attrs=None):
        """
        Parámetros:
            opciones: Lista de tuplas (valor, etiqueta)
                      Ejemplo: [('INDISCIPLINA', 'Indisciplina'), ...]
            attrs: Atributos HTML adicionales (opcional)
        """
        self.opciones = opciones or []
        super().__init__(attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """
        Renderiza el widget en HTML.
        
        Parámetros:
            name: Nombre del campo en el formulario
            value: Valor actual (lo que ya está guardado)
            attrs: Atributos HTML adicionales
            renderer: Renderer de Django (ignorado, para compatibilidad)
        """
        
        attrs = attrs or {}
        final_attrs = self.build_attrs(self.attrs, attrs)
        textarea_id = final_attrs.get('id') or f'id_{name}'
        select_id = f'{textarea_id}_predefinido'

        # Generar HTML del widget
        html = f'''
        <!-- WIDGET: Resumen con Opciones Predefinidas -->
        <div style="display: flex; gap: 20px; align-items: flex-start; font-family: Arial, sans-serif;">
            
            <!-- COLUMNA 1: SELECT con opciones predefinidas -->
            <div style="flex: 0 0 40%; min-width: 250px;">
                <label style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 13px; color: #333;">
                    📋 Opciones predefinidas:
                </label>
                
                <select id="{select_id}" 
                        style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 10.5px; background: white; cursor: pointer;">
                    <option value="" style="font-size: 10.5px;">-- Selecciona una opción --</option>
        '''
        
        # Añadir cada opción al SELECT
        for valor, etiqueta in self.opciones:
            etiqueta_escaped = escape(etiqueta)
            html += f'        <option value="{etiqueta_escaped}" style="font-size: 10.5px;">{etiqueta_escaped}</option>\n'
        
        html += f'''
                </select>
                
                <p style="font-size: 11px; color: #666; margin-top: 8px; margin-bottom: 0; line-height: 1.4;">
                    💡 Selecciona una opción para copiarla automáticamente al campo de texto.
                </p>
            </div>
            
            <!-- COLUMNA 2: TEXTAREA para escribir o editar -->
            <div style="flex: 1; min-width: 300px;">
                <label style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 13px; color: #333;">
                    ✏️ Tu resumen:
                </label>
                
                <textarea id="{textarea_id}" 
                          name="{name}" 
                          style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; font-family: Arial, sans-serif; resize: vertical; box-sizing: border-box;"
                          rows="6"
                          placeholder="Escribe aquí tu resumen o selecciona una opción predefinida">{escape(value or '')}</textarea>
                
                <p style="font-size: 11px; color: #666; margin-top: 8px; margin-bottom: 0; line-height: 1.4;">
                    💡 Puedes escribir cualquier texto personalizado. Si seleccionas una opción, aparecerá aquí.
                </p>
            </div>
        </div>
        
        <!-- JAVASCRIPT: Copiar opción al textarea cuando se selecciona -->
        <script type="text/javascript">
        (function() {{
            // Esperar a que el DOM esté listo
            var selectElement = document.getElementById('{select_id}');
            var textareaElement = document.getElementById('{textarea_id}');
            
            if (selectElement && textareaElement) {{
                // Escuchar cambios en el SELECT
                selectElement.addEventListener('change', function() {{
                    // Si se seleccionó una opción (no está vacío)
                    if (this.value) {{
                        // Copiar el valor al TEXTAREA
                        textareaElement.value = this.value;
                        // Hacer focus en el TEXTAREA para que el usuario vea el valor
                        textareaElement.focus();
                        // Seleccionar todo el texto para que pueda editarlo fácilmente
                        textareaElement.select();
                    }}
                }});
            }}
        }})();
        </script>
        '''
        
        # Retornar el HTML marcado como seguro
        return mark_safe(html)
    
    def value_from_datadict(self, data, files, name):
        """
        Extrae el valor que se guardará.
        
        Ignora el SELECT (id_*_predefinido) y solo toma el TEXTAREA (id_*)
        porque el TEXTAREA es el "source of truth".
        """
        return data.get(name, '')


# ════════════════════════════════════════════════════════════════════════════
#  FIN DE ARCHIVO
# ════════════════════════════════════════════════════════════════════════════
