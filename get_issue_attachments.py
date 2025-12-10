import os
import requests
import sys
from pathlib import Path 
from requests.auth import HTTPBasicAuth

# =========================================================================
# IMPORTACIÓN DE SERVICIOS
# =========================================================================
try:
    from services.process_doc import ProcessDOC
    from services.email import enviar_email
    from services.iachat import send_chat
    from services.formatxlsx import createxlsx
    from services.upload_attachment_to_jira import upload_attachment_to_jira
except ImportError as e:
    print(f"ERROR CRÍTICO de importación: {e}. Verifique la estructura de carpetas de 'services'.")
    sys.exit(1)
# =========================================================================

# --- CONFIGURACIÓN DE ENTORNO (Variables leídas del .yml) ---
JIRA_URL = os.getenv('URL_JIRA')
JIRA_USER = os.getenv('USER_JIRA')
JIRA_TOKEN = os.getenv('JIRA_TOKEN')
ISSUE_KEY = os.getenv('ISSUE_KEY')       # Clave de la incidencia (ej: T1-1)
TARGET_DIR = os.getenv('TARGET_DIR')     # Ruta de la carpeta dinámica (ej: CP/T1-1)

# Lista global para almacenar los metadatos de los adjuntos de Jira (payload)
attachments = [] 

# Define el endpoint de la API de Jira
ATTACHMENT_ENDPOINT = f"{JIRA_URL}/rest/api/3/issue/{ISSUE_KEY}?fields=attachment"

def download_attachments():
    """Conecta a la API de Jira y descarga los adjuntos en TARGET_DIR."""
    
    # CRÍTICO: Permite modificar la variable global 'attachments'
    global attachments 
    
    # 1. Verificación básica
    if not all([JIRA_URL, JIRA_USER, JIRA_TOKEN, ISSUE_KEY, TARGET_DIR]):
        print("ERROR CRÍTICO: Faltan credenciales o la ruta dinámica (TARGET_DIR) no se exportó.")
        sys.exit(1)
        
    # 2. Autenticación y solicitud de metadatos
    auth = HTTPBasicAuth(JIRA_USER, JIRA_TOKEN)
    headers = {"Accept": "application/json"}
    
    try:
        print(f"1. Buscando adjuntos para: {ISSUE_KEY}")
        response = requests.get(ATTACHMENT_ENDPOINT, headers=headers, auth=auth)
        response.raise_for_status() 
        issue_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR al conectar con la API de Jira: {e}")
        sys.exit(1)

    # El resultado de la API se asigna a la lista GLOBAL 'attachments'
    attachments = issue_data.get('fields', {}).get('attachment', [])
    download_count = 0

    if not attachments:
        print("No se encontraron archivos adjuntos para descargar.")
        return

    print(f"2. {len(attachments)} adjuntos encontrados. Descargando en '{TARGET_DIR}'...")
    

    # 3. Descargar cada archivo
    for attachment in attachments:
        filename = attachment['filename']
        content_url = attachment['content'] 

        # --- FILTRO DE ARCHIVOS ---
        if "hu" not in filename.lower():
            print(f"   -> Omitiendo '{filename}': No contiene el prefijo 'hu'.")
            continue 
        # ---------------------------
        
        filepath = Path(TARGET_DIR) / filename 
        
        try:
            print(f"   -> Descargando: {filename}")
            file_response = requests.get(content_url, auth=auth, stream=True)
            file_response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            download_count += 1
            print(f"   -> Guardado OK: {filepath}")

        except requests.exceptions.RequestException as e:
            print(f"ERROR al descargar '{filename}': {e}")
            continue 

    print(f"3. Proceso de descarga finalizado. Total descargado: {download_count}")


def process_downloaded_files(target_dir: str):
    """
    Itera sobre los archivos descargados y aplica la lógica de procesamiento.
    """
    # CRÍTICO: Se necesita acceder a estas variables globales para la subida a JIRA
    global JIRA_URL, JIRA_USER, JIRA_TOKEN, ISSUE_KEY
    
    target_path = Path(target_dir)
    if not target_path.is_dir():
        print(f"ADVERTENCIA: La ruta {target_dir} no es un directorio válido.")
        return

    # LISTA PARA RECOLECTAR LOS NOMBRES DE ARCHIVOS PROCESADOS/CREADOS
    archivos_procesados = [] 
    
    # 4. Iniciando el procesamiento
    print("\n4. Iniciando el procesamiento de archivos descargados...")
    
    # Iteramos sobre todos los archivos dentro de la carpeta dinámica
    for filepath in target_path.iterdir():
        if filepath.is_file():
            print(f"   -> Procesando archivo: {filepath.name}")
            
            try: # <- Bloque TRY cubre todo el procesamiento del archivo
                # 1. Ejecutar ProcessDOC (Ahora dentro del try para manejo de errores)
                file_text = ProcessDOC(str(filepath)).process()
                
                # 2. Enviar a send_chat (dentro creamos el prompt y concatenamos file_text)
                if(file_text):
                    ai_text = send_chat(file_text, ISSUE_KEY)
                    if ai_text:
                        target_dir_path = Path(target_dir) # Conversión a Path
                        
                        # 3. Generar archivo XLSX y CAPTURAR LA RUTA
                        xlsx_path = createxlsx(ai_text, target_dir_path, ISSUE_KEY)
                        
                        # 4. Verificar si el XLSX se creó y subirlo a JIRA
                        if xlsx_path and xlsx_path.exists():
                            
                            # AÑADIR EL NOMBRE DEL NUEVO ARCHIVO A LA LISTA DE NOTIFICACIÓN
                            archivos_procesados.append(xlsx_path.name)
                            
                            success = upload_attachment_to_jira(
                                xlsx_path, 
                                ISSUE_KEY, 
                                JIRA_URL, 
                                JIRA_USER,
                                JIRA_TOKEN
                            )
                            if success:
                                print(f"  -> Flujo HU: XLSX generado y subido a JIRA para {filepath.name}.")
                            else:
                                print(f"  -> Flujo HU: Falló la subida a JIRA para {filepath.name}.")
                        else:
                            print(f"  -> Flujo HU: Falló la creación del XLSX para {filepath.name}.")

                    else:
                        print(f"  - Flujo HU: Falló la respuesta de IA para {filepath.name}.")

                else:
                    print(f"  - Flujo HU: Falló la extracción de texto para {filepath.name}.")

            except Exception as e:
                print(f"ERROR: Falló el procesamiento del archivo {filepath.name}: {e}")
                continue 

    print("5. Procesamiento de archivos adjuntos finalizado.")
    
    # agregar a la lista los archivos de la tarjeta (los originales, que se cargaron en download_attachments)
    # Esto asegura que el correo liste ORIGINALES + GENERADOS (XLSX)
    for attachment in attachments:
        if isinstance(attachment, dict) and 'filename' in attachment:
            archivos_procesados.append(attachment['filename'])

    # 6. LLAMADA FINAL: ENVIAR CORREO DE NOTIFICACIÓN
    if archivos_procesados:
        print("\n6. Enviando notificación por correo electrónico.")
        enviar_email(archivos_procesados, ISSUE_KEY)
    else:
        print("\n6. No se enviará correo. No se generaron archivos XLSX.")


# --- PUNTO DE ENTRADA PRINCIPAL ---
if __name__ == "__main__":
    
    # 1. Aseguramos que las variables de entorno se lean
    # (Ya se leyeron globalmente, pero re-confirmamos TARGET_DIR si es necesario)
    TARGET_DIR = os.getenv('TARGET_DIR')
    
    # 2. Descargamos todos los archivos (función que ya creamos)
    download_attachments()
    
    # 3. Procesamos los archivos descargados
    if TARGET_DIR:
        process_downloaded_files(TARGET_DIR)
    else:
        print("ERROR: No se puede iniciar el procesamiento. TARGET_DIR está vacío.")