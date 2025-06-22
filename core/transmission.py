"""
転送制御モジュール（簡略化版）
"""

import time
import threading
import tkinter as tk
from typing import Callable

class TransmissionController:
    def __init__(self):
        self.is_transmitting = False
        self.current_index = 0
        self.cycle_count = 0
        self.transmission_thread = None
        
    def start(self, qr_generator, qr_canvas, fps, progress_callback):
        """送信開始（無限ループ）"""
        if self.is_transmitting:
            return
            
        self.is_transmitting = True
        self.current_index = 0
        self.cycle_count = 0
        
        self.transmission_thread = threading.Thread(
            target=self._transmission_loop,
            args=(qr_generator, qr_canvas, fps, progress_callback)
        )
        self.transmission_thread.daemon = True
        self.transmission_thread.start()
        
    def stop(self):
        """送信停止"""
        self.is_transmitting = False
        self.current_index = 0
        self.cycle_count = 0

    def _transmission_loop(self, qr_generator, qr_canvas, fps, progress_callback):
        """送信ループ（制御QR付きマトリックスを表示）"""
        frame_interval = 1.0 / fps
        matrix_duration = fps * 3  # 各ページ3秒表示
        
        # 写真モード用の設定を取得
        cols, rows, qr_per_frame = qr_canvas.get_matrix_size(photo_mode=True)
        
        # 実際のグリッドサイズを使用
        max_cols = max(5, cols)
        max_rows = max(4, rows)
        actual_qr_per_frame = max_cols * max_rows
        
        # 4隅の制御QR分を引く
        adjusted_qr_per_frame = actual_qr_per_frame - 4
        chunk_count = qr_generator.get_chunk_count()
        total_pages = (chunk_count + adjusted_qr_per_frame - 1) // adjusted_qr_per_frame
        
        print(f"=== 送信設定 ===")
        print(f"グリッド: {max_cols}x{max_rows} = {actual_qr_per_frame}個")
        print(f"データQR/ページ: {adjusted_qr_per_frame}個")
        print(f"総ページ数: {total_pages}")
        
        matrix_count = 0
        
        while self.is_transmitting:
            start_time = time.time()
            
            # チャンクマトリックス表示
            if matrix_count == 0:
                self._display_matrix(qr_generator, qr_canvas, self.current_index)
                
                # 進捗更新
                chunk_end = min(self.current_index + adjusted_qr_per_frame, chunk_count)
                progress = ((self.current_index // adjusted_qr_per_frame) + 1) / total_pages * 100
                page_number = (self.current_index // adjusted_qr_per_frame) + 1
                
                status = f"ページ {page_number}/{total_pages} - チャンク: {self.current_index + 1}-{chunk_end} / {chunk_count} (サイクル: {self.cycle_count + 1})"
                progress_callback(progress, status)
                
            matrix_count += 1
            
            if matrix_count >= matrix_duration:
                self.current_index += adjusted_qr_per_frame
                matrix_count = 0
                
                if self.current_index >= chunk_count:
                    # 一巡完了、最初に戻る
                    self.current_index = 0
                    self.cycle_count += 1
                    
            # フレームレート調整
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            time.sleep(sleep_time)
            
    def _display_matrix(self, qr_generator, qr_canvas, index):
        """マトリックス表示"""
        qr_canvas.clear()
        matrix_img = qr_generator.get_image(index)
        if matrix_img:
            # 写真モード：画面中央に配置
            x, y = qr_canvas.get_center()
            qr_canvas.display_image(matrix_img, x, y)
            
            # 制御QRコードの説明
            qr_canvas.display_text(
                x, 30,
                "📸 青と緑の制御QRコードが両方見えるようにiPhoneを向けてください",
                ('Arial', 16, 'bold'),
                'black'
            )