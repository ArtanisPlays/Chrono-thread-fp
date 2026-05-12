import tkinter as tk
from tkinter import messagebox
import json
import os

# --- KONFIGURASI VISUAL ---
COLORS = {
    'empty': '#333333',
    'wall': '#111111',
    'start': '#00BFFF',   # Biru
    'finish': '#32CD32',  # Hijau
    'door': '#8B4513',    # Coklat
    'button': '#FFD700',  # Emas
    'block': '#888888'    # Abu-abu
}

class LevelEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Chrono-Thread Level Editor")
        self.root.configure(bg="#222")
        
        self.cell_size = 40
        self.grid_width = 10
        self.grid_height = 10
        self.current_brush = 'wall'
        
        # Format: {(x, y): 'type'}
        self.grid_data = {} 
        
        self.setup_ui()
        self.draw_grid()

    def setup_ui(self):
        # --- PANEL KIRI (PENGATURAN & TOOLS) ---
        left_panel = tk.Frame(self.root, bg="#222", padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left_panel, text="Level ID:", fg="white", bg="#222").pack(anchor=tk.W)
        self.entry_id = tk.Entry(left_panel, width=20)
        self.entry_id.insert(0, "3")
        self.entry_id.pack(pady=(0, 10))

        tk.Label(left_panel, text="Nama Level:", fg="white", bg="#222").pack(anchor=tk.W)
        self.entry_name = tk.Entry(left_panel, width=20)
        self.entry_name.insert(0, "Level 3: Custom")
        self.entry_name.pack(pady=(0, 20))

        tk.Label(left_panel, text="Pilih Kuas (Brush):", fg="white", bg="#222").pack(anchor=tk.W)
        
        brushes = [
            ('Tembok (Wall)', 'wall'),
            ('Movable Block', 'block'),
            ('Tombol (Button)', 'button'),
            ('Pintu (Door)', 'door'),
            ('Start (Player)', 'start'),
            ('Finish', 'finish'),
            ('Hapus (Eraser)', 'empty')
        ]

        for text, val in brushes:
            btn = tk.Button(left_panel, text=text, bg=COLORS.get(val, 'white'), 
                            fg="white" if val in ['wall', 'empty', 'door'] else "black",
                            command=lambda v=val: self.set_brush(v))
            btn.pack(fill=tk.X, pady=2)

        tk.Button(left_panel, text="💾 SAVE KE JSON", bg="#4CAF50", fg="white", 
                  font=("Arial", 10, "bold"), command=self.save_level).pack(pady=20, fill=tk.X)

        # --- PANEL KANAN (CANVAS) ---
        self.canvas = tk.Canvas(self.root, width=self.grid_width * self.cell_size, 
                                height=self.grid_height * self.cell_size, bg=COLORS['empty'])
        self.canvas.pack(side=tk.RIGHT, padx=20, pady=20)
        
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<Button-1>", self.paint)

    def set_brush(self, brush_type):
        self.current_brush = brush_type

    def paint(self, event):
        x = event.x // self.cell_size
        y = event.y // self.cell_size
        
        if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
            # Aturan: Hanya boleh ada 1 Start dan 1 Finish
            if self.current_brush in ['start', 'finish']:
                # Hapus yang lama dulu
                to_delete = [k for k, v in self.grid_data.items() if v == self.current_brush]
                for k in to_delete:
                    del self.grid_data[k]
                    
            if self.current_brush == 'empty':
                if (x, y) in self.grid_data:
                    del self.grid_data[(x, y)]
            else:
                self.grid_data[(x, y)] = self.current_brush
                
            self.draw_grid()

    def draw_grid(self):
        self.canvas.delete("all")
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                x0, y0 = x * self.cell_size, y * self.cell_size
                x1, y1 = x0 + self.cell_size, y0 + self.cell_size
                
                cell_type = self.grid_data.get((x, y), 'empty')
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=COLORS[cell_type], outline="#444")

    def save_level(self):
        # Ekstrak data dari grid
        start = None
        finish = None
        walls, blocks, doors, buttons = [], [], [], []

        for (x, y), c_type in self.grid_data.items():
            if c_type == 'start': start = [x, y]
            elif c_type == 'finish': finish = [x, y]
            elif c_type == 'wall': walls.append([x, y])
            elif c_type == 'block': blocks.append([x, y])
            elif c_type == 'door': doors.append([x, y])
            elif c_type == 'button': buttons.append({"pos": [x, y], "targets": []})

        if not start or not finish:
            messagebox.showerror("Error", "Level harus memiliki titik Start dan Finish!")
            return

        # Auto-Link: Untuk kemudahan, setiap tombol di editor ini akan menargetkan SEMUA pintu di level.
        for btn in buttons:
            btn['targets'] = doors.copy()

        level_obj = {
            "id": int(self.entry_id.get()),
            "name": self.entry_name.get(),
            "width": self.grid_width,
            "height": self.grid_height,
            "start": start,
            "finish": finish,
            "walls": walls,
            "movable_blocks": blocks,
            "doors": doors,
            "buttons": buttons
        }

        # Baca file lama, timpa/tambah, lalu simpan
        filepath = 'levels.json'
        data = {"levels": []}
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)

        # Cek apakah ID sudah ada (jika ya, timpa level tersebut)
        existing_idx = next((i for i, l in enumerate(data['levels']) if l['id'] == level_obj['id']), None)
        if existing_idx is not None:
            data['levels'][existing_idx] = level_obj
        else:
            data['levels'].append(level_obj)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        messagebox.showinfo("Sukses", f"Level '{level_obj['name']}' berhasil disimpan ke levels.json!")

if __name__ == "__main__":
    root = tk.Tk()
    app = LevelEditor(root)
    root.mainloop()
