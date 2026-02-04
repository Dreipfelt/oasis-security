import os
from pathlib import Path

def export_structure(root_path, output_file, max_depth=5, ignore=['__pycache__', '.git', 'venv']):
    root = Path(root_path)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Structure du projet: {root.name}\n\n")
        
        def walk(path, prefix="", depth=0):
            if depth > max_depth:
                return
            items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            for i, item in enumerate(items):
                if any(ign in item.name for ign in ignore) or item.name.startswith('.'):
                    continue
                connector = "├── " if i < len(items)-1 else "└── "
                f.write(f"{prefix}{connector}{item.name}\n")
                if item.is_dir():
                    extension = "│   " if i < len(items)-1 else "    "
                    walk(item, prefix + extension, depth + 1)
        
        walk(root)

if __name__ == "__main__":
    export_structure('.', 'structure_projet.txt')
