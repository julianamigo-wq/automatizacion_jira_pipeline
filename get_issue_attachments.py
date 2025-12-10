import os
import requests
import sys
from pathlib import Path 
from requests.auth import HTTPBasicAuth # <--- AÑADIDO: Necesario para la autenticación

# =========================================================================
try:
    from services.process_doc import ProcessDOC
    from services.email import enviar_email
    from services.iachat import send_chat
    from services.formatxlsx import createxlsx
    from services.upload_attachment_to_jira import upload_attachment_to_jira
except ImportError as e:
    # Mantener el manejo de errores simple y claro
    print(f"ERROR CRÍTICO de importación: {e}. Verifique la estructura de carpetas de 'services'.")
    sys.exit(1) # Forzar la salida si falla 
# =========================================================================

# --- CONFIGURACIÓN DE ENTORNO ---
# Lee las variables inyectadas desde el .yml
JIRA_URL = os.getenv('URL_JIRA')
JIRA_USER = os.getenv('USER_JIRA')
JIRA_TOKEN = os.getenv('JIRA_TOKEN')
ISSUE_KEY = os.getenv('ISSUE_KEY')        # Clave de la incidencia (ej: PROY-123)
TARGET_DIR = os.getenv('TARGET_DIR')    # Ruta de la carpeta dinámica (ej: CP/PROY-123)

# Define el endpoint de la API de Jira
ATTACHMENT_ENDPOINT = f"{JIRA_URL}/rest/api/3/issue/{ISSUE_KEY}?fields=attachment"

def download_attachments():
    """Conecta a la API de Jira y descarga los adjuntos en TARGET_DIR."""
    
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
        response.raise_for_status() # Lanza un error para códigos 4xx/5xx
        issue_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR al conectar con la API de Jira: {e}")
        sys.exit(1)

    # attachments contiene la cantidad de adjuntos en la tarjeta
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

        # --- MODIFICACIÓN DE FILTRO INICIA AQUÍ ---
        # Convertimos el nombre del archivo a minúsculas para la comprobación
        # Esto permite que 'Hu', 'HU', o 'hu' sean válidos.
        if "hu" not in filename.lower():
            print(f"   -> Omitiendo '{filename}': No contiene el prefijo 'hu'.")
            continue # Salta al siguiente archivo en el bucle
        # --- MODIFICACIÓN DE FILTRO TERMINA AQUÍ ---
        
        filepath = Path(TARGET_DIR) / filename # Crea la ruta completa: TARGET_DIR/nombre_archivo
        
        try:
            print(f"   -> Descargando: {filename}")
            file_response = requests.get(content_url, auth=auth, stream=True)
            file_response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            download_count += 1
            print(f"   -> Guardado OK: {filepath}")

        except requests.exceptions.RequestException as e:
            print(f"ERROR al descargar '{filename}': {e}")
            continue # Pasa al siguiente archivo

    print(f"3. Proceso de descarga finalizado. Total descargado: {download_count}")


def process_downloaded_files(target_dir: str):
    """
    Itera sobre los archivos descargados y aplica la lógica de procesamiento.
    """
    target_path = Path(target_dir)
    if not target_path.is_dir():
        print(f"ADVERTENCIA: La ruta {target_dir} no es un directorio válido.")
        return

    print("\n4. Iniciando el procesamiento de archivos descargados...")
    
    # Iteramos sobre todos los archivos dentro de la carpeta dinámica
    for filepath in target_path.iterdir():
        if filepath.is_file():
            print(f"   -> Procesando archivo: {filepath.name}")
            
            try:
                # 1. Ejecutar ProcessDOC
                # Utilizamos str(filepath) para asegurar que ProcessDOC reciba la ruta como cadena
                file_text = ProcessDOC(str(filepath)).process()
                
                # 2. Imprimimos una parte del resultado para verificación (Opcional)
                print(f"      - Extracción exitosa de archivo {file_text} en el directorio {target_dir}.")
                
                # 3. Enviar a send_chat (dentro creamos el prompt y concatenamos file_text)
                if(file_text):
                    ai_text = send_chat(file_text, ISSUE_KEY)
                    # Validamos ia_text
                    if ai_text:
                        # Generar archivo XLSX
                        createxlsx(ai_text, target_dir, ISSUE_KEY)
                        print(f"  - Flujo HU Terminado: {filepath.name}")
                    else:
                        print(f"  - Flujo HU: Falló la respuesta de IA para {filepath.name}.")

                else:
                    print(f"  - Flujo HU: Falló la extracción de texto para {filepath}.")
                
            except Exception as e:
                print(f"ERROR: Falló el procesamiento del archivo {filepath.name}: {e}")
                # Podemos continuar con el siguiente archivo o detener la ejecución
                continue 

    print("5. Procesamiento de archivos adjuntos finalizado.")

# --- PUNTO DE ENTRADA PRINCIPAL ---
if __name__ == "__main__":
    
    # 1. Aseguramos que las variables de entorno se lean (si es que no están en el top-level)
    TARGET_DIR = os.getenv('TARGET_DIR')
    
    # 2. Descargamos todos los archivos (función que ya creamos)
    download_attachments()
    
    # 3. Procesamos los archivos descargados
    if TARGET_DIR:
        process_downloaded_files(TARGET_DIR)
    else:
        print("ERROR: No se puede iniciar el procesamiento. TARGET_DIR está vacío.")