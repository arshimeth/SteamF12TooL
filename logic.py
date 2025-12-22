import os
import time
import random
from PIL import Image
import winreg
import requests
import json
import re
import sys 

CONFIG_FILE = 'config.json'

MANUAL_MODS = {
    "17520": "Synergy",
    "225840": "Sven Co-op",
    "4000": "Garry's Mod",
    "362890": "Black Mesa",
    "290930": "Half-Life 2: Update",
    "243750": "Source SDK Base 2013 Multiplayer",
    "211": "Source SDK Base 2006",
    "215": "Source SDK Base 2007",
    "218": "Source SDK Base 2013 Singleplayer",
    "427720": "Black Mesa: Blue Shift",
    "1548270": "Prop Hunt",
    "3081410": "Battlefield 6 (Redsec)" 
}

def resource_path(relative_path):
    """ PyInstaller için dosya yolu bulucu (Hem GUI hem Logic kullanır) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_settings():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return {'language': 'en', 'theme': 'Dark', 'last_profile': None}

def save_settings(settings):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
    except IOError:
        print(f"Hata: Ayarlar dosyası '{CONFIG_FILE}' kaydedilemedi.")

def get_steam_install_path():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        return path
    except FileNotFoundError:
        return None

def find_steam_profiles():
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
    # Bu fonksiyon sadece "GÜNCEL" listeyi indirip exe'nin yanına (local) kaydeder.
    sources = [
        "http://api.steampowered.com/ISteamApps/GetAppList/v0002/?format=json",
        "https://raw.githubusercontent.com/jsnli/steamappidlist/refs/heads/master/data/games_appid.json"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    print("Oyun listesi indiriliyor...")

    for url in sources:
        try:
            print(f"Bağlanılıyor: {url}")
            raw_content = bytearray()
            with requests.get(url, headers=headers, stream=True, timeout=60) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk: raw_content.extend(chunk)
            
            try:
                json.loads(raw_content.decode('utf-8-sig', errors='ignore'))
            except json.JSONDecodeError:
                print("İndirilen veri geçerli bir JSON değil, atlanıyor.")
                continue

            # İndirilen dosya her zaman çalışılan dizine (exe yanına) kaydedilir.
            with open("steam_app_list.json", "wb") as f:
                f.write(raw_content)
                
            print(f"Dosya başarıyla indirildi ve kaydedildi. Boyut: {len(raw_content)} byte.")
            return {"status": "success"} 

        except Exception as e:
            print(f"Hata ({url}): {e}")
            continue
            
    return None

def parse_json_to_map(file_path, existing_map):
    """Helper: Verilen dosya yolundaki JSON'ı okuyup existing_map'e ekler."""
    if not os.path.exists(file_path):
        return

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f: 
            data = json.load(f)
        
        source_list = []
        # JSON yapısını analiz et (List mi, Dict mi?)
        if isinstance(data, list):
            source_list = data
        elif isinstance(data, dict):
            if "applist" in data and "apps" in data["applist"]:
                source_list = data["applist"]["apps"]
            elif "apps" in data:
                source_list = data["apps"]
            else:
                # Key-Value yapısındaysa (örn: {"10": "CS"})
                for k, v in data.items(): 
                    existing_map[str(k)] = str(v)
                return 

        # Liste yapısındaysa (örn: [{"appid": 10, "name": "CS"}]) standartlaştır
        for item in source_list:
            if isinstance(item, dict):
                aid = item.get('appid') or item.get('appId') or item.get('id')
                name = item.get('name') or item.get('gamename')
                if aid and name:
                    existing_map[str(aid)] = name
    except Exception as e:
        print(f"JSON okuma hatası ({file_path}): {e}")

def scan_for_games(selected_user_id):
    steam_path = get_steam_install_path()
    if not steam_path: return {"success": False, "message_key": "steam_not_found"}

    app_map = {}
    
    # 1. ADIM: Gömülü Dosya (Exe içindeki temel liste - Offline Destek)
    embedded_path = resource_path("steam_app_list.json")
    parse_json_to_map(embedded_path, app_map)

    # 2. ADIM: İndirilmiş Dosya (Exe yanındaki güncel liste - Update Desteği)
    local_path = "steam_app_list.json"
    
    # Eğer geliştirme ortamındaysak embedded ve local aynı dosya olabilir,
    # çift okumayı engellemek için path kontrolü yapıyoruz.
    if os.path.abspath(local_path) != os.path.abspath(embedded_path):
        # Local dosya varsa, embedded verilerin üzerine yazar (günceller)
        parse_json_to_map(local_path, app_map)
    
    # 3. ADIM: Manuel Modlar (En yüksek öncelik)
    app_map.update(MANUAL_MODS)

    found_games = []
    remote_path = os.path.join(steam_path, "userdata", selected_user_id, "760", "remote")
    
    if os.path.exists(remote_path):
        for app_id in os.listdir(remote_path):
            if not app_id.isdigit(): continue
            screenshots_path = os.path.join(remote_path, app_id, "screenshots")
            if os.path.exists(screenshots_path):
                game_name = app_map.get(str(app_id), f"Oyun ID: {app_id}")
                found_games.append({"name": game_name, "path": screenshots_path})
                
    if not found_games:
        return {"success": False, "message_key": "no_games_with_screenshots_found"}
        
    found_games.sort(key=lambda x: x['name'])
    return {"success": True, "data": found_games}

def generate_steam_filename():
    return f"{time.strftime('%Y%m%d%H%M%S')}_{random.randint(1, 5)}.jpg"

def create_thumbnail(image_source, output_path, width=200):
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
    try:
        img_to_process = image_source if isinstance(image_source, Image.Image) else Image.open(image_source)
        steam_filename = generate_steam_filename()
        steam_full_path = os.path.join(screenshots_folder_path, steam_filename)
        steam_thumbs_folder = os.path.join(screenshots_folder_path, "thumbnails")
        steam_thumb_path = os.path.join(steam_thumbs_folder, steam_filename)
        if not os.path.exists(steam_thumbs_folder): os.makedirs(steam_thumbs_folder)
        rgb_img = img_to_process.convert("RGB")
        rgb_img.save(steam_full_path, "JPEG", quality=95)
        if not create_thumbnail(img_to_process, steam_thumb_path):
            return {"success": False, "message_key": "thumbnail_error"}
        return {"success": True, "message_key": "upload_success_message", "data": steam_filename}
    except Exception as e:
        return {"success": False, "message_key": "unexpected_error", "data": str(e)}