import os
import requests
import sys
from pathlib import Path 
from concurrent.futures import ThreadPoolExecutor # ¡Nuevo! Para concurrencia

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

# --- CONFIGURACIÓN ---
JIRA_URL = os.getenv('JIRA_BASE_URL')
JIRA_USER = os.getenv('JIRA_API_USER')
JIRA_TOKEN = os.getenv('JIRA_API_TOKEN')

