@echo off
echo QR Matrix File Transfer - セットアップ
echo =====================================
echo.

:: Python確認
python --version >nul 2>&1
if errorlevel 1 (
    echo エラー: Pythonがインストールされていません
    echo https://www.python.org/ からPythonをインストールしてください
    pause
    exit /b 1
)

echo Pythonが検出されました
echo.

:: 仮想環境作成
echo 仮想環境を作成しています...
python -m venv venv

:: 仮想環境有効化
echo 仮想環境を有効化しています...
call venv\Scripts\activate.bat

:: パッケージインストール
echo 必要なパッケージをインストールしています...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo セットアップが完了しました！
echo.
echo 実行方法:
echo   run.bat
echo.
pause
