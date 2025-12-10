import pandas as pd
from io import StringIO
import uuid
from pathlib import Path

# NOTA: openpyxl ya no se necesita para la escritura de datos,
# pero openpyxl y csv ya no son necesarios para esta lógica.

def createxlsx(csv_text: str, target_dir: Path, name_issue: str) -> Path:
    """
    Convierte el texto CSV en un archivo XLSX usando Pandas y XlsxWriter,
    aplica formato, y lo guarda en el directorio especificado.

    :param csv_text: El string de datos en formato CSV (obtenido de la IA).
    :param target_dir: La ruta (Path object) donde se debe guardar el archivo XLSX.
    :param name_issue: La clave de la incidencia (ej: T1-1).
    :return: La ruta completa del archivo XLSX creado.
    """

    # --- 1. PREPARACIÓN Y PARSEO DE DATOS (CON PANDAS) ---
    
    csv_file = StringIO(csv_text.strip())
    
    # 1.1. Leer el CSV en un DataFrame. Asumimos el delimitador es ';'
    try:
        # Usamos header=0 para que la primera fila sea el encabezado
        df = pd.read_csv(csv_file, sep=';', header=0) 
    except Exception as e:
        print(f"ERROR: Falló el parseo del CSV con Pandas: {e}")
        raise e

    # --- 2. CONSTRUCCIÓN DE LA RUTA Y ESCRITURA ---
    
    # 2.1. Generar ID único y nombre de archivo
    unique_id = uuid.uuid4().hex[:8]
    nombre_base = f"CP_{name_issue}_{unique_id}.xlsx"
    ruta_guardado = target_dir / nombre_base 
    
    # 2.2. Definir el motor de escritura
    writer = pd.ExcelWriter(ruta_guardado, engine='xlsxwriter')
    
    # 2.3. Escribir los datos en el archivo (¡Rápido y eficiente!)
    # startrow=0, header=True son valores por defecto, pero se incluyen para claridad
    df.to_excel(writer, sheet_name='Casos de Prueba', index=False, startrow=0, header=True)
    
    # --- 3. APLICACIÓN DE FORMATO (CON XLSXWRITER) ---
    
    # 3.1. Obtener el objeto workbook y worksheet para aplicar formato
    workbook = writer.book
    worksheet = writer.sheets['Casos de Prueba']
    
    # 3.2. Definir el formato del encabezado
    verde_claro_hex = '#CCFFCC'
    
    # El formato se crea usando el objeto workbook de XlsxWriter
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'bg_color': verde_claro_hex,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })

    # 3.3. Aplicar formato a la fila de encabezado (fila 0 del DF, que es la fila 1 en Excel)
    for col_num, value in enumerate(df.columns.values):
        # write() es el método de XlsxWriter para escribir celdas/aplicar formato
        worksheet.write(0, col_num, value, header_format)
    
    # 3.4. Auto-ajuste de columnas (Lógica optimizada)
    for i, col in enumerate(df.columns):
        # Calculamos el ancho ideal basado en el contenido de la columna, 
        # pero limitado para evitar columnas gigantes
        max_len = max(
            df[col].astype(str).map(len).max(), # Longitud máxima del contenido
            len(col) # Longitud del encabezado
        ) or 10 # Si no hay datos, usar 10 como mínimo
        
        width = min(max_len * 1.2, 60) # Limitar el ancho máximo a 60
        worksheet.set_column(i, i, width) # Aplicar el ancho a la columna
        
    # --- 4. CIERRE Y GUARDADO ---
    
    # 4.1. Guardar el archivo (esto es manejado por el writer object)
    writer.close()
    
    print(f"Archivo '{nombre_base}' (Pandas/XlsxWriter) creado exitosamente en: {ruta_guardado}")
    
    return ruta_guardado