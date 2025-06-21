"""
UIコンポーネント
"""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox

class ControlPanel:
    def __init__(self, parent, on_file_selected, on_start, on_stop):
        self.on_file_selected = on_file_selected
        self.on_start = on_start
        self.on_stop = on_stop
        
        # コントロールパネル
        self.panel = tk.Frame(parent, bg='#f0f0f0', height=100)
        self.panel.pack(fill=tk.X, padx=10, pady=5)
        self.panel.pack_propagate(False)
        
        self.setup_controls()
        
    def setup_controls(self):
        """コントロール設定"""
        # ファイル選択エリア
        file_frame = tk.Frame(self.panel, bg='#f0f0f0')
        file_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.select_btn = tk.Button(
            file_frame,
            text="📁 ファイル選択",
            command=self.select_file,
            font=('Arial', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=20,
            pady=10
        )
        self.select_btn.pack(side=tk.TOP)
        
        self.file_label = tk.Label(
            file_frame,
            text="ファイルが選択されていません",
            bg='#f0f0f0',
            font=('Arial', 10)
        )
        self.file_label.pack(side=tk.TOP, pady=(5, 0))
        
        # 設定エリア
        settings_frame = tk.Frame(self.panel, bg='#f0f0f0')
        settings_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        tk.Label(settings_frame, text="設定", font=('Arial', 12, 'bold'), bg='#f0f0f0').pack()
        
        # チャンクサイズ設定
        chunk_frame = tk.Frame(settings_frame, bg='#f0f0f0')
        chunk_frame.pack(pady=2)
        tk.Label(chunk_frame, text="チャンクサイズ:", bg='#f0f0f0').pack(side=tk.LEFT)
        self.chunk_size_var = tk.StringVar(value="800")
        self.chunk_size_combo = ttk.Combobox(
            chunk_frame,
            textvariable=self.chunk_size_var,
            values=["300", "500", "600", "800", "1000"],
            width=10,
            state="readonly"
        )
        self.chunk_size_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # FPS設定
        fps_frame = tk.Frame(settings_frame, bg='#f0f0f0')
        fps_frame.pack(pady=2)
        tk.Label(fps_frame, text="FPS:", bg='#f0f0f0').pack(side=tk.LEFT)
        self.fps_var = tk.IntVar(value=5)
        tk.Spinbox(
            fps_frame,
            from_=3,
            to=10,
            textvariable=self.fps_var,
            width=10
        ).pack(side=tk.LEFT)
        
        # 送信コントロール
        control_frame = tk.Frame(self.panel, bg='#f0f0f0')
        control_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.start_btn = tk.Button(
            control_frame,
            text="▶️ 送信開始",
            command=lambda: self.on_start(self.fps_var.get()),
            font=('Arial', 14, 'bold'),
            bg='#2196F3',
            fg='white',
            padx=30,
            pady=10,
            state=tk.DISABLED
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            control_frame,
            text="⏹️ 停止",
            command=self.on_stop,
            font=('Arial', 14, 'bold'),
            bg='#f44336',
            fg='white',
            padx=30,
            pady=10,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
    def select_file(self):
        """ファイル選択"""
        file_path = filedialog.askopenfilename(
            title="送信するファイルを選択",
            filetypes=[("すべてのファイル", "*.*")]
        )
        
        if file_path:
            self.file_label.config(text=f"📄 {file_path.split('/')[-1]}")
            self.on_file_selected(file_path)
            
    def enable_transmission(self):
        """送信ボタン有効化"""
        self.start_btn.config(state=tk.NORMAL)


class QRDisplayCanvas:
    def __init__(self, parent):
        self.qr_size = 250
        
        self.canvas = tk.Canvas(
            parent,
            bg='white',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
    def get_matrix_size(self):
        """マトリックスサイズ取得"""
        self.canvas.update()
        width = self.canvas.winfo_width() - 40
        height = self.canvas.winfo_height() - 40
        
        cols = max(1, width // self.qr_size)
        rows = max(1, height // self.qr_size)
        
        return cols, rows, cols * rows
        
    def clear(self):
        """キャンバスクリア"""
        self.canvas.delete("all")
        
    def display_image(self, image, x, y, anchor=tk.CENTER):
        """画像表示"""
        self.canvas.create_image(x, y, image=image, anchor=anchor)
        
    def display_text(self, x, y, text, font, fill='black'):
        """テキスト表示"""
        self.canvas.create_text(x, y, text=text, font=font, fill=fill)
        
    def get_center(self):
        """中心座標取得"""
        self.canvas.update()
        return self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2


class StatusBar:
    def __init__(self, parent, screen_width):
        # ステータス表示
        status_frame = tk.Frame(parent, bg='white')
        status_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="待機中",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='#666'
        )
        self.status_label.pack()
        
        self.progress_label = tk.Label(
            status_frame,
            text="",
            font=('Arial', 10),
            bg='white'
        )
        self.progress_label.pack()
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            parent,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=screen_width - 40
        )
        self.progress_bar.pack(fill=tk.X, padx=20, pady=(0, 10))
        
    def set_status(self, text, color='#666'):
        """ステータス設定"""
        self.status_label.config(text=text, fg=color)
        
    def update_progress(self, progress, text):
        """進捗更新"""
        self.progress_var.set(progress)
        self.progress_label.config(text=text)
        
    def update_generation_progress(self, progress, message):
        """生成進捗更新"""
        self.progress_var.set(progress)
        self.status_label.config(text=message, fg='#2196F3')
