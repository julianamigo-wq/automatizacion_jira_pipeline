# Importar la clase ReaderFactory desde su módulo
from ifactory.factory import ReaderFactory

# --- Funciones Auxiliares ---
def get_extension(cadena: str) -> str:
    # La implementación es perfecta, se mantiene.
    ultimo_punto_indice = cadena.rfind('.')
    if ultimo_punto_indice == -1:
        return ""
    return cadena[ultimo_punto_indice + 1:]

# --- Clase Principal ---
class ProcessDOC:
    # constructor
    def __init__(self, filename: str):
        self.filename = filename

    # Funcion para conexion con factory y obtener datos extraidos
    def process(self) -> str: 
        
        file = self.filename
        ext = get_extension(file)
        
        # Inicializamos get_info a "" para garantizar el retorno en caso de fallos
        get_info = "" 

        if ext == "":
            # Archivo sin extensión: retorna "" (el valor inicial de get_info)
            print(f"[{file}] | LOG: Archivo SIN extensión. No se puede procesar.")
            return get_info 
        
        # Proceso con extensión
        try:
            # 1. Obtenemos la instancia del objeto (ReaderPDF, ReaderTXT, etc.)
            doc_reader = ReaderFactory.get_reader_object(ext)

            # 2. Llamamos al método implementado
            get_info = doc_reader.get_reading(file)
            
        except ValueError as e:
            # Manejo de error si la extensión no es soportada por la Factory.
            # get_info permanece como "", que es lo que se retornará al final.
            print(f"[{file}] | LOG: Error al crear objeto para '{ext}': {e}")
            return get_info # Ya que get_info es ""
            
        # 3. Verificamos el resultado (solo si no hubo error en la Factory)
        if get_info == "":
            # Extensión soportada, pero el lector no pudo extraer datos.
            print(f"[{file}] | LOG: No podemos extraer datos de este tipo de archivo con la extensión '{ext}'.")
            
        else:
            # Éxito: Mostramos la información extraída
            print(f"--- Obteniendo la información de {file} ({ext.upper()}) ---")
        
        # Retorna el contenido (si es exitoso) o "" (si no hay datos o hubo fallo)
        return get_info