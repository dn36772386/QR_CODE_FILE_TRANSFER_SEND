"""
ファイル処理モジュール
"""

import base64
from pathlib import Path
from typing import Optional, Dict, Any

# Zstandard圧縮のインポート（オプション）
try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False
    import gzip

class FileProcessor:
    def __init__(self, chunk_size=800, compression_level=3):
        self.chunk_size = chunk_size
        self.compression_level = compression_level
        
    def process_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """ファイル処理"""
        path = Path(file_path)
        if not path.exists():
            return None
            
        try:
            # ファイル読み込み
            with open(path, 'rb') as f:
                file_data = f.read()
            
            file_size = len(file_data)
            
            # 圧縮
            compressed_data = self.compress_data(file_data)
            compressed_size = len(compressed_data)
            
            # Base64エンコード
            encoded_data = base64.b64encode(compressed_data).decode('utf-8')
            
            # チャンク分割
            chunks = []
            for i in range(0, len(encoded_data), self.chunk_size):
                chunks.append(encoded_data[i:i + self.chunk_size])
            
            return {
                'file_name': path.name,
                'file_type': path.suffix,
                'original_size': file_size,
                'compressed_size': compressed_size,
                'chunks': chunks,
                'compression_type': 'zstd' if HAS_ZSTD else 'gzip'
            }
            
        except Exception as e:
            print(f"ファイル処理エラー: {str(e)}")
            return None
            
    def compress_data(self, data: bytes) -> bytes:
        """データ圧縮"""
        if HAS_ZSTD:
            cctx = zstd.ZstdCompressor(level=self.compression_level)
            return cctx.compress(data)
        else:
            return gzip.compress(data, compresslevel=self.compression_level)
