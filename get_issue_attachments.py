import os
import sys
import asyncio
from pathlib import Path
import httpx # Reemplazo moderno y asíncrono de 'requests'
from requests.auth import HTTPBasicAuth # Se mantiene para la autenticación básica

# =========================================================================
# IMPORTACIÓN DE SERVICIOS
# (Asumimos que estos servicios son síncronos o no pueden ser fácilmente refactorizados a async)
# =========================================================================
try:
    # Nota: Si ProcessDOC, send_chat, createxlsx, y upload_attachment_to_jira
    # tienen llamadas a API o I/O internas que son lentas, 
    # se beneficiarían de ser refactorizadas a async/await internamente.
    # Por ahora, los ejecutaremos dentro de un threadpool con asyncio.to_thread().
    from services.process_doc import ProcessDOC
    from services.email import enviar_email
    from services.iachat import send_chat
    from services.formatxlsx import createxlsx
    from services.upload_attachment_to_jira import upload_attachment_to_jira
except ImportError as e:
    print(f"ERROR CRÍTICO de importación: {e}. Verifique la estructura de carpetas de 'services'.")
    sys.exit(1)
# =========================================================================

# --- CONFIGURACIÓN DE ENTORNO ---
JIRA_URL = os.getenv('URL_JIRA')
JIRA_USER = os.getenv('USER_JIRA')
JIRA_TOKEN = os.getenv('JIRA_TOKEN')
ISSUE_KEY = os.getenv('ISSUE_KEY')
TARGET_DIR = os.getenv('TARGET_DIR')
ATTACHMENT_ENDPOINT = f"{JIRA_URL}/rest/api/3/issue/{ISSUE_KEY}?fields=attachment"

# Lista global para almacenar los metadatos de los adjuntos de Jira (payload)
# Ahora no es estrictamente necesario que sea global si se maneja como retorno/parámetro.
# La mantendremos para coherencia, pero la pasaremos como parámetro.
attachments = [] 

# --- FUNCIONES ASÍNCRONAS ---

async def fetch_jira_attachments_metadata(client: httpx.AsyncClient) -> list:
    """Conecta a la API de Jira y obtiene los metadatos de los adjuntos."""
    global attachments # Para mantener la compatibilidad con la función de correo

    if not all([JIRA_URL, JIRA_USER, JIRA_TOKEN, ISSUE_KEY, TARGET_DIR]):
        print("ERROR CRÍTICO: Faltan credenciales o la ruta dinámica (TARGET_DIR) no se exportó.")
        sys.exit(1)
        
    print(f"1. Buscando adjuntos para: {ISSUE_KEY}")
    
    try:
        response = await client.get(ATTACHMENT_ENDPOINT, timeout=30.0)
        response.raise_for_status() 
        issue_data = response.json()
        attachments = issue_data.get('fields', {}).get('attachment', []) # Asignamos al global
        return attachments
    except httpx.RequestError as e:
        print(f"ERROR al conectar con la API de Jira: {e}")
        sys.exit(1)

async def download_single_attachment(client: httpx.AsyncClient, attachment: dict, target_dir: str) -> bool:
    filename = attachment['filename']
    content_url = attachment['content']
    filepath = Path(target_dir) / filename

    # --- FILTRO DE ARCHIVOS ---
    if "hu" not in filename.lower():
        print(f"   -> Omitiendo '{filename}': No contiene el prefijo 'hu'.")
        return False
    # ---------------------------
    
    print(f"   -> Iniciando descarga: {filename}")
    
    try:
        # [MODIFICACIÓN CLAVE]: Usamos client.get() en lugar de client.stream().
        # Esto permite que httpx gestione automáticamente la redirección 303,
        # y la respuesta final (file_response) será la que contenga el archivo real (código 200).
        file_response = await client.get(content_url, follow_redirects=True, timeout=None)
        
        # Ahora, raise_for_status() se ejecuta en la respuesta 200 OK final, o falla solo si es 4xx/5xx.
        file_response.raise_for_status()
        
        # [MODIFICACIÓN CLAVE]: Guardamos todo el contenido de una vez (file_response.content).
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(file_response.content)
            
        print(f"   -> Guardado OK: {filepath.name}")
        return True
        
    except httpx.RequestError as e:
        print(f"ERROR al descargar '{filename}': {e}")
        return False

async def process_single_file(filepath: Path) -> str | None:
    """
    Función que envuelve la lógica síncrona de procesamiento en un ThreadPoolExecutor.
    Esto permite que la ejecución I/O intensiva o lenta de ProcessDOC, send_chat,
    y createxlsx no bloquee el bucle de eventos asíncrono.
    Retorna el nombre del archivo XLSX generado o None.
    """
    
    # Esta es la CLAVE: Ejecuta la función síncrona en un hilo separado
    # y espera el resultado de forma asíncrona.
    
    def sync_processing_workflow():
        """Flujo de trabajo síncrono original para un solo archivo."""
        try:
            if "corrupto" in filepath.name:
                raise ValueError("Simulación de error: Archivo corrupto detectado")
                
            # 1. Ejecutar ProcessDOC
            file_text = ProcessDOC(str(filepath)).process()
            
            if file_text:
                # 2. Enviar a send_chat (lento por la espera a la IA)
                ai_text = send_chat(file_text, ISSUE_KEY)
                
                if ai_text:
                    target_dir_path = filepath.parent
                    # 3. Generar archivo XLSX
                    xlsx_path = createxlsx(ai_text, target_dir_path, ISSUE_KEY)
                    
                    if xlsx_path and xlsx_path.exists():
                        # 4. Subir a JIRA (lento por I/O de red)
                        success = upload_attachment_to_jira(
                            xlsx_path, 
                            ISSUE_KEY, 
                            JIRA_URL, 
                            JIRA_USER,
                            JIRA_TOKEN
                        )
                        if success:
                            print(f"  -> Flujo HU: XLSX generado y subido a JIRA para {filepath.name}.")
                            return xlsx_path.name
                        else:
                            print(f"  -> Flujo HU: Falló la subida a JIRA para {filepath.name}.")
            
            return None
        except Exception as e:
            print(f"ERROR: Falló el procesamiento del archivo {filepath.name}: {e}")
            return None

    print(f"   -> Procesando archivo (en hilo): {filepath.name}")
    # Ejecuta el flujo síncrono en un ThreadPool y espera
    return await asyncio.to_thread(sync_processing_workflow)


async def main():
    """Función principal asíncrona que coordina todas las tareas."""
    global attachments, TARGET_DIR

    TARGET_DIR = os.getenv('TARGET_DIR')
    if not TARGET_DIR:
        print("ERROR: No se puede iniciar el procesamiento. TARGET_DIR está vacío.")
        sys.exit(1)

    auth = HTTPBasicAuth(JIRA_USER, JIRA_TOKEN)
    
    # httpx.AsyncClient es crucial para manejar la concurrencia eficiente
    async with httpx.AsyncClient(auth=auth, headers={"Accept": "application/json"}) as client:
        
        # --- FASE 1: DESCARGA CONCURRENTE ---
        
        # 1. Obtener metadatos
        attachments_metadata = await fetch_jira_attachments_metadata(client)
        
        if not attachments_metadata:
            print("No se encontraron archivos adjuntos para descargar. Proceso finalizado.")
            return

        print(f"2. {len(attachments_metadata)} adjuntos encontrados. Descargando de forma CONCURRENTE en '{TARGET_DIR}'...")
        
        # 2. Iniciar tareas de descarga concurrentes
        # Creamos una lista de 'tasks' (tareas asíncronas)
        download_tasks = [
            download_single_attachment(client, attachment, TARGET_DIR) 
            for attachment in attachments_metadata
        ]
        
        # Esperamos a que todas las descargas finalicen (se ejecutan en paralelo/concurrencia)
        download_results = await asyncio.gather(*download_tasks)
        download_count = sum(download_results) # Contamos cuántas descargas fueron exitosas
        
        print(f"3. Proceso de descarga finalizado. Total descargado: {download_count}")
        
        if download_count == 0:
             print("No se descargó ningún archivo. No hay nada que procesar.")
             return
        
        # --- FASE 2: PROCESAMIENTO Y SUBIDA CONCURRENTE ---
        
        target_path = Path(TARGET_DIR)
        
        print("\n4. Iniciando el procesamiento de archivos descargados de forma CONCURRENTE...")
        
        # 1. Encontramos los archivos descargados que coincidan con el filtro 'hu'
        files_to_process = [p for p in target_path.iterdir() if p.is_file() and 'hu' in p.name.lower()]
        
        # 2. Iniciar tareas de procesamiento concurrentes (usando ThreadPool para I/O/CPU)
        process_tasks = [
            process_single_file(filepath)
            for filepath in files_to_process
        ]
        
        # Esperamos a que todos los procesos (incluyendo IA y subida) finalicen
        # Los resultados son los nombres de los archivos XLSX generados (o None)
        processed_results = await asyncio.gather(*process_tasks)
        
        # Filtramos para obtener solo los nombres de archivos generados con éxito
        archivos_procesados_xlsx = [name for name in processed_results if name is not None]

        print("5. Procesamiento de archivos adjuntos finalizado.")
        
        # --- FASE 3: NOTIFICACIÓN FINAL ---
        
        archivos_procesados = list(archivos_procesados_xlsx)

        # Añadir los nombres de los archivos originales a la lista para el correo
        # (Usamos la lista global 'attachments' poblada en la Fase 1)
        for attachment in attachments:
            if isinstance(attachment, dict) and 'filename' in attachment:
                # Solo añadimos los originales que SÍ se descargaron/procesaron (los que tienen 'hu')
                if 'hu' in attachment['filename'].lower():
                    archivos_procesados.append(attachment['filename'])

        # Eliminar duplicados si hay (p.ej., si un XLSX generado tiene el mismo nombre que un adjunto)
        archivos_procesados = list(set(archivos_procesados))
        
        # 6. LLAMADA FINAL: ENVIAR CORREO DE NOTIFICACIÓN
        if archivos_procesados_xlsx: # Solo si se generó al menos un XLSX
            print("\n6. Enviando notificación por correo electrónico.")
            # Ejecutar la función síncrona de correo en un hilo
            await asyncio.to_thread(enviar_email, archivos_procesados, ISSUE_KEY)
        else:
            print("\n6. No se enviará correo. No se generaron archivos XLSX.")


# --- PUNTO DE ENTRADA PRINCIPAL ---
if __name__ == "__main__":
    try:
        # Inicia el bucle de eventos de asyncio y ejecuta la función 'main'
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario.")
        sys.exit(1)
