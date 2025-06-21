"""
QRコード生成モジュール
"""

import json
import time
import threading
from PIL import Image, ImageTk
import segno
from io import BytesIO
from typing import Dict, Any, Callable, Tuple

class QRGenerator:
    def __init__(self):
        self.file_data = None
        self.qr_images = {}
        self.qr_images_lock = threading.Lock()
        self.is_generating = False
        
    def set_file_data(self, file_data: Dict[str, Any]):
        """ファイルデータ設定"""
        self.file_data = file_data
        self.qr_images.clear()
        
    def generate_all_qrcodes(self, matrix_size: Tuple[int, int, int], 
                           progress_callback: Callable, 
                           complete_callback: Callable):
        """すべてのQRコード生成"""
        if self.is_generating or not self.file_data:
            return
            
        self.is_generating = True
        cols, rows, qr_per_frame = matrix_size
        
        # バックグラウンドで生成
        thread = threading.Thread(
            target=self._generate_thread,
            args=(cols, rows, qr_per_frame, progress_callback, complete_callback)
        )
        thread.daemon = True
        thread.start()
        
    def _generate_thread(self, cols, rows, qr_per_frame, progress_callback, complete_callback):
        """生成スレッド"""
        try:
            chunks = self.file_data['chunks']
            total_count = 1 + len(chunks)
            current_count = 0
            
            # ヘッダー生成
            progress_callback(0, "ヘッダーQRコード生成中...")
            header_img = self._create_header_qr()
            with self.qr_images_lock:
                self.qr_images['header'] = header_img
            current_count += 1
            progress_callback((current_count / total_count) * 100, "ヘッダー生成完了")
            
            # チャンクマトリックス生成
            for i in range(0, len(chunks), qr_per_frame):
                msg = f"マトリックス生成中... {i//qr_per_frame + 1}/{(len(chunks) + qr_per_frame - 1)//qr_per_frame}"
                progress_callback((current_count / total_count) * 100, msg)
                
                matrix_img = self._create_qr_matrix(i, cols, rows, qr_per_frame)
                photo = ImageTk.PhotoImage(matrix_img)
                
                with self.qr_images_lock:
                    self.qr_images[i] = photo
                
                current_count += min(qr_per_frame, len(chunks) - i)
                
            complete_callback()
            
        finally:
            self.is_generating = False
            
    def _create_header_qr(self):
        """ヘッダーQRコード生成"""
        header_info = {
            "type": "header",
            "fileName": self.file_data['file_name'],
            "fileType": self.file_data['file_type'],
            "originalSize": self.file_data['original_size'],
            "compressedSize": self.file_data['compressed_size'],
            "compressed": True,
            "compressionType": self.file_data['compression_type'],
            "totalChunks": len(self.file_data['chunks']),
            "chunkSize": 2500,
            "timestamp": int(time.time())
        }
        
        qr = segno.make(json.dumps(header_info), error='l')
        buffer = BytesIO()
        qr.save(buffer, kind='png', scale=10, border=4)
        buffer.seek(0)
        img = Image.open(buffer)
        img = img.resize((600, 600), Image.Resampling.NEAREST)
        return ImageTk.PhotoImage(img)
        
    def _create_qr_matrix(self, start_index, cols, rows, qr_per_frame):
        """QRコードマトリックス生成"""
        qr_size = 250
        matrix_width = cols * qr_size
        matrix_height = rows * qr_size
        matrix = Image.new('RGB', (matrix_width, matrix_height), 'white')
        
        chunks = self.file_data['chunks']
        
        for i in range(qr_per_frame):
            chunk_index = start_index + i
            if chunk_index >= len(chunks):
                break
                
            chunk_data = {
                "type": "chunk",
                "chunkIndex": chunk_index,
                "data": chunks[chunk_index]
            }
            
            qr = segno.make(json.dumps(chunk_data), error='l')
            buffer = BytesIO()
            qr.save(buffer, kind='png', scale=4, border=1)
            buffer.seek(0)
            qr_img = Image.open(buffer)
            qr_img = qr_img.resize((qr_size - 20, qr_size - 20), Image.Resampling.NEAREST)
            
            row = i // cols
            col = i % cols
            x = col * qr_size + 10
            y = row * qr_size + 10
            
            matrix.paste(qr_img, (x, y))
            
        return matrix
        
    def get_image(self, key):
        """画像取得"""
        with self.qr_images_lock:
            return self.qr_images.get(key)
            
    def get_chunk_count(self):
        """チャンク数取得"""
        return len(self.file_data['chunks']) if self.file_data else 0
