import requests
import os
from pathlib import Path
import sys

# La función debe recibir todos los parámetros necesarios del script principal.
def upload_attachment_to_jira(issue_key: str, file_path: str, jira_url: str, jira_user: str, jira_token: str) -> bool:
    """
    Sube un archivo a un ticket específico de Jira como un nuevo adjunto.

    Args:
        issue_key (str): La clave del ticket de Jira (ej: 'PROYECTO-123').
        file_path (str): La ruta completa del archivo local a subir.
        jira_url (str): URL base de la instancia de Jira (ej: https://tuempresa.atlassian.net).
        jira_user (str): Correo electrónico del usuario de la API.
        jira_token (str): Token de API de Atlassian.

    Returns:
        bool: True si la subida fue exitosa, False en caso contrario.
    """
    
    # 1. Construir la URL del endpoint de adjuntos
    # Endpoint: /rest/api/3/issue/{issueIdOrKey}/attachments
    api_url = f"{jira_url}/rest/api/3/issue/{issue_key}/attachments"
    
    # 2. Configurar la autenticación
    auth = (jira_user, jira_token)
    
    # 3. Configurar los encabezados (Headers)
    # Jira requiere el encabezado 'X-Atlassian-Token: no-check' para adjuntar archivos.
    headers = {
        'X-Atlassian-Token': 'no-check'
    }

    # 4. Leer el archivo y preparar la carga útil (Payload)
    try:
        # Abrimos el archivo en modo binario
        with open(file_path, 'rb') as f:
            file_name = Path(file_path).name
            # El cuerpo de la petición debe ser 'files' para el tipo de contenido multipart/form-data
            files = {
                'file': (file_name, f)
            }
            
            # 5. Realizar la petición POST
            response = requests.post(
                api_url,
                auth=auth,
                headers=headers,
                files=files
            )
            
            # 6. Verificar el estado de la respuesta
            response.raise_for_status() # Lanza una excepción para códigos de error HTTP (4xx o 5xx)
            
            print(f"  -> INFO: Adjunto '{file_name}' subido correctamente a {issue_key}.")
            return True

    except requests.exceptions.HTTPError as e:
        print(f"  -> ERROR HTTP al subir adjunto a Jira. Código: {e.response.status_code}")
        print(f"  -> Respuesta de Jira: {e.response.text}")
        return False
        
    except FileNotFoundError:
        print(f"  -> ERROR: Archivo no encontrado en la ruta: {file_path}")
        return False
        
    except Exception as e:
        print(f"  -> ERROR inesperado durante la subida: {e}")
        return False
        
# -------------------------------------------------------------------------------------------------
