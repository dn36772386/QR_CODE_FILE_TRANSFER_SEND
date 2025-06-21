# QR Matrix File Transfer - 送信側 (Windows)

高速QRコード転送システムの送信側アプリケーションです。

## セットアップ

### 方法1: VSCode内でのセットアップ

1. VSCodeでフォルダを開く
2. ターミナルを開く（Ctrl+`）
3. 以下のコマンドを実行：

```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化
.\venv\Scripts\activate

# パッケージインストール
pip install -r requirements.txt