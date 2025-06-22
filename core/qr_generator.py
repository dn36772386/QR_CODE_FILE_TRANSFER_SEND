"""
QRコード生成モジュール（写真撮影最適化版）
"""

import json
import time
import threading
from PIL import Image, ImageTk, ImageDraw, ImageFont
import segno
from io import BytesIO
from typing import Dict, Any, Callable, Tuple

class QRGenerator:
    def __init__(self):
        self.file_data = None
        self.qr_images = {}
        self.qr_images_lock = threading.Lock()
        self.is_generating = False
        self.control_qr_images = {}
        # 写真撮影用に最適化されたサイズ
        self.photo_optimized_qr_size = 150  # より小さいQRコード
        self.standard_qr_size = 250  # 動画用の標準サイズ
        
    def set_file_data(self, file_data: Dict[str, Any]):
        """ファイルデータ設定"""
        self.file_data = file_data
        self.qr_images.clear()
        
    def generate_all_qrcodes(self, matrix_size: Tuple[int, int, int], 
                           progress_callback: Callable, 
                           complete_callback: Callable,
                           photo_mode: bool = True):
        """すべてのQRコード生成"""
        if self.is_generating or not self.file_data:
            return
            
        self.is_generating = True
        cols, rows, qr_per_frame = matrix_size
        
        # バックグラウンドで生成
        thread = threading.Thread(
            target=self._generate_thread,
            args=(cols, rows, qr_per_frame, progress_callback, complete_callback, photo_mode)
        )
        thread.daemon = True
        thread.start()
        
    def _generate_thread(self, cols, rows, qr_per_frame, progress_callback, complete_callback, photo_mode):
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
            if photo_mode:
                # 写真モード：最大限のQRコードを配置（最低20個）
                self._generate_photo_optimized_matrices(
                    chunks, cols, rows, current_count, total_count, 
                    progress_callback
                )
            else:
                # 通常モード（動画用）
                adjusted_qr_per_frame = qr_per_frame - 2
                for i in range(0, len(chunks), adjusted_qr_per_frame):
                    page_number = (i // adjusted_qr_per_frame) + 1
                    total_pages = (len(chunks) + adjusted_qr_per_frame - 1) // adjusted_qr_per_frame
                    
                    msg = f"マトリックス生成中... {page_number}/{total_pages}"
                    progress_callback((current_count / total_count) * 100, msg)
                    
                    matrix_img = self._create_qr_matrix(i, cols, rows, adjusted_qr_per_frame, page_number, photo_mode=False)
                    photo = ImageTk.PhotoImage(matrix_img)
                    
                    with self.qr_images_lock:
                        self.qr_images[i] = photo
                    
                    current_count += min(adjusted_qr_per_frame, len(chunks) - i)
                
            complete_callback()
            
        finally:
            self.is_generating = False
    
    def _generate_photo_optimized_matrices(self, chunks, cols, rows, current_count, total_count, progress_callback):
        """写真撮影に最適化されたマトリックス生成"""
        # 写真モードでは制御QRコードを含めて最低20個のQRコードを表示
        # 画面サイズに応じて自動調整
        
        # より多くのQRコードを配置するための計算
        qr_size = self.photo_optimized_qr_size
        
        # 画面に収まる最大のグリッドサイズを計算
        max_cols = max(5, cols)  # 最低5列
        max_rows = max(4, rows)  # 最低4行
        
        # 制御QRコード分を考慮（4隅に配置）
        control_qr_count = 4
        qr_per_frame = (max_cols * max_rows) - control_qr_count
        
        # 最低16個のデータQRコードを確保
        qr_per_frame = max(16, qr_per_frame)
        
        for i in range(0, len(chunks), qr_per_frame):
            page_number = (i // qr_per_frame) + 1
            total_pages = (len(chunks) + qr_per_frame - 1) // qr_per_frame
            
            msg = f"写真用マトリックス生成中... ページ {page_number}/{total_pages}"
            progress_callback((current_count / total_count) * 100, msg)
            
            matrix_img = self._create_photo_optimized_matrix(
                i, max_cols, max_rows, qr_per_frame, page_number, total_pages
            )
            photo = ImageTk.PhotoImage(matrix_img)
            
            with self.qr_images_lock:
                self.qr_images[i] = photo
            
            current_count += min(qr_per_frame, len(chunks) - i)
            
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
            "chunkSize": len(self.file_data['chunks'][0]) if self.file_data['chunks'] else 0,
            "timestamp": int(time.time())
        }
        
        qr = segno.make(json.dumps(header_info), error='l')
        buffer = BytesIO()
        qr.save(buffer, kind='png', scale=10, border=4)
        buffer.seek(0)
        img = Image.open(buffer)
        img = img.resize((600, 600), Image.Resampling.NEAREST)
        return ImageTk.PhotoImage(img)
    
    def _create_photo_optimized_matrix(self, start_index, cols, rows, qr_per_frame, page_number, total_pages):
        """写真撮影に最適化されたQRマトリックス（4隅に制御QR）"""
        qr_size = self.photo_optimized_qr_size
        padding = 5
        matrix_width = cols * qr_size + padding * 2
        matrix_height = rows * qr_size + padding * 2 + 50  # ヘッダー用のスペース
        matrix = Image.new('RGB', (matrix_width, matrix_height), 'white')
        draw = ImageDraw.Draw(matrix)
        
        # ヘッダー情報を描画
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        header_text = f"ページ {page_number}/{total_pages} - チャンク {start_index + 1}-{min(start_index + qr_per_frame, len(self.file_data['chunks']))}"
        draw.text((matrix_width // 2, 25), header_text, fill="black", font=font, anchor="mm")
        
        chunks = self.file_data['chunks']
        chunk_offset = 0
        
        # 各位置にQRコードを配置
        for row in range(rows):
            for col in range(cols):
                x = col * qr_size + padding
                y = row * qr_size + padding + 50  # ヘッダー分のオフセット
                
                # 4隅の制御QRコード
                if (row == 0 and col == 0):  # 左上
                    control_data = {
                        "type": "control",
                        "position": "top-left",
                        "page": page_number,
                        "total": total_pages,
                        "timestamp": int(time.time())
                    }
                    qr = segno.make(json.dumps(control_data), error='m')
                    buffer = BytesIO()
                    qr.save(buffer, kind='png', scale=3, border=1, dark='blue', light='lightblue')
                    buffer.seek(0)
                    qr_img = Image.open(buffer)
                    qr_img = qr_img.resize((qr_size - 10, qr_size - 10), Image.Resampling.NEAREST)
                    matrix.paste(qr_img, (x + 5, y + 5))
                    # ラベル
                    draw.text((x + qr_size // 2, y + qr_size + 2), "制御-左上", fill="blue", font=font, anchor="mt")
                    
                elif (row == 0 and col == cols - 1):  # 右上
                    control_data = {
                        "type": "control",
                        "position": "top-right",
                        "page": page_number,
                        "total": total_pages,
                        "timestamp": int(time.time())
                    }
                    qr = segno.make(json.dumps(control_data), error='m')
                    buffer = BytesIO()
                    qr.save(buffer, kind='png', scale=3, border=1, dark='red', light='pink')
                    buffer.seek(0)
                    qr_img = Image.open(buffer)
                    qr_img = qr_img.resize((qr_size - 10, qr_size - 10), Image.Resampling.NEAREST)
                    matrix.paste(qr_img, (x + 5, y + 5))
                    draw.text((x + qr_size // 2, y + qr_size + 2), "制御-右上", fill="red", font=font, anchor="mt")
                    
                elif (row == rows - 1 and col == 0):  # 左下
                    control_data = {
                        "type": "control",
                        "position": "bottom-left",
                        "page": page_number,
                        "total": total_pages,
                        "timestamp": int(time.time())
                    }
                    qr = segno.make(json.dumps(control_data), error='m')
                    buffer = BytesIO()
                    qr.save(buffer, kind='png', scale=3, border=1, dark='orange', light='#FFE5B4')
                    buffer.seek(0)
                    qr_img = Image.open(buffer)
                    qr_img = qr_img.resize((qr_size - 10, qr_size - 10), Image.Resampling.NEAREST)
                    matrix.paste(qr_img, (x + 5, y + 5))
                    draw.text((x + qr_size // 2, y - 2), "制御-左下", fill="orange", font=font, anchor="mb")
                    
                elif (row == rows - 1 and col == cols - 1):  # 右下
                    control_data = {
                        "type": "control",
                        "position": "bottom-right",
                        "page": page_number,
                        "total": total_pages,
                        "timestamp": int(time.time())
                    }
                    qr = segno.make(json.dumps(control_data), error='m')
                    buffer = BytesIO()
                    qr.save(buffer, kind='png', scale=3, border=1, dark='green', light='lightgreen')
                    buffer.seek(0)
                    qr_img = Image.open(buffer)
                    qr_img = qr_img.resize((qr_size - 10, qr_size - 10), Image.Resampling.NEAREST)
                    matrix.paste(qr_img, (x + 5, y + 5))
                    draw.text((x + qr_size // 2, y - 2), "制御-右下", fill="green", font=font, anchor="mb")
                    
                else:
                    # 通常のチャンクQRコード
                    chunk_index = start_index + chunk_offset
                    if chunk_index < len(chunks):
                        chunk_data = {
                            "type": "chunk",
                            "chunkIndex": chunk_index,
                            "data": chunks[chunk_index]
                        }
                        
                        qr = segno.make(json.dumps(chunk_data), error='m')
                        buffer = BytesIO()
                        qr.save(buffer, kind='png', scale=3, border=1)
                        buffer.seek(0)
                        qr_img = Image.open(buffer)
                        qr_img = qr_img.resize((qr_size - 10, qr_size - 10), Image.Resampling.NEAREST)
                        matrix.paste(qr_img, (x + 5, y + 5))
                        
                        # チャンク番号を表示
                        draw.text((x + qr_size // 2, y + qr_size // 2), 
                                str(chunk_index), 
                                fill="red", font=font, anchor="mm")
                        
                        chunk_offset += 1
                    else:
                        # 空のスペースに「終了」マーク
                        draw.rectangle([x + 5, y + 5, x + qr_size - 5, y + qr_size - 5], 
                                     outline="gray", width=2)
                        draw.text((x + qr_size // 2, y + qr_size // 2), 
                                "空", fill="gray", font=font, anchor="mm")
            
        # グリッド線を描画（デバッグ用）
        for i in range(cols + 1):
            x = i * qr_size + padding
            draw.line([(x, 50), (x, matrix_height)], fill="lightgray", width=1)
        for i in range(rows + 1):
            y = i * qr_size + padding + 50
            draw.line([(0, y), (matrix_width, y)], fill="lightgray", width=1)
            
        return matrix
        
    def _create_qr_matrix(self, start_index, cols, rows, adjusted_qr_per_frame, page_number, photo_mode=False):
        """QRコードマトリックス生成（動画用）"""
        qr_size = self.standard_qr_size if not photo_mode else self.photo_optimized_qr_size
        matrix_width = cols * qr_size
        matrix_height = rows * qr_size
        matrix = Image.new('RGB', (matrix_width, matrix_height), 'white')
        
        chunks = self.file_data['chunks']
        total_pages = (len(chunks) + adjusted_qr_per_frame - 1) // adjusted_qr_per_frame
        
        # 各位置にQRコードを配置
        chunk_offset = 0
        for i in range(cols * rows):
            row = i // cols
            col = i % cols
            x = col * qr_size + 10
            y = row * qr_size + 10
            
            # 左上（0,0）の位置
            if row == 0 and col == 0:
                # 左上の制御QRコード（青）
                control_data = {
                    "type": "control",
                    "position": "top-left",
                    "page": page_number,
                    "total": total_pages,
                    "timestamp": int(time.time())
                }
                
                qr = segno.make(json.dumps(control_data), error='l')
                buffer = BytesIO()
                qr.save(buffer, kind='png', scale=4, border=1, dark='blue', light='white')
                buffer.seek(0)
                qr_img = Image.open(buffer)
                qr_img = qr_img.resize((qr_size - 20, qr_size - 20), Image.Resampling.NEAREST)
                matrix.paste(qr_img, (x, y))
                
            # 右下（最後の行、最後の列）の位置
            elif row == rows - 1 and col == cols - 1:
                # 右下の制御QRコード（緑）
                control_data = {
                    "type": "control",
                    "position": "bottom-right",
                    "page": page_number,
                    "total": total_pages,
                    "timestamp": int(time.time())
                }
                
                qr = segno.make(json.dumps(control_data), error='l')
                buffer = BytesIO()
                qr.save(buffer, kind='png', scale=4, border=1, dark='green', light='white')
                buffer.seek(0)
                qr_img = Image.open(buffer)
                qr_img = qr_img.resize((qr_size - 20, qr_size - 20), Image.Resampling.NEAREST)
                matrix.paste(qr_img, (x, y))
                
            else:
                # 通常のチャンクQRコード
                chunk_index = start_index + chunk_offset
                if chunk_index < len(chunks):
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
                    matrix.paste(qr_img, (x, y))
                    
                    chunk_offset += 1
            
        return matrix
        
    def get_image(self, key):
        """画像取得"""
        with self.qr_images_lock:
            return self.qr_images.get(key)
            
    def get_chunk_count(self):
        """チャンク数取得"""
        return len(self.file_data['chunks']) if self.file_data else 0
        
    def get_photo_optimized_settings(self):
        """写真最適化設定を取得"""
        # 画面サイズに基づいて最適なグリッドサイズを計算
        return {
            'qr_size': self.photo_optimized_qr_size,
            'min_cols': 5,
            'min_rows': 4,
            'min_qr_count': 20  # 制御QR込みで最低20個
        }
        
    def create_control_qr(self, control_type):
        """制御用QRコード生成"""
        control_data = {
            "type": "control",
            "action": control_type,
            "timestamp": int(time.time())
        }
        
        qr = segno.make(json.dumps(control_data), error='l')
        buffer = BytesIO()
        qr.save(buffer, kind='png', scale=10, border=4)
        buffer.seek(0)
        img = Image.open(buffer)
        img = img.resize((600, 600), Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(img)

        # 制御QRイメージを保持（ガベージコレクション防止）
        with self.qr_images_lock:
            self.control_qr_images[control_type] = photo

        return photo