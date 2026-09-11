from pathlib import Path

def initialize_project(list_dirs: list[Path]):
# 1. Описываем структуру: какие папки и файлы должны быть
    STRUCTURE = {
        "folders": list_dirs
    }


    print("🚀 Запуск инициализации проекта...")

    # Создаем папки
    for folder_path in STRUCTURE["folders"]:
        path = Path(folder_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Создана папка: {path}")
        else:
            print(f"ℹ️ Папка уже существует: {path}")

    print("\n✅ Проект успешно готов к работе!")