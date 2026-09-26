import os
import json
from typing import Dict

import requests
from dotenv import load_dotenv


class IpDetector:
    """Класс для получения IP-адреса и геолокации."""

    def __init__(self):
        self.current_ip = None
        self.geo_data = None

    def get_public_ip(self) -> str:
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=10)
            response.raise_for_status()
            self.current_ip = response.json().get('ip')
            return self.current_ip
        except requests.RequestException as e:
            raise RuntimeError(f"Ошибка при получении IP-адреса: {e}")

    def get_geo_info(self, ip_address: str) -> Dict:
        """
        Получает географическую информацию по IP через API ipinfo.
        ВАЖНО: Сервис /geo возвращает чистый JSON, используем .json().
        """
        url = f'https://ipinfo.io/{ip_address}/json'
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.geo_data = response.json()
            return self.geo_data
        except requests.RequestException as e:
            raise RuntimeError(f"Ошибка при запросе к ipinfo: {e}")


class JsonStorage:
    """Класс для сохранения данных в локальный JSON-файл."""

    @staticmethod
    def save_to_file(filename: str, data: Dict) -> None:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)


class YandexDiskUploader:
    """Класс для работы с REST API Яндекс.Диска."""
    
    BASE_URL = 'https://cloud-api.yandex.net/v1/disk/resources'

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'OAuth {self.token}',
            'Accept': 'application/json',
        }

    def _ensure_folder(self, path: str) -> None:
        """Проверяет наличие папки, создает её при отсутствии."""
        endpoint = f'{self.BASE_URL}'
        params = {'path': path}
        
        # Проверяем существование
        head_response = requests.head(endpoint, headers=self.headers, params=params)
        if head_response.status_code != 200:
            # Если нет - создаем
            put_response = requests.put(endpoint, headers=self.headers, params=params)
            try:
                put_response.raise_for_status()
                print(f"[Я.Диск] Папка '{path}' создана или уже существовала.")
            except requests.exceptions.HTTPError:
                # Игнорируем ошибку 409 (папку создал кто-то другой параллельно)
                if put_response.status_code != 409:
                    put_response.raise_for_status()

    def upload_file(self, filename: str, disk_path: str) -> bool:
        """
        Загружает файл методом PUT по URL-превью.
        Возвращает True, если загрузка успешна.
        """
        try:
            # Шаг 1: Запрашиваем ссылку для загрузки
            upload_endpoint = f'{self.BASE_URL}/upload'
            params = {'path': disk_path, 'overwrite': 'true'}
            
            resp = requests.get(upload_endpoint, headers=self.headers, params=params, timeout=15)
            resp.raise_for_status()
            
            href = resp.json().get('href')
            if not href:
                raise RuntimeError("Яндекс.Диск не вернул ссылку для загрузки.")

            # Шаг 2: Отправляем сам файл
            with open(filename, 'rb') as file:
                put_resp = requests.put(href, files={'file': file}, timeout=60)
                put_resp.raise_for_status()

            print(f"[Я.Диск] Файл успешно загружен: {disk_path}")
            return True

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            text = e.response.text
            if status == 409:
                print("[Я.Диск] Ошибка 409 Conflict. Ресурс заблокирован.")
            elif status == 403:
                print("[Я.Диск] Ошибка 403 Forbidden. Проверьте токен, права доступа и квоту диска.")
            else:
                print(f"[Я.Диск] HTTP Error {status}: {text}")
            return False
        except Exception as e:
            print(f"[Я.Диск] Критическая ошибка: {e}")
            return False


def main():
    load_dotenv()
    
    token = os.getenv('YANDEX_DISK_TOKEN')
    if not token:
        print("Ошибка: Токен Я.Диска не найден в .env")
        return

    detector = IpDetector()
    storage = JsonStorage()
    uploader = YandexDiskUploader(token)

    local_filename = 'ip_detect_result.json'

    try:
        # 1. Сбор данных
        ip_addr = detector.get_public_ip()
        geo_info = detector.get_geo_info(ip_addr)
        
        city = geo_info.get('city', 'Неизвестно')
        country = geo_info.get('country', '')
        print(f"Ваш текущий IP-адрес: {ip_addr}")
        print(f"Геолокация найдена: {city}, {country}")

        result_data = {"ip": ip_addr, "geo": geo_info}

        # 2. Сохранение JSON на компьютер
        storage.save_to_file(local_filename, result_data)
        print(f"[OK] Данные сохранены в {local_filename}")

        # 3. Загрузка на Яндекс.Диск
        yandex_disk_path = '/Poligon/ip_detector_result.json'
        
        # Гарантируем наличие папки Poligon перед загрузкой
        uploader._ensure_folder('/Poligon')
        
        success = uploader.upload_file(local_filename, yandex_disk_path)

        if success:
            print("\n[ИТОГ] Курсовая работа выполнена полностью.")
        else:
            print("\n[ИТОГ] Произошла ошибка при работе с диском.")
            return

    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] {e}")

    finally:
        # Удаление локального файла согласно критерию задания
        if os.path.exists(local_filename):
            try:
                os.remove(local_filename)
                print(f"[CLEANUP] Временный файл {local_filename} удален.")
            except PermissionError:
                print(f"[CLEANUP] Не удалось удалить {local_filename}. Закройте файл.")


if __name__ == '__main__':
    main()
