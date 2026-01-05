import os
import winreg
from pathlib import Path
import getpass
import shutil

# -------------------- Проверка mutagen --------------------

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
    can_set_meta = True
except ImportError:
    print("[INFO] Библиотека 'mutagen' не найдена. Попытка установки через python -m pip...")
    import sys
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mutagen"])
        from mutagen.easyid3 import EasyID3
        from mutagen.mp3 import MP3
        can_set_meta = True
        print("[OK] mutagen установлен и готов к использованию")
    except Exception as e:
        print(f"[WARN] Не удалось установить mutagen автоматически: {e}")
        can_set_meta = False

# -------------------- Настройки --------------------
working_directory = Path.cwd()
copy_to = working_directory / "MusicParserOSU"
copy_to.mkdir(exist_ok=True)

err_ = []
not_err = []

# -------------------- Функции поиска osu! --------------------

def get_osu_from_registry():
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"osustable.File.osz2\DefaultIcon") as key:
            value, _ = winreg.QueryValueEx(key, "")
            exe_path = value.split(",")[0].strip('"')
            exe_path = Path(exe_path)
            if exe_path.exists():
                return exe_path.parent
    except FileNotFoundError:
        pass
    return None

def get_osu_from_common_dirs():
    username = getpass.getuser()
    candidates = [
        Path(f"C:/Users/{username}/AppData/Local/osu!"),
        Path("C:/Program Files/osu!"),
        Path("C:/Program Files (x86)/osu!"),
    ]
    for path in candidates:
        if (path / "osu!.exe").exists():
            return path
    return None

def request_osu_from_user():
    while True:
        path = input("Введите полный путь к папке osu!: ").strip('" ')
        folder = Path(path)
        if (folder / "osu!.exe").exists():
            return folder
        print("[ERROR] В указанной папке нет osu!.exe\n")

def get_osu_folder():
    print("Поиск osu! через реестр...")
    osu_path = get_osu_from_registry()
    if osu_path:
        print(f"[OK] Найдено через реестр: {osu_path}")
        return osu_path
    print("Поиск в стандартных директориях...")
    osu_path = get_osu_from_common_dirs()
    if osu_path:
        print(f"[OK] Найдено в стандартной директории: {osu_path}")
        return osu_path
    print("Автоматический поиск не удался.")
    return request_osu_from_user()

def get_audio_filename(osu_file: Path) -> str:
    with osu_file.open("r", encoding="utf-8") as file:
        for line in file:
            if line.startswith("AudioFilename:"):
                return line.split(":", 1)[1].strip()
    raise ValueError(f"[ERROR] AudioFilename not found in {osu_file}")

def process_folder(folder: Path):
    try:
        if folder.name.lower() == "failed":
            return
        osu_files = list(folder.glob("*.osu"))
        if not osu_files:
            raise FileNotFoundError(f"[ERROR] Нет .osu файлов в {folder}")
        audio_filename = get_audio_filename(osu_files[0])
        audio_file = folder / audio_filename
        if not audio_file.exists():
            raise FileNotFoundError(f"[ERROR] Аудиофайл {audio_filename} не найден в {folder}")
        parts = folder.name.split(" ", 1)
        artist_title = parts[1] if len(parts) == 2 else audio_file.stem
        if " - " in artist_title:
            artist, title = artist_title.split(" - ", 1)
        else:
            artist, title = "Unknown", artist_title
        f_name = f"{artist.strip()} - {title.strip()}{audio_file.suffix}"
        f_name = f_name.replace("/", "_").replace("\\", "_")
        target_file = copy_to / f_name
        shutil.copyfile(audio_file, target_file)
        if can_set_meta and target_file.suffix.lower() == ".mp3":
            try:
                audio = MP3(target_file, ID3=EasyID3)
                audio["artist"] = artist.strip()
                audio["title"] = title.strip()
                audio.save()
            except Exception as e:
                print(f"[WARN] Не удалось установить теги для {f_name}: {e}")

        print(f"[OK] Скопировано: {f_name}")
        not_err.append(folder)

    except Exception as e:
        print(e)
        err_.append(folder)

# -------------------- Главная логика --------------------

if __name__ == "__main__":
    osu_folder = get_osu_folder()
    print(f"\nИспользуется папка osu!: {osu_folder}")

    songs_folder = osu_folder / "Songs"
    if not songs_folder.exists():
        raise FileNotFoundError("[ERROR] Папка Songs не найдена!")

    print(f"Папка Songs: {songs_folder}\n")

    for folder in songs_folder.iterdir():
        if folder.is_dir():
            process_folder(folder)

    print("\n===== Результаты =====")
    print(f"Успешно обработано: {len(not_err)}")
    print(f"С ошибками: {len(err_)}")
