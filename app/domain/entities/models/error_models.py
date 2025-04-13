"""
Modelos específicos relacionados con errores.
Define las estructuras de datos utilizadas para representar errores en la aplicación.
"""
from typing import Optional, TypedDict

class ErrorResult(TypedDict):
    """Modelo para representar un resultado de error"""
    error: str
    details: Optional[str] 