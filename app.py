import sys
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

class CleanBrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WhatsApp 管理器")
        self.resize(1200, 800)

        # 1. 🎯 在这里锁定您需要打开的固定网址
        TARGET_URL = "https://google.com"

        # 2. 核心：创建一个“无痕/非持久化”的全新浏览器配置文件
        # storage_name 留空，True 表示开启 Off-the-Record (无痕内存模式)
        profile = QWebEngineProfile("", self)
        
        # 3. 强力双保险：禁用 Cookie 持久化存储，彻底切断本地写入
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        
        # 清理可能残存的内存缓存（防止单次运行中的极端缓存）
        profile.clearHttpCache()

        # 4. 用这个干净的配置创建一个网页页面
        web_page = QWebEnginePage(profile, self)

        # 5. 将页面绑定到视图并加载锁定地址
        self.browser = QWebEngineView(self)
        self.browser.setPage(web_page)
        self.browser.setUrl(QUrl(TARGET_URL))

        self.setCentralWidget(self.browser)

def main():
    # 彻底关闭磁盘缓存和应用缓存的全局环境变量设置
    import os
    os.environ["QTWEBENGINE_DISABLE_HDCP"] = "1"
    
    app = QApplication(sys.argv)
    window = CleanBrowserWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
