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
        api_key= os.getenv('OPENROUTER_APIKEY'),
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
        # return csv_text
        return """ID_CP;Descripcion del Caso;Pasos a Seguir;Resultado Esperado
PP_001;Verificar la opción "Guardar tarjeta para futuras compras" durante el checkout.;1. Iniciar un proceso de compra y llegar a la página de pago.;2. Seleccionar "Tarjeta de Crédito/Débito" como método de pago.;3. Buscar la casilla de verificación para guardar la tarjeta.;La opción "Guardar tarjeta para futuras compras" o similar debe ser visible y seleccionable.
PP_002;Guardar exitosamente una tarjeta de crédito/débito para futuras compras.;1. Seguir los pasos del CP_001, ingresar los datos de una tarjeta válida.;2. Marcar la casilla "Guardar tarjeta para futuras compras".;3. Completar el pago.;4. El sistema debe confirmar el pago y mostrar un mensaje (si aplica) de que la tarjeta ha sido almacenada de forma segura.;La tarjeta debe ser procesada para el pago y almacenada de forma segura. El usuario debe recibir una confirmación de almacenamiento y pago.
PP_003;Verificar el mensaje de confirmación de almacenamiento seguro de la tarjeta.;1. Realizar los pasos del CP_002.;2. Observar la interfaz inmediatamente después de marcar la opción o al confirmar el pago.;El sistema debe mostrar un mensaje claro que confirme que la información de la tarjeta se almacenará de forma **segura**.
PP_004;Verificar la visualización de la tarjeta guardada en la siguiente compra.;1. Realizar una primera compra guardando la tarjeta (CP_002).;2. Cerrar la sesión y volver a iniciarla (si aplica) o esperar un tiempo.;3. Iniciar un nuevo proceso de compra y llegar a la página de pago.;La tarjeta guardada debe aparecer como una opción de pago destacada o por defecto, mostrando solo los últimos 4 dígitos y el tipo de tarjeta (ej., "Visa terminada en 1234").
PP_005;Pagar con una tarjeta guardada sin reintroducir los datos completos.;1. Seguir los pasos del CP_004.;2. Seleccionar la tarjeta guardada.;3. Completar la compra (puede requerir reintroducir el CVC/CVV por seguridad).;El pago debe completarse exitosamente utilizando la tarjeta guardada, sin requerir la reintroducción de los dígitos principales de la tarjeta.
PP_006;Acceder a la sección de gestión de tarjetas guardadas en el perfil de usuario.;1. Navegar a la sección del perfil o configuración de la cuenta del usuario.;2. Buscar la opción para gestionar métodos de pago o tarjetas guardadas.;Debe existir una sección accesible dentro del perfil del usuario que permita ver y gestionar (eliminar/modificar) las tarjetas guardadas.
PP_007;Eliminar una tarjeta guardada desde la sección de gestión de perfil.;1. Acceder a la sección de gestión de tarjetas (CP_006).;2. Seleccionar la opción de "Eliminar" o "Remover" para una de las tarjetas guardadas.;3. Confirmar la eliminación (si se solicita).;La tarjeta seleccionada debe ser eliminada permanentemente de los métodos de pago guardados y ya no debe aparecer como opción en futuras compras.
PP_008;Verificar el comportamiento al no guardar la tarjeta durante la compra.;1. Iniciar un proceso de compra, ingresar los datos de la tarjeta.;2. **No** marcar la casilla "Guardar tarjeta para futuras compras".;3. Completar el pago.;4. Iniciar una nueva compra y llegar a la página de pago.;La tarjeta utilizada en la compra anterior **no** debe aparecer como una opción guardada en la nueva compra."""

    except FileNotFoundError:
        # ... (código de manejo de errores omitido por brevedad)
        return ""
