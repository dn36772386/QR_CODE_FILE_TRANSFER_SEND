"""
転送制御モジュール
"""

import time
import threading
from typing import Callable

class TransmissionController:
    def __init__(self):
        self.is_transmitting = False
        self.current_index = -1
        self.cycle_count = 0
        self.transmission_thread = None
        
    def start(self, qr_generator, qr_canvas, fps, progress_callback):
        """送信開始"""
        if self.is_transmitting:
            return
            
        self.is_transmitting = True
        self.current_index = -1
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
        
    def _transmission_loop(self, qr_generator, qr_canvas, fps, progress_callback):
        """送信ループ"""
        frame_interval = 1.0 / fps
        header_duration = fps * 3  # 3秒
        matrix_duration = fps  # 1秒
        
        _, _, qr_per_frame = qr_canvas.get_matrix_size()
        chunk_count = qr_generator.get_chunk_count()
        
        header_count = 0
        matrix_count = 0
        
        while self.is_transmitting:
            start_time = time.time()
            
            if self.current_index == -1:
                # ヘッダー表示
                if header_count == 0:
                    self._display_header(qr_generator, qr_canvas)
                header_count += 1
                
                if header_count >= header_duration:
                    self.current_index = 0
                    header_count = 0
                    matrix_count = 0
            else:
                # チャンクマトリックス表示
                if matrix_count == 0:
                    self._display_matrix(qr_generator, qr_canvas, self.current_index)
                    
                    # 進捗更新
                    chunk_end = min(self.current_index + qr_per_frame, chunk_count)
                    progress = (chunk_end / chunk_count) * 100
                    status = f"チャンク: {self.current_index + 1}-{chunk_end} / {chunk_count} (サイクル: {self.cycle_count + 1})"
                    progress_callback(progress, status)
                    
                matrix_count += 1
                
                if matrix_count >= matrix_duration:
                    self.current_index += qr_per_frame
                    matrix_count = 0
                    
                    if self.current_index >= chunk_count:
                        self.current_index = -1
                        self.cycle_count += 1
                        
            # フレームレート調整
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            time.sleep(sleep_time)
            
    def _display_header(self, qr_generator, qr_canvas):
        """ヘッダー表示"""
        qr_canvas.clear()
        header_img = qr_generator.get_image('header')
        if header_img:
            x, y = qr_canvas.get_center()
            qr_canvas.display_image(header_img, x, y)
            qr_canvas.display_text(
                x, y + 320,
                "📱 ヘッダー情報 - iPhoneで録画を開始してください",
                ('Arial', 20, 'bold'),
                'red'
            )
            
    def _display_matrix(self, qr_generator, qr_canvas, index):
        """マトリックス表示"""
        qr_canvas.clear()
        matrix_img = qr_generator.get_image(index)
        if matrix_img:
            qr_canvas.display_image(matrix_img, 50, 50, tk.NW)
