"""
メインウィンドウUI（簡略化版）
"""

import tkinter as tk
from tkinter import ttk
from .components import ControlPanel, QRDisplayCanvas, StatusBar
from utils.helpers import format_size

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
        # チャンクサイズを更新
        self.file_processor.chunk_size = int(self.control_panel.chunk_size_var.get())
        result = self.file_processor.process_file(file_path)
        if result:
            # ファイルサイズ情報を表示
            size_info = f"元: {format_size(result['original_size'])} → 圧縮: {format_size(result['compressed_size'])} " \
                       f"({100 - (result['compressed_size'] / result['original_size'] * 100):.1f}%削減)"
            self.status_bar.progress_label.config(text=size_info)
            
            # QRコード生成前に総ページ数を計算
            cols, rows, qr_per_frame = self.qr_canvas.get_matrix_size(photo_mode=True)
            max_cols = max(5, cols)
            max_rows = max(4, rows)
            actual_qr_per_frame = max_cols * max_rows
            adjusted_qr_per_frame = actual_qr_per_frame - 4  # 4隅の制御QR分を引く
            total_pages = (len(result['chunks']) + adjusted_qr_per_frame - 1) // adjusted_qr_per_frame
            
            self.status_bar.set_status(
                f"準備完了: {len(result['chunks'])}チャンク / {total_pages}ページ", 
                "#4CAF50"
            )
            
            self.qr_generator.set_file_data(result)
            self.qr_generator.generate_all_qrcodes(
                self.qr_canvas.get_matrix_size(photo_mode=True),
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
        # 初期表示（ヘッダー）
        self._display_header()
        
    def on_start_transmission(self, fps):
        """送信開始（制御QR付きマトリックスを直接表示）"""
        self.transmission_controller.start(
            self.qr_generator,
            self.qr_canvas,
            fps,
            self.on_transmission_progress
        )
        # ボタン状態更新
        self.control_panel.start_btn.config(state=tk.DISABLED)
        self.control_panel.stop_btn.config(state=tk.NORMAL)
        self.status_bar.set_status("送信中...", "#2196F3")

    def on_stop_transmission(self):
        """送信停止（手動）"""
        self.transmission_controller.stop()
        # ボタン状態更新
        self.control_panel.start_btn.config(state=tk.NORMAL)
        self.control_panel.stop_btn.config(state=tk.DISABLED)
        # ヘッダー表示に戻る
        self._display_header()
        self.status_bar.set_status("待機中", "#666")
        self.status_bar.update_progress(0, "")

    def on_transmission_progress(self, progress, status):
        """送信進捗"""
        self.status_bar.update_progress(progress, status)
        
    def _display_header(self):
        """ヘッダー表示"""
        self.qr_canvas.clear()
        header_img = self.qr_generator.get_image('header')
        if header_img:
            x, y = self.qr_canvas.get_center()
            self.qr_canvas.display_image(header_img, x, y)
            
            # 総ページ数を含むメッセージ
            cols, rows, qr_per_frame = self.qr_canvas.get_matrix_size(photo_mode=True)
            max_cols = max(5, cols)
            max_rows = max(4, rows)
            actual_qr_per_frame = max_cols * max_rows
            adjusted_qr_per_frame = actual_qr_per_frame - 4
            chunk_count = self.qr_generator.get_chunk_count()
            total_pages = (chunk_count + adjusted_qr_per_frame - 1) // adjusted_qr_per_frame
            
            self.qr_canvas.display_text(
                x, y + 320,
                f"📱 ヘッダー情報 - iPhoneでスキャンしてください\n（全{total_pages}ページ）",
                ('Arial', 20, 'bold'),
                'red'
            )