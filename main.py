import os
import json
import re
from typing import Dict

import requests
from dotenv import load_dotenv


class IpDetector:
    """Класс для получения IP-адреса и геолокации."""

    def __init__(self):
        self.current_ip = None
        self.geo_data = None

    def get_public_ip(self) -> str:
        """Получает внешний IP-адрес пользователя через сервис ipify."""
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
        Сервис возвращает текст вида "key: value\nkey: value".
        """
        url = f'https://ipinfo.io/{ip_address}/geo'
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Надежный парсер строкового ответа
            lines = [line.strip() for line in response.text.split('\n') if ': ' in line]
            data_dict = dict(re.split(r':\s+', line, maxsplit=1) for line in lines)
            
            self.geo_data = data_dict
            return self.geo_data
        except requests.RequestException as e:
            raise RuntimeError(f"Ошибка при запросе к ipinfo: {e}")


class JsonStorage:
    """Класс для сохранения данных в локальный JSON-файл."""

    @staticmethod
    def save_to_file(filename: str, data: Dict) -> None:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)


def main():
    load_dotenv()
    
    detector = IpDetector()
    storage = JsonStorage()

    # Имя итогового файла
    local_filename = 'ip_detector_result.json'

    try:
        ip_addr = detector.get_public_ip()
        print(f"Ваш текущий IP-адрес: {ip_addr}")

        geo_info = detector.get_geo_info(ip_addr)
        city = geo_info.get('city', 'Неизвестно')
        country = geo_info.get('country', '')
        print(f"Геолокация найдена: {city}, {country}")

        result_data = {
            "ip": ip_addr,
            "geo": geo_info
        }

        # Сохранение информации ТОЛЬКО в локальный файл
        storage.save_to_file(local_filename, result_data)
        
        abs_path = os.path.abspath(local_filename)
        print(f"[ГОТОВО] Данные успешно сохранены.")
        print(f"Путь к файлу: {abs_path}")

    except Exception as e:
        print(f"Произошла критическая ошибка: {e}")

# Обратите внимание: блока finally с удалением файла здесь НЕТ.
# Файл останется лежать рядом с .py скриптом после завершения работы.

if __name__ == '__main__':
    main()