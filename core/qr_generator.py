"""
QRコード生成モジュール（簡略化版）
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
        # 写真撮影用に最適化されたサイズ
        self.photo_optimized_qr_size = 150
        
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
            
            # 写真モード用のグリッドサイズを使用
            max_cols = max(5, cols)  # 最低5列
            max_rows = max(4, rows)  # 最低4行
            
            # 4隅の制御QR分を引く（実際の配置に基づく）
            adjusted_qr_per_frame = (max_cols * max_rows) - 4
            total_pages = (len(chunks) + adjusted_qr_per_frame - 1) // adjusted_qr_per_frame
            
            print(f"=== QR生成設定 ===")
            print(f"グリッド: {max_cols}x{max_rows} = {max_cols * max_rows}個")
            print(f"制御QR: 4個")
            print(f"データQR/ページ: {adjusted_qr_per_frame}個")
            print(f"総チャンク数: {len(chunks)}")
            print(f"総ページ数: {total_pages}")
            
            # ヘッダー生成（総ページ数を含む）
            progress_callback(0, "ヘッダーQRコード生成中...")
            header_img = self._create_header_qr(total_pages)
            with self.qr_images_lock:
                self.qr_images['header'] = header_img
            progress_callback(10, "ヘッダー生成完了")
            
            # チャンクマトリックス生成（写真モード）
            self._generate_photo_optimized_matrices(
                chunks, max_cols, max_rows, progress_callback, adjusted_qr_per_frame, total_pages
            )
                
            complete_callback()
            
        finally:
            self.is_generating = False
    
    def _generate_photo_optimized_matrices(self, chunks, cols, rows, progress_callback, adjusted_qr_per_frame, total_pages):
        """写真撮影に最適化されたマトリックス生成"""
        # より多くのQRコードを配置するための計算
        max_cols = max(5, cols)  # 最低5列
        max_rows = max(4, rows)  # 最低4行
        
        total_count = len(chunks)
        current_count = 0
        
        for i in range(0, len(chunks), adjusted_qr_per_frame):
            page_number = (i // adjusted_qr_per_frame) + 1
            
            msg = f"写真用マトリックス生成中... ページ {page_number}/{total_pages}"
            progress = 10 + (current_count / total_count) * 90
            progress_callback(progress, msg)
            
            matrix_img = self._create_photo_optimized_matrix(
                i, max_cols, max_rows, adjusted_qr_per_frame, page_number, total_pages
            )
            photo = ImageTk.PhotoImage(matrix_img)
            
            with self.qr_images_lock:
                self.qr_images[i] = photo
            
            current_count += min(adjusted_qr_per_frame, len(chunks) - i)
            
    def _create_header_qr(self, total_pages):
        """ヘッダーQRコード生成（総ページ数を含む）"""
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
            "totalPages": total_pages,  # 総ページ数（必要な写真枚数）を追加
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
            small_font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
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
                    draw.text((x + qr_size // 2, y + qr_size + 2), "制御-左上", fill="blue", font=small_font, anchor="mt")
                    
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
                    draw.text((x + qr_size // 2, y + qr_size + 2), "制御-右上", fill="red", font=small_font, anchor="mt")
                    
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
                    draw.text((x + qr_size // 2, y - 2), "制御-左下", fill="orange", font=small_font, anchor="mb")
                    
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
                    draw.text((x + qr_size // 2, y - 2), "制御-右下", fill="green", font=small_font, anchor="mb")
                    
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
        
    def get_image(self, key):
        """画像取得"""
        with self.qr_images_lock:
            return self.qr_images.get(key)
            
    def get_chunk_count(self):
        """チャンク数取得"""
        return len(self.file_data['chunks']) if self.file_data else 0