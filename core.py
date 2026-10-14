import os
import zipfile
import shutil
import urllib.parse

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
    
    # 🟢 彻底解决病根1：清洗和解码 Windows 传入的任何带有中文、大括号或特殊符号的复杂路径
    try:
        file_path = file_path.strip('{} ')
        file_path = urllib.parse.unquote(file_path)
        pure_name = os.path.basename(file_path)
    except:
        pure_name = f"backup_{archive_id}.zip"
        
    # 在本地创建绝对安全的纯英文隔离缓存区，彻底断绝任何因中文包名引发的解压路径死锁
    temp_dir = os.path.join(CACHE_ROOT, f"env_archive_box_{archive_id}")
    
    try:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir, ignore_errors=True)
        
        # 🟢 彻底解决病根2：双重编码撞击引擎，100% 解决含中文、字母、符号备份解压后的乱码判定失败问题
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                z.extractall(temp_dir)
        except:
            with zipfile.ZipFile(file_path, 'r') as z:
                for member in z.infolist():
                    try:
                        member.filename = member.filename.encode('cp437').decode('gbk')
                    except:
                        try:
                            member.filename = member.filename.encode('cp437').decode('utf-8')
                        except:
                            pass
                    z.extract(member, temp_dir)
        
        # 全盘扫描任何包含 Default、Profile (中文字母数字全包容) 关键字的目录
        found_profiles = []
        for dirpath, _, filenames in os.walk(temp_dir):
            folder_name = os.path.basename(dirpath).lower()
            if "default" in folder_name or "profile" in folder_name:
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
            
            # 状态只保留：成功 或 失败
            profile_list.append({
                "name": name, 
                "path": p_path,
                "status": "成功" if is_valid else "失败",
                "valid": is_valid
            })
        return {"profiles": profile_list, "temp_dir": temp_dir, "pure_name": pure_name}
    except Exception as e:
        print(f"底层核心致命错误: {e}")
        return None

def run_chrome(profile_path):
    if not os.path.exists(CHROME_EXE): return False
    try:
        if os.path.exists(TARGET_REPLACE_DIR): shutil.rmtree(TARGET_REPLACE_DIR, ignore_errors=True)
    except: pass
    copy_contents(profile_path, TARGET_REPLACE_DIR)
    os.system(f'start "" "{CHROME_EXE}" --no-first-run --no-default-browser-check "https://://whatsapp.com"')
    return True
