"""
転送制御モジュール（一巡で自動終了版）
"""

import time
import threading
import tkinter as tk
from typing import Callable

class TransmissionController:
    def __init__(self):
        self.is_transmitting = False
        self.current_index = -1
        self.cycle_count = 0
        self.transmission_thread = None
        self.single_cycle_mode = True  # 一巡で終了するモード
        
    def start(self, qr_generator, qr_canvas, fps, progress_callback, single_cycle=True):
        """送信開始"""
        if self.is_transmitting:
            return
            
        self.is_transmitting = True
        self.current_index = -1
        self.cycle_count = 0
        self.single_cycle_mode = single_cycle
        
        self.transmission_thread = threading.Thread(
            target=self._transmission_loop,
            args=(qr_generator, qr_canvas, fps, progress_callback)
        )
        self.transmission_thread.daemon = True
        self.transmission_thread.start()
        
    def stop(self):
        """送信停止"""
        self.is_transmitting = False
        self.current_index = -1

    def _transmission_loop(self, qr_generator, qr_canvas, fps, progress_callback):
        """送信ループ"""
        # 最初に録画開始QRを表示
        self._display_control_qr(qr_generator, qr_canvas, "recording_start")
        time.sleep(2.0)  # 2秒間表示
        
        frame_interval = 1.0 / fps
        header_duration = fps * 2  # 2秒
        matrix_duration = fps * 3  # 3秒（デュアル制御のため延長）
        
        cols, rows, qr_per_frame = qr_canvas.get_matrix_size(photo_mode=True)
        
        # 写真モードでは4隅の制御QR分を引く
        adjusted_qr_per_frame = qr_per_frame - 4
        chunk_count = qr_generator.get_chunk_count()
        
        header_count = 0
        matrix_count = 0
        
        # 一巡で終了するかどうかのフラグ
        should_stop_after_cycle = self.single_cycle_mode
        
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
                    self._display_matrix(qr_generator, qr_canvas, self.current_index, photo_mode=True)
                    
                    # 進捗更新
                    chunk_end = min(self.current_index + adjusted_qr_per_frame, chunk_count)
                    progress = (chunk_end / chunk_count) * 100
                    page_number = (self.current_index // adjusted_qr_per_frame) + 1
                    total_pages = (chunk_count + adjusted_qr_per_frame - 1) // adjusted_qr_per_frame
                    
                    if should_stop_after_cycle:
                        status = f"ページ {page_number}/{total_pages} - チャンク: {self.current_index + 1}-{chunk_end} / {chunk_count}"
                    else:
                        status = f"ページ {page_number}/{total_pages} - チャンク: {self.current_index + 1}-{chunk_end} / {chunk_count} (サイクル: {self.cycle_count + 1})"
                    
                    progress_callback(progress, status)
                    
                matrix_count += 1
                
                if matrix_count >= matrix_duration:
                    self.current_index += adjusted_qr_per_frame
                    matrix_count = 0
                    
                    if self.current_index >= chunk_count:
                        # 一巡完了
                        self.cycle_count += 1
                        
                        if should_stop_after_cycle:
                            # 一巡モードの場合、ループを終了
                            self.is_transmitting = False
                            progress_callback(100, "転送完了！")
                            break
                        else:
                            # 継続モードの場合、最初に戻る
                            self.current_index = -1
                        
            # フレームレート調整
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            time.sleep(sleep_time)
        
        # 最後に録画終了QRを表示（ループを抜けた後）
        self._display_control_qr(qr_generator, qr_canvas, "recording_end")
        time.sleep(3.0)  # 3秒間表示（確実に検出されるように）
        
        # 通常のヘッダー表示に戻す
        self._display_header(qr_generator, qr_canvas)
        progress_callback(100, "転送完了 - 終了QRコードを表示しました")
            
    def _display_header(self, qr_generator, qr_canvas):
        """ヘッダー表示"""
        qr_canvas.clear()
        header_img = qr_generator.get_image('header')
        if header_img:
            x, y = qr_canvas.get_center()
            qr_canvas.display_image(header_img, x, y)
            qr_canvas.display_text(
                x, y + 320,
                "📱 ヘッダー情報 - iPhoneでスキャンしてください",
                ('Arial', 20, 'bold'),
                'red'
            )
            
    def _display_matrix(self, qr_generator, qr_canvas, index, photo_mode=False):
        """マトリックス表示"""
        qr_canvas.clear()
        matrix_img = qr_generator.get_image(index)
        if matrix_img:
            if photo_mode:
                # 写真モード：画面中央に配置
                x, y = qr_canvas.get_center()
                # マトリックスのサイズに応じて調整
                qr_canvas.display_image(matrix_img, x, y)
                
                # 4隅の制御QRコードの説明
                qr_canvas.display_text(
                    x, 30,
                    "📸 青と緑の制御QRコードが見えるようにiPhoneを向けてください",
                    ('Arial', 16, 'bold'),
                    'black'
                )
            else:
                # 動画モード：左上配置
                qr_canvas.display_image(matrix_img, 50, 50, tk.NW)
                
                # デュアル制御の説明を追加
                x, y = qr_canvas.get_center()
                qr_canvas.display_text(
                    x, 30,
                    "左上（青）と右下（緑）の制御QRコードが両方見えるようにしてください",
                    ('Arial', 14, 'bold'),
                    'black'
                )
            
    def _display_control_qr(self, qr_generator, qr_canvas, control_type):
        """制御用QRコード表示"""
        
        qr_canvas.clear()
        control_img = qr_generator.create_control_qr(control_type)
        if control_img:
            x, y = qr_canvas.get_center()
            qr_canvas.display_image(control_img, x, y)
            
            # メッセージ表示
            if control_type == "recording_start":
                message = "📱 録画/撮影を開始してください"
                color = 'red'
            else:  # recording_end
                message = "✅ 転送完了！録画/撮影を停止してください"
                color = 'green'
                
            qr_canvas.display_text(
                x, y + 320,
                message,
                ('Arial', 20, 'bold'),
                color
            )
            
            # 終了QRの場合は追加情報を表示
            if control_type == "recording_end":
                qr_canvas.display_text(
                    x, y + 350,
                    "このQRコードを検出すると自動的に処理が開始されます",
                    ('Arial', 14),
                    'gray'
                )