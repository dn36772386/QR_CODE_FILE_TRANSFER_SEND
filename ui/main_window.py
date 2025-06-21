"""
メインウィンドウUI
"""

import tkinter as tk
from tkinter import ttk
from .components import ControlPanel, QRDisplayCanvas, StatusBar

class MainWindow:
    def __init__(self, window, file_processor, qr_generator, transmission_controller):
        self.window = window
        self.file_processor = file_processor
        self.qr_generator = qr_generator
        self.transmission_controller = transmission_controller
        
        # フルスクリーン設定
        self.window.state('zoomed')
        self.window.configure(bg='white')
        
        # 画面サイズ取得
        self.screen_width = self.window.winfo_screenwidth()
        self.screen_height = self.window.winfo_screenheight()
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI構築"""
        # メインコンテナ
        self.main_frame = tk.Frame(self.window, bg='white')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # コントロールパネル
        self.control_panel = ControlPanel(
            self.main_frame,
            self.on_file_selected,
            self.on_start_transmission,
            self.on_stop_transmission
        )
        
        # QRコード表示エリア
        self.qr_canvas = QRDisplayCanvas(self.main_frame)
        
        # ステータスバー
        self.status_bar = StatusBar(self.main_frame, self.screen_width)
        
        # ESCキーで終了
        self.window.bind('<Escape>', lambda e: self.window.quit())
        
    def on_file_selected(self, file_path):
        """ファイル選択時の処理"""
        result = self.file_processor.process_file(file_path)
        if result:
            self.qr_generator.set_file_data(result)
            self.qr_generator.generate_all_qrcodes(
                self.qr_canvas.get_matrix_size(),
                self.on_generation_progress,
                self.on_generation_complete
            )
            
    def on_generation_progress(self, progress, message):
        """QRコード生成進捗"""
        self.status_bar.update_generation_progress(progress, message)
        
    def on_generation_complete(self):
        """QRコード生成完了"""
        self.control_panel.enable_transmission()
        self.status_bar.set_status("送信準備完了", "#4CAF50")
        
    def on_start_transmission(self, fps):
        """送信開始"""
        self.transmission_controller.start(
            self.qr_generator,
            self.qr_canvas,
            fps,
            self.on_transmission_progress
        )
        
    def on_stop_transmission(self):
        """送信停止"""
        self.transmission_controller.stop()
        
    def on_transmission_progress(self, progress, status):
        """送信進捗"""
        self.status_bar.update_progress(progress, status)
