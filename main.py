# main.py
#!/usr/bin/env python3
"""
QR Code Matrix File Transfer - メインエントリーポイント
"""

from app import QRMatrixSenderApp

def main():
    """メイン関数"""
    app = QRMatrixSenderApp()
    app.run()

if __name__ == "__main__":
    main()


# app.py
"""
メインアプリケーションクラス
"""

import tkinter as tk
from pathlib import Path
from ui.main_window import MainWindow
from core.file_processor import FileProcessor
from core.qr_generator import QRGenerator
from core.transmission import TransmissionController

class QRMatrixSenderApp:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("QR Matrix File Transfer - 高速送信")
        
        # コンポーネント初期化
        self.file_processor = FileProcessor()
        self.qr_generator = QRGenerator()
        self.transmission_controller = TransmissionController()
        
        # UI初期化
        self.ui = MainWindow(
            self.window,
            self.file_processor,
            self.qr_generator,
            self.transmission_controller
        )
        
    def run(self):
        """アプリケーション実行"""
        self.window.mainloop()