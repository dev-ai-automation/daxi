"""
Script para crear enlaces simbólicos y facilitar las importaciones.
Esto es útil para mantener la compatibilidad mientras se migra a una estructura más limpia.
"""
import os
import sys

def create_symlink(source, target):
    """Crear un enlace simbólico de source a target."""
    try:
        # En Windows los enlaces simbólicos requieren privilegios especiales o modo desarrollador
        if os.name == 'nt':  # Windows
            if not os.path.exists(target):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                os.system(f'mklink /J "{target}" "{source}"')
                print(f"Enlace creado: {source} -> {target}")
            else:
                print(f"El destino ya existe: {target}")
        else:  # Unix/Linux/MacOS
            if not os.path.exists(target):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                os.symlink(source, target, target_is_directory=True)
                print(f"Enlace creado: {source} -> {target}")
            else:
                print(f"El destino ya existe: {target}")
    except Exception as e:
        print(f"Error al crear enlace {source} -> {target}: {str(e)}")

def main():
    """Crear los enlaces simbólicos necesarios."""
    print("Creando enlaces simbólicos para la configuración...")
    
    # Directorios base
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Enlaces para configuración
    create_symlink(
        os.path.join(base_dir, 'app', 'infrastructure', 'config', 'config'),
        os.path.join(base_dir, 'app', 'config')
    )
    
    # Enlaces para modelos
    create_symlink(
        os.path.join(base_dir, 'app', 'domain', 'entities', 'models'),
        os.path.join(base_dir, 'app', 'models')
    )
    
    # Enlaces para webhook
    create_symlink(
        os.path.join(base_dir, 'app', 'presentation', 'webhook'),
        os.path.join(base_dir, 'app', 'webhook')
    )
    
    # Enlaces para tools
    create_symlink(
        os.path.join(base_dir, 'app', 'application', 'services', 'tools'),
        os.path.join(base_dir, 'app', 'tools')
    )
    
    # Enlaces para agents
    create_symlink(
        os.path.join(base_dir, 'app', 'infrastructure', 'external', 'agents'),
        os.path.join(base_dir, 'app', 'agents')
    )
    
    # Enlaces para services
    create_symlink(
        os.path.join(base_dir, 'app', 'infrastructure', 'persistence'),
        os.path.join(base_dir, 'app', 'services')
    )
    
    print("Proceso completado.")

if __name__ == "__main__":
    main() 