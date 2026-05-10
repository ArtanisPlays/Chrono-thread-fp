import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import heapq
import json

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- 1. ALGORITMA CORE ---
def manhattan_distance(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])

class GridMap:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.walls = set()            
        self.closed_doors = set()     
        self.movable_blocks = set()   

    def is_blocked(self, pos):
        # Keluar batas peta
        if not (0 <= pos[0] < self.width and 0 <= pos[1] < self.height): return True
        # Menabrak objek padat
        if pos in self.walls: return True
        if pos in self.closed_doors: return True
        if pos in self.movable_blocks: return True
        return False

    def get_neighbors(self, pos):
        x, y = pos
        directions = [(x, y-1), (x, y+1), (x-1, y), (x+1, y)]
        return [n for n in directions if not self.is_blocked(n)]
    
    # --- Logika Peta yang Menangani Dorongan ---
    def push_block(self, from_pos, block_pos, occupied_positions):
        if block_pos in self.movable_blocks:
            dx = block_pos[0] - from_pos[0]
            dy = block_pos[1] - from_pos[1]
            push_target = (block_pos[0] + dx, block_pos[1] + dy)
            
            # Jika di belakang balok kosong, geser
            if not self.is_blocked(push_target) and push_target not in occupied_positions:
                self.movable_blocks.remove(block_pos)
                self.movable_blocks.add(push_target)
                return True
            return False
        return False # Bukan balok
    
def a_star_search(grid, start, goal):
    frontier = []
    heapq.heappush(frontier, (0, start))
    came_from, cost_so_far = {start: None}, {start: 0}
    
    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal: break
        for next_node in grid.get_neighbors(current):
            new_cost = cost_so_far[current] + 1
            if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                cost_so_far[next_node] = new_cost
                priority = new_cost + manhattan_distance(next_node, goal)
                heapq.heappush(frontier, (priority, next_node))
                came_from[next_node] = current
                
    if goal not in came_from: return []
    path, current = [], goal
    while current != start:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path

# --- 2. ENTITAS BAYANGAN ---
class AdaptiveShadow:
    def __init__(self, breadcrumbs):
        self.breadcrumbs = breadcrumbs
        self.current_tick = 0
        self.position = breadcrumbs[0]
        self.state = "REPLAYING"
        self.recalculated_path = []

    def tick(self, grid_map, occupied_positions):
        if self.current_tick >= len(self.breadcrumbs) - 1 and self.state == "REPLAYING":
            return self.position    

        if self.state == "REPLAYING":
            next_pos = self.breadcrumbs[self.current_tick + 1]

            # Bayangan mencoba mendorong objek di depannya
            grid_map.push_block(self.position, next_pos, occupied_positions)

            if grid_map.is_blocked(next_pos) and self.current_tick < len(self.breadcrumbs) - 2: # BUTTERFLY EFFECT DETECTED
                # We skip this tile and go to the next one
                next_pos = self.breadcrumbs[self.current_tick + 2]
                self.state = "PATHFINDING"
                self.recalculated_path = a_star_search(grid_map, self.position, next_pos)
            else:
                self.position = next_pos
            
            self.current_tick += 1

        if self.state == "PATHFINDING" and self.recalculated_path:
            next_ai_pos = self.recalculated_path[0]
            # Validasi ulang jika tiba-tiba ada balok baru yang didorong pemain ke jalur A*
            if not grid_map.is_blocked(next_ai_pos):
                self.position = self.recalculated_path.pop(0)
            else:
                # Kalkulasi ulang jalan jika terblokir lagi
                self.recalculated_path = a_star_search(grid_map, self.position, self.current_tick + 2)
        elif self.state == "PATHFINDING":
            self.state = "REPLAYING"


        return self.position

class GameState:
    def __init__(self):
        self.levels_data = self.load_json()
        self.current_level_id = 1
        self.load_level(self.current_level_id)

    def load_json(self):
        with open('levels.json', 'r') as f:
            return json.load(f)['levels']

    def load_level(self, level_id):
        level = next(l for l in self.levels_data if l['id'] == level_id)
        
        self.grid = GridMap(level['width'], level['height'])
        self.grid.walls = set(tuple(w) for w in level['walls'])
        self.movable_blocks_original_pos = set(tuple(b) for b in level.get('movable_blocks', []))
        self.grid.movable_blocks = self.movable_blocks_original_pos.copy()
        
        self.doors = set(tuple(d) for d in level.get('doors', []))
        self.buttons = level.get('buttons', [])
        self.finish = tuple(level['finish'])
        
        self.start_pos = tuple(level['start'])
        self.player = self.start_pos
        self.log = [self.start_pos]
        self.shadows = []
        self.is_recording = False
        self.is_won = False # Tambahkan status kemenangan
        self.update_mechanics() # Jalankan logika pertama kali

    def update_mechanics(self):
        # 1. Kumpulkan semua entitas yang ada di peta (Pemain + Bayangan)
        occupied_positions = {self.player}
        for s in self.shadows:
            occupied_positions.add(s.position)

        # 2. Cek tombol mana yang sedang diinjak
        pressed_targets = set()
        for btn in self.buttons:
            if tuple(btn['pos']) in occupied_positions:
                for t in btn['targets']:
                    pressed_targets.add(tuple(t))

        # 3. Buka/Tutup Pintu
        self.grid.closed_doors = set()
        for door in self.doors:
            if door not in pressed_targets:
                self.grid.closed_doors.add(door) # Tutup pintu jika tidak diinjak

    def reset(self):
        # Reset sekarang mengembalikan map ke kondisi awal level tersebut
        self.load_level(self.current_level_id)

    def rewind(self):
        # Hanya simpan bayangan jika pemain benar-benar sudah bergerak (Log > 1)
        if len(self.log) > 1:
            self.shadows.append(AdaptiveShadow(self.log.copy()))

        self.grid.movable_blocks = self.movable_blocks_original_pos.copy()
            
        self.player = self.start_pos
        self.log = [self.start_pos]
        self.is_recording = False # Jeda rekaman lagi untuk timeline baru
        self.update_mechanics() # Jalankan logika pertama kali
        
        # Kembalikan semua bayangan ke garis start
        for shadow in self.shadows:
            shadow.current_tick = 0
            shadow.state = "WAITING"
            shadow.position = shadow.breadcrumbs[0]


    def move_player(self, dx, dy):
        # Jangan izinkan pemain bergerak jika sudah menang
        if self.is_won: return

        if self.is_recording == False:
            for shadow in self.shadows:
                shadow.state = "REPLAYING"
                
        self.is_recording = True

        target_x, target_y = self.player[0] + dx, self.player[1] + dy
        target_pos = (target_x, target_y)

        occupied_positions = {self.player}
        for s in self.shadows:
            occupied_positions.add(s.position)

        # Minta peta untuk mendorong balok (jika ada balok di target)
        self.grid.push_block(self.player, target_pos, occupied_positions)

        # Jika jalur aman (atau balok baru saja berhasil didorong), majulah
        if not self.grid.is_blocked(target_pos):
            self.player = target_pos

            # CEK KONDISI MENANG
            if self.player == self.finish:
                self.is_won = True
                self.is_recording = False # Hentikan rekaman waktu

game = GameState()

async def server_game_loop():
    while True:
        game.update_mechanics() # Sinkronisasi pintu sebelum bayangan bergerak
        
        if game.is_recording == True:
            game.log.append(game.player)

        occupied_positions = {game.player}
        for s in game.shadows:
            occupied_positions.add(s.position)
            
        for shadow in game.shadows: 
            shadow.tick(game.grid, occupied_positions)
            
        game.update_mechanics() # Sinkronisasi lagi setelah bayangan bergerak
        await asyncio.sleep(0.15)


# Nyalakan mesin saat server Uvicorn pertama kali jalan
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(server_game_loop())

# Endpoint baru untuk mengganti level
@app.post("/load_level/{level_id}")
def api_load_level(level_id: int):
    game.current_level_id = level_id
    game.load_level(level_id)
    return {"status": "success"}

# Update Endpoint State
@app.get("/state")
def get_state():
    return {
        "width": game.grid.width,
        "height": game.grid.height,
        "player": game.player,
        "shadows": [s.position for s in game.shadows],
        "walls": list(game.grid.walls),
        "doors": list(game.grid.closed_doors),
        "buttons": [b['pos'] for b in game.buttons],
        "movable_blocks": list(game.grid.movable_blocks),
        "finish": game.finish,
        "is_won": game.is_won, # Kirim status menang ke Frontend
        "stats": {
            "shadows_used": len(game.shadows),
            "moves_done": len(game.log) - 1 # Kurangi 1 karena log awal adalah spawn statis
        }
    }

@app.post("/action/{action_type}")
def do_action(action_type: str, x: int = 0, y: int = 0):
    if action_type == "up": game.move_player(0, -1)
    elif action_type == "down": game.move_player(0, 1)
    elif action_type == "left": game.move_player(-1, 0)
    elif action_type == "right": game.move_player(1, 0)
    elif action_type == "rewind": game.rewind()
    elif action_type == "reset": game.reset() 
    # elif action_type == "wall": game.grid.walls.add((x, y))
    return {"status": "success"}

@app.get("/levels_info")
def get_levels_info():
    # Ambil hanya ID dan Nama dari setiap level di JSON
    levels_list = []
    for level in game.levels_data:
        levels_list.append({"id": level["id"], "name": level["name"]})
    return levels_list