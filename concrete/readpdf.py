from ifactory.interface import ReadingInterface
from pypdf import PdfReader
from pathlib import Path

class ReadPDF(ReadingInterface):
   
    def get_reading(self, file: str) -> str:
        """
        Lee el contenido de texto de todas las páginas de un archivo PDF.

        :param file: La ruta (string) al archivo PDF.
        :return: Un string que contiene el texto concatenado de todas las páginas.
        """
        pdf_path = Path(file)
        
        # Verifica si el archivo existe
        if not pdf_path.is_file():
            return f"Error: El archivo no fue encontrado en la ruta {file}"

        try:
            # Crear un objeto PdfReader
            reader = PdfReader(pdf_path)
            text = ""
            
            # Iterar sobre todas las páginas
            for page in reader.pages:
                # Extraer el texto de la página y concatenarlo
                text += page.extract_text(extraction_mode="layout") + "\n"  # Agregamos un salto de línea entre páginas
            
            return text
            
        except Exception as e:
            # Manejo de errores durante la lectura (ej. archivo corrupto, permisos)
            return f"Error al leer el archivo PDF {file}: {e}"