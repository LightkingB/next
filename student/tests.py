import ctypes
import os

# Устанавливаем путь к библиотеке в переменную окружения
lib_path = os.path.expanduser('/home/lightking/Projects/sdk/Linux/x86_64/libwgssSTU.so.2')
os.environ['LD_LIBRARY_PATH'] = os.path.dirname(lib_path) + ':' + os.environ.get('LD_LIBRARY_PATH', '')

# Загружаем библиотеку
try:
    libwgss = ctypes.CDLL(lib_path)
    print(f"Библиотека {lib_path} успешно загружена.")
except OSError as e:
    print(f"Ошибка при загрузке библиотеки: {e}")
    exit(1)

# Пример вызова функции для захвата
try:
    # Используем функцию WacomGSS_Protocol_setStartCapture вместо WacomGSS_Protocol_startCapture
    status = libwgss.WacomGSS_Protocol_setStartCapture()
    print(f"Статус устройства после начала захвата: {status}")
except AttributeError as e:
    print(f"Не удалось найти функцию в библиотеке: {e}")
    exit(1)
except Exception as e:
    print(f"Произошла ошибка при вызове функции: {e}")
    exit(1)
