import os
from pypdf import PdfReader
from openai import OpenAI

# ******************************************************************
# 1. BASE DEL PROMPT (Ahora como una plantilla sin la variable issue)
# Usamos un marcador de posición, como {issue_code}, en lugar de una f-string
# que se evaluaría de inmediato.
texto_plantilla = """
A continuación, te proporcionaré la información de una Historia de Usuario. Tu tarea es analizar
esta historia, identificar los requisitos clave, y generar una lista de Casos de Prueba (Test Cases)
que cubran las funcionalidades descritas, incluyendo escenarios positivos, negativos y de borde
cuando sea pertinente.El formato de respuesta debe ser una tabla sencilla con las siguientes columnas
para cada caso de prueba, utilizando únicamente el punto y coma (;) como delimitador para separar los campos:
ID del Caso: Debe seguir el formato numero_correlativo_{issue_code} (ej: 1_{issue_code}, 2_{issue_code}, 3_{issue_code}, etc).
Nombre/Descripción del Caso
Pasos a Seguir
Resultado Esperado.
Necesito que lo muestres como si fuera un formato CSV puro, y no escribas nada adicional ni sugerencias finales,
ni caracteres especiales, adornos de emojis, negritas o formatos de texto. Solo el resultado de manera sobria.
La información es la siguiente:

"""

# ******************************************************************
def send_chat(text_doc: str, name_issue: str) -> str:
    try:
        
        # 2. CONSTRUYE EL PROMPT: Inserta el name_issue en la plantilla
        # Usamos .format() o una f-string para reemplazar el marcador {issue_code}
        # y luego concatenamos el texto del documento.
        
        # Primero formateamos la plantilla con el valor de name_issue
        prompt_formateado = texto_plantilla.format(issue_code=name_issue)
        
        # Ahora concatenamos la información completa
        prompt_completo = prompt_formateado + text_doc
        
        # generamos la consulta a chatgpt
        client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key= os.getenv('APIKEY_OPENROUTER'),
        )

        completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "<YOUR_SITE_URL>",
            "X-Title": "<YOUR_SITE_NAME>",
        },
        extra_body={},
        model="google/gemma-3-4b-it:free",
        messages=[
                    {
                        "role": "user",
                        # Aquí pasamos el prompt completo
                        "content": prompt_completo 
                    }
                ]
        )
        # la respuesta la podemos almacenar en una variable
        csv_text = completion.choices[0].message.content
        return csv_text


    except FileNotFoundError:
        # ... (código de manejo de errores omitido por brevedad)
        return ""
