"""
ユーティリティ関数
"""

def format_size(bytes: int) -> str:
    """ファイルサイズフォーマット"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"
