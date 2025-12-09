from ifactory.interface import ReadingInterface
from pathlib import Path
from docx import Document # Importamos la clase Document de la librería python-docx
from docx.opc.exceptions import PackageNotFoundError # Importamos el error específico para archivos no encontrados o corruptos

class ReadDOCX(ReadingInterface):
    
    def get_reading(self, file: str) -> str:
        """
        Lee el contenido de texto de todos los párrafos de un archivo DOCX.

        :param file: La ruta (string) al archivo DOCX.
        :return: Un string que contiene el texto concatenado de todos los párrafos.
        """
        docx_path = Path(file)
        
        # 1. Validación de Ruta
        # Verifica si el archivo existe
        if not docx_path.is_file():
            return f"Error: El archivo no fue encontrado en la ruta {file}"

        try:
            # 2. Lectura del Contenido
            # Abrir el documento DOCX
            document = Document(docx_path)
            text = []
            
            # Iterar sobre todos los párrafos del documento
            for paragraph in document.paragraphs:
                # Añadir el texto del párrafo a la lista
                text.append(paragraph.text)
                
            # Unir todos los textos de los párrafos con un salto de línea
            return "\n".join(text)
            
        except PackageNotFoundError:
            # Manejo de errores específicos de docx (ej. archivo corrupto o no es un DOCX válido)
            return f"Error al leer el archivo DOCX {file}: El archivo no es un documento de Word válido o está corrupto."
            
        except Exception as e:
            # 3. Manejo de Errores (para permisos u otros problemas no capturados antes)
            return f"Error inesperado al leer el archivo DOCX {file}: {e}"