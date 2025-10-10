# logic.py - SteamF12TooL Arka Plan İşlemleri

import os
import time
import random
from PIL import Image
import winreg
import requests
import json
import re

CONFIG_FILE = 'config.json'

# --- AYAR YÖNETİMİ (CONFIGURATION) ---

def load_settings():
    """config.json dosyasından ayarları yükler."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return {'language': 'en', 'theme': 'Dark', 'last_profile': None}

def save_settings(settings):
    """Verilen ayarları config.json dosyasına kaydeder."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
    except IOError:
        print(f"Hata: Ayarlar dosyası '{CONFIG_FILE}' kaydedilemedi.")


# --- STEAM OTOMASYONU (STEAM AUTOMATION) ---

def get_steam_install_path():
    """Windows Registry'den Steam'in kurulum yolunu bulur."""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        return path
    except FileNotFoundError:
        return None

def find_steam_profiles():
    """Bilgisayardaki tüm Steam profillerini userdata klasöründen tarar ve kullanıcı adı ile ID'sini döndürür."""
    steam_path = get_steam_install_path()
    if not steam_path: return []
    userdata_path = os.path.join(steam_path, "userdata")
    if not os.path.exists(userdata_path): return []
    profiles = []
    for user_id in os.listdir(userdata_path):
        if not user_id.isdigit(): continue
        config_path = os.path.join(userdata_path, user_id, 'config', 'localconfig.vdf')
        persona_name = f"Profil ({user_id})"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    match = re.search(r'"PersonaName"\s+"([^"]+)"', content)
                    if match: persona_name = match.group(1)
            except Exception: pass
        profiles.append({'persona_name': persona_name, 'user_id': user_id})
    return profiles

def get_app_list_from_steam():
    """Steam API'sinden tüm oyunların listesini çeker ve bir JSON dosyasına kaydeder."""
    try:
        url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        app_map = {str(app['appid']): app['name'] for app in data.get('applist', {}).get('apps', [])}
        with open("steam_app_list.json", "w", encoding="utf-8") as f:
            json.dump(app_map, f)
        return app_map
    except (requests.RequestException, json.JSONDecodeError):
        return None

def scan_for_games(selected_user_id):
    """SADECE seçilen kullanıcının klasörlerini tarar ve SS klasörü olan oyunları bulur."""
    steam_path = get_steam_install_path()
    if not steam_path: return {"success": False, "message_key": "steam_not_found"}

    app_map = {}
    try:
        if os.path.exists("steam_app_list.json"):
            with open("steam_app_list.json", "r", encoding="utf-8") as f:
                app_map = json.load(f)
        else:
            app_map = get_app_list_from_steam()
            if app_map is None: return {"success": False, "message_key": "applist_download_fail"}
    except Exception as e:
        return {"success": False, "message_key": "applist_process_fail", "data": str(e)}

    found_games = []
    remote_path = os.path.join(steam_path, "userdata", selected_user_id, "760", "remote")
    if os.path.exists(remote_path):
        for app_id in os.listdir(remote_path):
            if not app_id.isdigit(): continue
            screenshots_path = os.path.join(remote_path, app_id, "screenshots")
            if os.path.exists(screenshots_path):
                game_name = app_map.get(app_id, f"Bilinmeyen Oyun ({app_id})")
                found_games.append({"name": game_name, "path": screenshots_path})
    if not found_games:
        return {"success": False, "message_key": "no_games_with_screenshots_found"}
    found_games.sort(key=lambda x: x['name'])
    return {"success": True, "data": found_games}


# --- RESİM İŞLEME (IMAGE PROCESSING) ---

def generate_steam_filename():
    """Rastgele, tarih ve saat damgalı bir Steam dosyası adı oluşturur."""
    return f"{time.strftime('%Y%m%d%H%M%S')}_{random.randint(1, 5)}.jpg"

def create_thumbnail(image_source, output_path, width=200):
    """Hem dosya yolundan hem de Pillow nesnesinden thumbnail oluşturabilir."""
    try:
        img = image_source if isinstance(image_source, Image.Image) else Image.open(image_source)
        ratio = width / float(img.size[0])
        height = int((float(img.size[1]) * float(ratio)))
        resized_img = img.resize((width, height), Image.LANCZOS)
        rgb_img = resized_img.convert('RGB')
        rgb_img.save(output_path, "JPEG", quality=90)
        return True
    except Exception:
        return False

def process_image(image_source, screenshots_folder_path):
    """Hem dosya yolundan hem de Pillow nesnesinden resim işleyebilir."""
    try:
        img_to_process = image_source if isinstance(image_source, Image.Image) else Image.open(image_source)
        steam_filename = generate_steam_filename()
        steam_full_path = os.path.join(screenshots_folder_path, steam_filename)
        steam_thumbs_folder = os.path.join(screenshots_folder_path, "thumbnails")
        steam_thumb_path = os.path.join(steam_thumbs_folder, steam_filename)
        if not os.path.exists(steam_thumbs_folder):
            os.makedirs(steam_thumbs_folder)
        rgb_img = img_to_process.convert("RGB")
        rgb_img.save(steam_full_path, "JPEG", quality=95)
        if not create_thumbnail(img_to_process, steam_thumb_path):
            return {"success": False, "message_key": "thumbnail_error"}
        return {"success": True, "message_key": "upload_success_message", "data": steam_filename}
    except Exception as e:
        return {"success": False, "message_key": "unexpected_error", "data": str(e)}