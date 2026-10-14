import os
import zipfile
import shutil

# 内置固定的便携版浏览器地址与替换目标路径
CHROME_EXE = r"C:\Users\Administrator\Desktop\GoogleChromePortable\GoogleChromePortable.exe"
TARGET_REPLACE_DIR = r"C:\Users\Administrator\Desktop\GoogleChromePortable\Data\profile\Default"
CACHE_ROOT = os.path.join(os.getcwd(), "whatsapp_runtime_env")

def init_cache():
    if not os.path.exists(CACHE_ROOT):
        os.makedirs(CACHE_ROOT)

def copy_contents(source_dir, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    for item in os.listdir(source_dir):
        s = os.path.join(source_dir, item)
        d = os.path.join(target_dir, item)
        if os.path.isdir(s):
            if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

def analyze_zip(file_path, archive_id):
    init_cache()
    pure_name = os.path.basename(file_path)
    temp_dir = os.path.join(CACHE_ROOT, f"env_{pure_name.replace('.', '_')}_{archive_id}")
    
    try:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir, ignore_errors=True)
        with zipfile.ZipFile(file_path, 'r') as z: z.extractall(temp_dir)
        
        valid_names = {"default"}
        for i in range(1, 101): valid_names.add(f"profile {i}")
        
        found_profiles = []
        for dirpath, _, filenames in os.walk(temp_dir):
            if os.path.basename(dirpath).lower() in valid_names:
                found_profiles.append(dirpath)
        if not found_profiles: found_profiles.append(temp_dir)
        
        profile_list = []
        for p_path in found_profiles:
            name = os.path.basename(p_path)
            if name == os.path.basename(temp_dir): name = "Default"
            
            is_valid = False
            for dp, _, fnames in os.walk(p_path):
                if "local storage" in dp.lower() and "leveldb" in dp.lower():
                    for f in fnames:
                        if f.lower().endswith(('.log', '.ldb', '.localstorage')):
                            try:
                                with open(os.path.join(dp, f), 'rb') as db:
                                    if b'whatsapp' in db.read() or b'://whatsapp.com' in db.read():
                                        is_valid = True
                                        break
                            except: pass
                if is_valid: break
            
            profile_list.append({
                "name": name, "path": p_path,
                "status": "已导入打开" if is_valid else "失败：未甄别到登录数据",
                "valid": is_valid
            })
        return {"profiles": profile_list, "temp_dir": temp_dir, "pure_name": pure_name}
    except:
        return None

def run_chrome(profile_path):
    if not os.path.exists(CHROME_EXE): return False
    try:
        if os.path.exists(TARGET_REPLACE_DIR): shutil.rmtree(TARGET_REPLACE_DIR, ignore_errors=True)
    except: pass
    copy_contents(profile_path, TARGET_REPLACE_DIR)
    os.system(f'start "" "{CHROME_EXE}" --no-first-run --no-default-browser-check "https://://whatsapp.com"')
    return True
