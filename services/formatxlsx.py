import pandas as pd
from io import StringIO
import uuid
from pathlib import Path
import re # Necesario para la limpieza de texto

def createxlsx(csv_text: str, target_dir: Path, name_issue: str) -> Path:
    """
    Convierte el texto en formato CSV (devuelto por la IA) en un archivo XLSX 
    usando Pandas y XlsxWriter, aplica formato, y lo guarda en el directorio especificado.

    :param csv_text: El string de datos en formato CSV (obtenido de la IA).
    :param target_dir: La ruta (Path object) donde se debe guardar el archivo XLSX.
    :param name_issue: La clave de la incidencia (ej: T1-1).
    :return: La ruta completa del archivo XLSX creado.
    """

    # --- 1. LIMPIEZA Y NORMALIZACIÓN DE DATOS ---
    
    # 1.1. Limpieza Agresiva: Eliminar líneas vacías, espacios alrededor de las líneas,
    # y cualquier posible texto antes o después del bloque CSV.
    limpio_text = '\n'.join([line.strip() for line in csv_text.strip().split('\n') if line.strip()])
    
    # 1.2. Reemplazar posibles comillas dobles (") que la IA pudo haber usado para encerrar texto, 
    # ya que a menudo rompen el parser de CSV, especialmente si el delimitador es un ';'
    limpio_text = limpio_text.replace('"', '') 

    # Convertir el string limpio en un objeto de archivo en memoria para Pandas
    csv_file = StringIO(limpio_text)

    # --- 2. PARSEO DE DATOS (CON PANDAS) ---
    
    try:
        # 2.1. Leer el CSV en un DataFrame. Asumimos el delimitador es ';'
        df = pd.read_csv(
            csv_file, 
            sep=';', 
            header='infer', # Le decimos a Pandas que determine el encabezado (la primera fila)
            skipinitialspace=True, # Ignorar espacios después del delimitador (;)
            lineterminator='\n' # Asegurar la detección correcta del salto de línea
        )
        
        # Opcional: Eliminar cualquier fila que haya quedado completamente vacía
        df.dropna(how='all', inplace=True)
        
        # Si la limpieza introdujo una columna 'Unnamed: X', la eliminamos
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    except Exception as e:
        # Relanzamos el error para que el flujo principal lo capture
        print(f"ERROR: Falló el parseo del CSV con Pandas. Revise el formato del string de la IA: {e}")
        raise e # Forzar la detención aquí si el formato es irrecuperable

    # --- 3. CONSTRUCCIÓN DE LA RUTA Y ESCRITURA ---
    
    # 3.1. Generar ID único y nombre de archivo
    unique_id = uuid.uuid4().hex[:8]
    nombre_base = f"CP_{name_issue}_{unique_id}.xlsx"
    ruta_guardado = target_dir / nombre_base 
    
    # 3.2. Definir el motor de escritura (xlsxwriter es requerido para formatear)
    writer = pd.ExcelWriter(ruta_guardado, engine='xlsxwriter')
    
    # 3.3. Escribir los datos en el archivo (¡Rápido y eficiente!)
    df.to_excel(writer, sheet_name='Casos de Prueba', index=False, startrow=0, header=True)
    
    # --- 4. APLICACIÓN DE FORMATO (CON XLSXWRITER) ---
    
    workbook = writer.book
    worksheet = writer.sheets['Casos de Prueba']
    
    # 4.1. Definir el formato del encabezado
    verde_claro_hex = '#CCFFCC'
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'bg_color': verde_claro_hex,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })

    # 4.2. Aplicar formato y auto-ajuste
    for i, col in enumerate(df.columns):
        # Aplicar formato al encabezado de la columna
        worksheet.write(0, i, col, header_format)
        
        # Calcular y aplicar ancho de columna
        max_len = max(
            df[col].astype(str).map(len).max(),
            len(col)
        ) or 10 
        
        width = min(max_len * 1.2, 60)
        worksheet.set_column(i, i, width)

    # --- 5. CIERRE Y RETORNO ---
    
    writer.close()
    
    print(f"Archivo '{nombre_base}' creado exitosamente en: {ruta_guardado}")
    
    return ruta_guardado