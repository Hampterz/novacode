import tkinter as tk
import serial
import serial.tools.list_ports
import time
import threading
import math
import queue
from tkinter import filedialog, messagebox
try:
    from PIL import Image
except ImportError:
    pass

MODE_NAMES = {0: "--", 1: "March", 2: "Walk", 3: "Freestyle", 4: "Trot", 5: "Follow"}

# ============================================================
# Radar Configuration  — Forward-Facing Dual-Cone Display
# ============================================================
RADAR_W = 420             # Canvas width
RADAR_H = 340             # Canvas height
RADAR_MAX_CM = 200        # Max displayed range in cm
RADAR_ARCS = [50, 100, 150, 200]   # Distance arcs in cm
RADAR_BG = "#060d06"      # Deep dark green-black
RADAR_ARC_COLOR = "#163016"
RADAR_GRID_COLOR = "#0f240f"
RADAR_TEXT_COLOR = "#2a6a2a"
RADAR_GLOW = "#00ff41"    # Bright green accent

# Sensor cone geometry (degrees from vertical center-line, 0 = straight ahead)
# Left sensor points ~30° to the left, right ~30° to the right
# Each sensor has a ±15° beam width (typical HC-SR04 is ~15° half-angle)
LEFT_CENTER_DEG = -25     # Negative = left of center
RIGHT_CENTER_DEG = 25     # Positive = right of center
BEAM_HALF_WIDTH = 15      # Half-angle of each sensor cone

BLIP_TRAIL_LENGTH = 30    # Increased trail length for longer persistence
PERSISTENCE_TICKS = 15    # How long to hold the last valid reading before dropping to 0 (1.5 seconds)


class RadarCanvas:
    """Forward-facing dual-cone ultrasonic radar display."""

    def __init__(self, parent):
        self.canvas = tk.Canvas(
            parent, width=RADAR_W, height=RADAR_H,
            bg=RADAR_BG, highlightthickness=1, highlightbackground="#1a4a1a"
        )
        self.canvas.pack(pady=5)

        # Robot is at the bottom-center of the canvas, sensors face upward
        self.robot_x = RADAR_W // 2
        self.robot_y = RADAR_H - 30  # 30px from bottom for labels
        self.max_radius = RADAR_H - 65  # pixels available for max range

        # Trail history: list of (dist_cm, age)
        self.left_trail = []
        self.right_trail = []
        self.sweep_phase = 0.0  # Animated sweep position 0..1

        # Current distances
        self.dist_left = 0
        self.dist_right = 0
        
        # Debounce/Persistence states
        self.display_left = 0
        self.display_right = 0
        self.left_zero_ticks = 0
        self.right_zero_ticks = 0

        self._draw_static()

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------
    def _cm_to_px(self, cm):
        """Convert a distance in cm to pixels from the robot origin."""
        return int((min(cm, RADAR_MAX_CM) / RADAR_MAX_CM) * self.max_radius)

    def _polar_to_xy(self, dist_cm, angle_deg):
        """Convert (distance_cm, angle_degrees_from_forward) to canvas (x, y).
        0° = straight ahead (up on screen), negative = left, positive = right."""
        r = self._cm_to_px(dist_cm)
        rad = math.radians(angle_deg)
        x = self.robot_x + r * math.sin(rad)
        y = self.robot_y - r * math.cos(rad)
        return int(x), int(y)

    # ------------------------------------------------------------------
    # Static background
    # ------------------------------------------------------------------
    def _draw_static(self):
        """Draw fixed elements: arcs, gridlines, robot icon, labels."""
        rx, ry = self.robot_x, self.robot_y

        # --- Distance arcs (semicircular, only the forward half) ---
        for cm in RADAR_ARCS:
            r = self._cm_to_px(cm)
            # Draw arc from -60° to +60° (the visible cone area)
            self.canvas.create_arc(
                rx - r, ry - r, rx + r, ry + r,
                start=30, extent=120,  # tkinter arc: 0°=3-o'clock, CCW
                style='arc', outline=RADAR_ARC_COLOR, width=1, tags="static"
            )
            # Label at the top of each arc
            lx, ly = self._polar_to_xy(cm, 0)
            self.canvas.create_text(
                lx + 14, ly + 2, text=f"{cm}cm",
                fill=RADAR_TEXT_COLOR, font=("Consolas", 7), anchor="w", tags="static"
            )

        # --- Center line (straight ahead) ---
        x0, y0 = self._polar_to_xy(0, 0)
        x1, y1 = self._polar_to_xy(RADAR_MAX_CM, 0)
        self.canvas.create_line(x0, y0, x1, y1,
                                fill=RADAR_GRID_COLOR, width=1, dash=(3, 6), tags="static")

        # --- Cone boundary lines ---
        for deg in [LEFT_CENTER_DEG - BEAM_HALF_WIDTH,
                    LEFT_CENTER_DEG + BEAM_HALF_WIDTH,
                    RIGHT_CENTER_DEG - BEAM_HALF_WIDTH,
                    RIGHT_CENTER_DEG + BEAM_HALF_WIDTH]:
            ex, ey = self._polar_to_xy(RADAR_MAX_CM, deg)
            self.canvas.create_line(rx, ry, ex, ey,
                                    fill=RADAR_GRID_COLOR, width=1, dash=(2, 8), tags="static")

        # --- Sensor center-line indicators ---
        for deg in [LEFT_CENTER_DEG, RIGHT_CENTER_DEG]:
            ex, ey = self._polar_to_xy(RADAR_MAX_CM, deg)
            self.canvas.create_line(rx, ry, ex, ey,
                                    fill="#1a3a1a", width=1, tags="static")

        # --- Robot body icon (top-down quadruped silhouette) ---
        # Main body rectangle
        bw, bh = 18, 24
        self.canvas.create_rectangle(
            rx - bw//2, ry - bh//2, rx + bw//2, ry + bh//2,
            fill="#0a1a0a", outline=RADAR_GLOW, width=1, tags="static"
        )
        # Head (small triangle pointing up)
        self.canvas.create_polygon(
            rx, ry - bh//2 - 8,
            rx - 6, ry - bh//2,
            rx + 6, ry - bh//2,
            fill="#0a1a0a", outline=RADAR_GLOW, width=1, tags="static"
        )
        # Legs (four small lines)
        for lx_off, ly_off in [(-bw//2 - 4, -8), (-bw//2 - 4, 8),
                                (bw//2 + 4, -8), (bw//2 + 4, 8)]:
            self.canvas.create_line(
                rx + lx_off, ry + ly_off - 4,
                rx + lx_off, ry + ly_off + 4,
                fill=RADAR_GLOW, width=2, tags="static"
            )

        # --- L / R labels at bottom ---
        self.left_label_id = self.canvas.create_text(
            40, RADAR_H - 12, text="L  --cm", fill="#00aa22",
            font=("Consolas", 10, "bold"), anchor="w", tags="static"
        )
        self.right_label_id = self.canvas.create_text(
            RADAR_W - 40, RADAR_H - 12, text="R  --cm", fill="#00aa22",
            font=("Consolas", 10, "bold"), anchor="e", tags="static"
        )

        # --- Title ---
        self.canvas.create_text(
            RADAR_W // 2, 10, text="FORWARD  PROXIMITY",
            fill=RADAR_TEXT_COLOR, font=("Consolas", 8), anchor="n", tags="static"
        )

    # ------------------------------------------------------------------
    # Color mapping
    # ------------------------------------------------------------------
    def _dist_to_color(self, dist_cm):
        """Red (close/danger) → yellow (caution) → green (safe)."""
        if dist_cm <= 0:
            return "#002200"
        if dist_cm < 15:
            return "#ff2020"
        if dist_cm < 50:
            t = (dist_cm - 15) / 35.0
            r = 255
            g = int(50 + t * 205)
            return f"#{r:02x}{g:02x}20"
        if dist_cm < 100:
            t = (dist_cm - 50) / 50.0
            r = int(255 * (1 - t))
            g = 255
            return f"#{r:02x}{g:02x}20"
        return "#00ff41"

    def _fade_color(self, hex_color, factor):
        """Dim a hex color by a factor (0..1)."""
        r = int(int(hex_color[1:3], 16) * factor)
        g = int(int(hex_color[3:5], 16) * factor)
        b = int(int(hex_color[5:7], 16) * factor)
        return f"#{max(r,3):02x}{max(g,3):02x}{max(b,3):02x}"

    # ------------------------------------------------------------------
    # Update / redraw
    # ------------------------------------------------------------------
    def update(self, dist_left, dist_right):
        """Called periodically with new sensor readings."""
        self.dist_left = dist_left
        self.dist_right = dist_right
        
        # Apply persistence filter (reduce stuttering from sudden 0s)
        if dist_left > 0:
            self.display_left = dist_left
            self.left_zero_ticks = 0
        else:
            self.left_zero_ticks += 1
            if self.left_zero_ticks >= PERSISTENCE_TICKS:
                self.display_left = 0
                
        if dist_right > 0:
            self.display_right = dist_right
            self.right_zero_ticks = 0
        else:
            self.right_zero_ticks += 1
            if self.right_zero_ticks >= PERSISTENCE_TICKS:
                self.display_right = 0

        # Only add to trail if we have a reading
        if self.display_left > 0:
            self.left_trail.append((self.display_left, 0))
        if self.display_right > 0:
            self.right_trail.append((self.display_right, 0))

        # Age and trim trails
        self.left_trail = [(d, a + 1) for d, a in self.left_trail if a < BLIP_TRAIL_LENGTH]
        self.right_trail = [(d, a + 1) for d, a in self.right_trail if a < BLIP_TRAIL_LENGTH]

        self.sweep_phase = (self.sweep_phase + 0.04) % 1.0
        self._redraw()

    def _redraw(self):
        self.canvas.delete("dynamic")
        rx, ry = self.robot_x, self.robot_y

        # --- Animated sweep within each cone ---
        self._draw_sweep(LEFT_CENTER_DEG)
        self._draw_sweep(RIGHT_CENTER_DEG)

        # --- Danger zone fill (if object < 15cm) ---
        for dist, center_deg in [(self.display_left, LEFT_CENTER_DEG),
                                  (self.display_right, RIGHT_CENTER_DEG)]:
            if 0 < dist < 30:
                alpha = max(0.05, 0.25 * (1.0 - dist / 30.0))
                r_val = int(255 * alpha)
                g_val = int(30 * alpha)
                danger_color = f"#{r_val:02x}{g_val:02x}05"
                # Fill a polygon for the danger zone
                pts = [(rx, ry)]
                lo = center_deg - BEAM_HALF_WIDTH
                hi = center_deg + BEAM_HALF_WIDTH
                for d in range(lo, hi + 1, 2):
                    pts.append(self._polar_to_xy(dist, d))
                flat = []
                for p in pts:
                    flat.extend(p)
                if len(flat) >= 6:
                    self.canvas.create_polygon(*flat, fill=danger_color,
                                               outline="", tags="dynamic")

        # --- Trail blips ---
        self._draw_trail(self.left_trail, LEFT_CENTER_DEG)
        self._draw_trail(self.right_trail, RIGHT_CENTER_DEG)

        # --- Current blips (bright) ---
        self._draw_blip(self.display_left, LEFT_CENTER_DEG, "L")
        self._draw_blip(self.display_right, RIGHT_CENTER_DEG, "R")

        # --- Detection arc lines (current distance arcs within cones) ---
        for dist, center_deg in [(self.display_left, LEFT_CENTER_DEG),
                                  (self.display_right, RIGHT_CENTER_DEG)]:
            if dist > 0 and dist <= RADAR_MAX_CM:
                color = self._dist_to_color(dist)
                lo = center_deg - BEAM_HALF_WIDTH
                hi = center_deg + BEAM_HALF_WIDTH
                prev = None
                for d in range(lo, hi + 1, 2):
                    pt = self._polar_to_xy(dist, d)
                    if prev:
                        self.canvas.create_line(
                            prev[0], prev[1], pt[0], pt[1],
                            fill=self._fade_color(color, 0.4), width=1, tags="dynamic"
                        )
                    prev = pt

        # --- Update text labels ---
        l_str = f"L  {self.display_left}cm" if self.display_left > 0 else "L  --"
        r_str = f"R  {self.display_right}cm" if self.display_right > 0 else "R  --"
        self.canvas.itemconfig(self.left_label_id, text=l_str,
                               fill=self._dist_to_color(self.display_left))
        self.canvas.itemconfig(self.right_label_id, text=r_str,
                               fill=self._dist_to_color(self.display_right))

    def _draw_sweep(self, center_deg):
        """Animated sweep line that oscillates within one sensor cone."""
        lo = center_deg - BEAM_HALF_WIDTH
        hi = center_deg + BEAM_HALF_WIDTH
        # Oscillate within the cone
        sweep_deg = lo + (hi - lo) * (0.5 + 0.5 * math.sin(self.sweep_phase * 2 * math.pi))
        rx, ry = self.robot_x, self.robot_y

        for i, offset in enumerate([0, 0.5, 1.0, 1.5]):
            d = sweep_deg + offset * (1 if center_deg > 0 else -1)
            d = max(lo, min(hi, d))
            fade = 1.0 - (i / 4.0)
            g = int(0x60 * fade)
            color = f"#00{max(g, 0x08):02x}00"
            ex, ey = self._polar_to_xy(RADAR_MAX_CM, d)
            self.canvas.create_line(rx, ry, ex, ey, fill=color, width=1, tags="dynamic")

    def _draw_trail(self, trail, center_deg):
        """Draw fading trail dots and connected lines along the sensor center-line."""
        prev_pt = None
        for dist_cm, age in trail:
            if dist_cm <= 0 or dist_cm > RADAR_MAX_CM:
                continue
            fade = 1.0 - (age / BLIP_TRAIL_LENGTH)
            size = max(1, int(3 * fade))
            base_color = self._dist_to_color(dist_cm)
            faded = self._fade_color(base_color, fade * 0.6)

            bx, by = self._polar_to_xy(dist_cm, center_deg)
            
            # Draw dot
            self.canvas.create_oval(
                bx - size, by - size, bx + size, by + size,
                fill=faded, outline="", tags="dynamic"
            )
            
            # Draw connecting line
            if prev_pt:
                self.canvas.create_line(
                    prev_pt[0], prev_pt[1], bx, by,
                    fill=faded, width=1, tags="dynamic"
                )
            prev_pt = (bx, by)

    def _draw_blip(self, dist_cm, center_deg, label):
        """Draw the current active blip with glow and distance readout."""
        if dist_cm <= 0 or dist_cm > RADAR_MAX_CM:
            return
        bx, by = self._polar_to_xy(dist_cm, center_deg)
        color = self._dist_to_color(dist_cm)

        # Outer glow ring
        self.canvas.create_oval(
            bx - 10, by - 10, bx + 10, by + 10,
            fill="", outline=self._fade_color(color, 0.3), width=1, tags="dynamic"
        )
        # Middle ring
        self.canvas.create_oval(
            bx - 6, by - 6, bx + 6, by + 6,
            fill="", outline=color, width=1, tags="dynamic"
        )
        # Inner dot
        self.canvas.create_oval(
            bx - 3, by - 3, bx + 3, by + 3,
            fill=color, outline="", tags="dynamic"
        )
        # Distance label
        anchor = "sw" if center_deg < 0 else "se"
        offset_x = 12 if center_deg < 0 else -12
        self.canvas.create_text(
            bx + offset_x, by - 8, text=f"{dist_cm}cm",
            fill=color, font=("Consolas", 8, "bold"),
            anchor=anchor, tags="dynamic"
        )


class NovaController:
    def __init__(self, master):
        self.master = master
        master.title("Nova SM3 Python Controller")
        master.geometry("620x920")
        master.configure(bg="#1a1a2e")

        self.serial_port = None
        self.is_running = True

        # =====================================================
        # THREAD-SAFE KEY STATE
        # All key state is protected by self._lock.
        # The transmit thread reads snapshots under the lock.
        # The Tkinter main thread writes under the lock.
        # =====================================================
        self._lock = threading.Lock()
        self._held_keys = set()          # Currently physically held keys
        self._key_press_time = {}        # key -> timestamp of last press event
        self._key_release_time = {}      # key -> timestamp of last release event
        
        # One-shot command queue: items are dicts like {"sel2": 1} or {"p2": 12}
        # The transmit loop drains this and sends each command for 3 consecutive packets
        self._cmd_queue = queue.Queue()
        
        # Active one-shot commands being sent (list of {field: value, "remaining": N})
        self._active_cmds = []
        
        # Sticks default to CENTER (127)
        self.lx = 127
        self.ly = 127
        self.rx = 127
        self.ry = 127

        # Robot status from ACK
        self.robot_mode = 0
        self.robot_start_mode = 0
        self.robot_mpu = 0
        self.uss_left = 0
        self.uss_right = 0
        self.radar_enabled = True
        self.swap_sensors = False
        
        # Local mode tracking
        self.local_mode = 0
        self.local_started = False
        self.last_ack_time = 0
        self.speed_val = 2  # Default to FAST (2ms step delay)

        self.setup_ui()
        self.refresh_ports()
        
        # Bind keyboard events
        master.bind('<KeyPress>', self.on_press)
        master.bind('<KeyRelease>', self.on_release)
        master.bind('<Deactivate>', self.on_deactivate)
        
        self.last_sent_packet = ""
        # Start transmission thread
        self.tx_thread = threading.Thread(target=self.transmit_loop)
        self.tx_thread.daemon = True
        self.tx_thread.start()

        # Start serial read thread
        self.rx_thread = threading.Thread(target=self.receive_loop)
        self.rx_thread.daemon = True
        self.rx_thread.start()

        # Start radar update loop
        self._update_radar()

    def setup_ui(self):
        # --- Header ---
        header = tk.Frame(self.master, bg="#16213e", pady=8)
        header.pack(fill='x')
        tk.Label(header, text="NOVA SM3", font=("Consolas", 16, "bold"),
                 fg="#00ff41", bg="#16213e").pack()

        self.status_var = tk.StringVar(value="Status: Disconnected")
        tk.Label(header, textvariable=self.status_var, font=("Consolas", 10),
                 fg="#e94560", bg="#16213e").pack()
        
        # --- COM Port selector ---
        port_frame = tk.Frame(self.master, bg="#1a1a2e", pady=5)
        port_frame.pack(fill='x', padx=10)
        
        self.port_var = tk.StringVar()
        self.port_dropdown = tk.OptionMenu(port_frame, self.port_var, "")
        self.port_dropdown.config(bg="#0f3460", fg="white", activebackground="#16213e",
                                  highlightthickness=0, font=("Consolas", 9))
        self.port_dropdown.pack(side='left', padx=3)
        
        btn_style = {"bg": "#0f3460", "fg": "white", "activebackground": "#e94560",
                     "activeforeground": "white", "font": ("Consolas", 9, "bold"),
                     "relief": "flat", "padx": 8, "pady": 3}

        tk.Button(port_frame, text="Connect", command=self.connect_serial, **btn_style).pack(side='left', padx=3)
        tk.Button(port_frame, text="Refresh", command=self.refresh_ports, **btn_style).pack(side='left', padx=3)

        # --- Controls ---
        tk.Label(self.master, text="─── Controls ───", font=("Consolas", 11, "bold"),
                 fg="#00ff41", bg="#1a1a2e").pack(pady=(8, 4))
        
        controls = [
            ("W / S", "Walk Forward / Backward"),
            ("A / D", "Turn Left / Right"),
            ("I / K", "Pitch / Stride Mod"),
            ("J / L", "Yaw"),
            ("1 - 5", "March, Walk, Free, Trot, Follow"),
            ("[ / ]", "Speed Down / Speed Up"),
            ("Q", "Start / Stop Mode"),
            ("H", "Home"),
            ("M", "Toggle MPU"),
            ("X", "Sit Down"),
            ("C", "Lay Down"),
        ]
        
        ctrl_frame = tk.Frame(self.master, bg="#1a1a2e")
        ctrl_frame.pack(fill='x', padx=30)
        for keys, desc in controls:
            row = tk.Frame(ctrl_frame, bg="#1a1a2e")
            row.pack(fill='x', pady=1)
            tk.Label(row, text=keys, width=8, anchor='e', font=("Consolas", 9, "bold"),
                     fg="#e94560", bg="#1a1a2e").pack(side='left')
            tk.Label(row, text=desc, anchor='w', font=("Consolas", 9),
                     fg="#a0a0a0", bg="#1a1a2e").pack(side='left', padx=8)

        # --- Speed selector bar ---
        speed_frame = tk.Frame(self.master, bg="#1a1a2e", pady=3)
        speed_frame.pack(fill='x', padx=30)
        self.speed_label_var = tk.StringVar(value="Speed: FAST (2ms)")
        tk.Label(speed_frame, textvariable=self.speed_label_var, font=("Consolas", 9, "bold"),
                 fg="#ffb703", bg="#1a1a2e").pack(side='left', padx=(0, 10))
        for sname, sval in [("Slow", 6), ("Med", 4), ("Fast", 2), ("Turbo", 1)]:
            tk.Button(speed_frame, text=sname, command=lambda v=sval: self.set_speed(v), **btn_style).pack(side='left', padx=2)

        # --- Quick Actions toolbar (including MPU Auto-Level toggle) ---
        action_frame = tk.Frame(self.master, bg="#1a1a2e", pady=4)
        action_frame.pack(fill='x', padx=30)
        tk.Label(action_frame, text="Quick:", font=("Consolas", 9, "bold"),
                 fg="#00ff41", bg="#1a1a2e").pack(side='left', padx=(0, 10))

        self.mpu_btn = tk.Button(action_frame, text="MPU: OFF", command=lambda: self._handle_oneshot('m'),
                                 bg="#3a3a4a", fg="#a0a0a0", activebackground="#4e4e63", activeforeground="white",
                                 font=("Consolas", 9, "bold"), relief="flat", padx=10, pady=3)
        self.mpu_btn.pack(side='left', padx=3)

        tk.Button(action_frame, text="Home (H)", command=lambda: self._handle_oneshot('h'), **btn_style).pack(side='left', padx=3)
        tk.Button(action_frame, text="Start/Stop (Q)", command=lambda: self._handle_oneshot('q'), **btn_style).pack(side='left', padx=3)
        tk.Button(action_frame, text="Sit (X)", command=lambda: self._handle_oneshot('x'), **btn_style).pack(side='left', padx=3)
        tk.Button(action_frame, text="Lay (C)", command=lambda: self._handle_oneshot('c'), **btn_style).pack(side='left', padx=3)
        
        # --- Status display ---
        self.mode_var = tk.StringVar(value="Mode: --  |  MPU: --")
        tk.Label(self.master, textvariable=self.mode_var, font=("Consolas", 10, "bold"),
                 fg="#53d8fb", bg="#1a1a2e").pack(pady=5)

        self.data_var = tk.StringVar(value="Tx: <...>")
        tk.Label(self.master, textvariable=self.data_var, font=("Consolas", 8),
                 fg="#3a3a4a", bg="#1a1a2e").pack(pady=2)

        # --- Radar Section ---
        radar_header = tk.Frame(self.master, bg="#1a1a2e")
        radar_header.pack(fill='x', pady=(8, 2))
        tk.Label(radar_header, text="─── Ultrasonic Radar ───", font=("Consolas", 11, "bold"),
                 fg="#00ff41", bg="#1a1a2e").pack(side='left', padx=(140, 10))
        
        self.radar_btn = tk.Button(radar_header, text="Turn OFF", command=self.toggle_radar, **btn_style)
        self.radar_btn.pack(side='left', padx=(0, 5))
        
        self.swap_btn = tk.Button(radar_header, text="Swap L/R", command=self.toggle_swap, **btn_style)
        self.swap_btn.pack(side='left')

        radar_frame = tk.Frame(self.master, bg="#1a1a2e")
        radar_frame.pack(pady=5)
        self.radar = RadarCanvas(radar_frame)

    def _update_radar(self):
        """Periodically update the radar display at ~10Hz."""
        if self.is_running:
            if self.radar_enabled:
                if self.swap_sensors:
                    self.radar.update(self.uss_right, self.uss_left)
                else:
                    self.radar.update(self.uss_left, self.uss_right)
            self.master.after(100, self._update_radar)

    def toggle_swap(self):
        self.swap_sensors = not self.swap_sensors
        if self.swap_sensors:
            self.swap_btn.config(bg="#e94560")
            print("[RADAR] Sensors swapped (Left <-> Right)")
        else:
            self.swap_btn.config(bg="#0f3460")
            print("[RADAR] Sensors normal")

    def toggle_radar(self):
        self.radar_enabled = not self.radar_enabled
        if self.radar_enabled:
            self.radar_btn.config(text="Turn OFF", bg="#0f3460")
        else:
            self.radar_btn.config(text="Turn ON", bg="#8a1a1a")
            # Clear radar display when turned off
            self.radar.canvas.delete("dynamic")
            self.radar.dist_left = 0
            self.radar.dist_right = 0
            # Update labels to show OFF
            self.radar.canvas.itemconfig(self.radar.left_label_id, text="L  --cm", fill="#00aa22")
            self.radar.canvas.itemconfig(self.radar.right_label_id, text="R  --cm", fill="#00aa22")

    def update_mpu_ui(self, mpu_state):
        """Update MPU button text and styling based on live robot telemetry."""
        if hasattr(self, 'mpu_btn') and self.mpu_btn:
            if mpu_state:
                self.mpu_btn.config(text="MPU: ON (Auto-Level)", bg="#2a9d8f", fg="white", activebackground="#21867a")
            else:
                self.mpu_btn.config(text="MPU: OFF", bg="#3a3a4a", fg="#a0a0a0", activebackground="#4e4e63")

    def set_speed(self, spd_val):
        self.speed_val = spd_val
        name_map = {6: "SLOW", 4: "MEDIUM", 2: "FAST", 1: "TURBO"}
        name = name_map.get(spd_val, f"{spd_val}ms")
        self.speed_label_var.set(f"Speed: {name} ({spd_val}ms)")
        print(f"[SPEED] Step speed set to {name} ({spd_val}ms delay)")

    def refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        menu = self.port_dropdown["menu"]
        menu.delete(0, "end")
        
        if not ports:
            self.port_var.set("No Ports")
            return
            
        for p in ports:
            menu.add_command(label=p.device, command=lambda value=p.device: self.port_var.set(value))
            
        self.port_var.set(ports[0].device)

    def connect_serial(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            
        port = self.port_var.get()
        if not port or port == "No Ports":
            return
            
        try:
            self.serial_port = serial.Serial(port, 19200, timeout=0.1)
            print(f"[SERIAL] Connected to {port}, waiting for Arduino to boot...")
            self.status_var.set(f"Status: Connecting to {port}...")
            self.master.update()  # Force UI refresh
            time.sleep(2)  # Wait for Arduino to finish booting
            self.serial_port.reset_input_buffer()  # Flush any garbage from boot
            self.status_var.set(f"Status: Connected to {port}")
            print(f"[SERIAL] Ready on {port}")
        except Exception as e:
            self.status_var.set(f"Status: Error - {e}")
            print(f"[SERIAL] ERROR: {e}")

    # =================================================================
    # KEY HANDLING — Thread-safe, no timers
    # =================================================================
    def on_press(self, event):
        key = event.keysym.lower()
        now = time.time()
        with self._lock:
            already_held = key in self._held_keys
            self._held_keys.add(key)
            self._key_press_time[key] = now
            # Remove any pending release timestamp — the key is being held
            self._key_release_time.pop(key, None)
        
        if not already_held:
            # First press of this key — handle one-shot commands
            self._handle_oneshot(key)

    def on_release(self, event):
        key = event.keysym.lower()
        now = time.time()
        with self._lock:
            # Don't immediately remove from held_keys!
            # Just record the release timestamp. The transmit thread
            # will check if enough time has passed without a new press
            # before actually releasing the key.
            self._key_release_time[key] = now

    def on_deactivate(self, event):
        """Clear all active keys when the window is deactivated (alt-tabbed away)."""
        with self._lock:
            self._held_keys.clear()
            self._key_press_time.clear()
            self._key_release_time.clear()
        print("[FOCUS] Window deactivated - keys cleared, robot stopped.")

    def _handle_oneshot(self, key):
        """Queue one-shot commands (mode select, start/stop, etc.)
        These are NOT continuous — they fire once on key-down."""
        if key == 'q':
            self._cmd_queue.put({"sel2": 1})
            # Toggle local started state for display
            self.local_started = not self.local_started
        elif key == 'h':
            self._cmd_queue.put({"p2": 1})
        elif key == 'm':
            self._cmd_queue.put({"p2": 2})
        elif key == 'x':
            self._cmd_queue.put({"p2": 3})
        elif key == 'c':
            self._cmd_queue.put({"p2": 4})
        elif key == 'z':
            self._cmd_queue.put({"p2": 5})
        elif key in ('1', '2', '3', '4', '5'):
            mode_val = int(key) + 10  # 11-15
            self._cmd_queue.put({"p2": mode_val})
            self.local_mode = int(key)
            self.local_started = False
        elif key in ('[', '-', 'minus', 'bracketleft'):
            # Decrease speed (longer delay)
            levels = [1, 2, 4, 6]
            curr_idx = levels.index(self.speed_val) if self.speed_val in levels else 1
            if curr_idx < len(levels) - 1:
                self.set_speed(levels[curr_idx + 1])
        elif key in (']', '=', '+', 'plus', 'equal', 'bracketright'):
            # Increase speed (shorter delay)
            levels = [1, 2, 4, 6]
            curr_idx = levels.index(self.speed_val) if self.speed_val in levels else 1
            if curr_idx > 0:
                self.set_speed(levels[curr_idx - 1])

    # =================================================================
    # TRANSMIT LOOP — Runs in background thread at 20Hz
    # All state computation happens HERE, not on the main thread
    # =================================================================
    def transmit_loop(self):
        DEBOUNCE_SEC = 0.15  # 150ms debounce for key releases
        
        while self.is_running:
            now = time.time()
            
            # --- Step 1: Process key release debouncing under lock ---
            with self._lock:
                # Check if any keys have been released for longer than DEBOUNCE_SEC
                # without a subsequent press event
                expired = []
                for key, release_time in self._key_release_time.items():
                    press_time = self._key_press_time.get(key, 0)
                    # Only release if the release happened AFTER the last press
                    # AND enough time has passed
                    if release_time > press_time and (now - release_time) >= DEBOUNCE_SEC:
                        expired.append(key)
                
                for key in expired:
                    self._held_keys.discard(key)
                    del self._key_release_time[key]
                
                # Take a snapshot of currently held keys
                held = set(self._held_keys)
            
            # --- Step 2: Compute continuous joystick values from held keys ---
            ry = 127
            if 'w' in held: ry = 40    # Forward
            if 's' in held: ry = 215   # Backward

            lx = 127
            if 'a' in held: lx = 215   # Left
            if 'd' in held: lx = 40    # Right

            ly = 127
            if 'i' in held: ly = 40    # Up / pitch mod
            if 'k' in held: ly = 215   # Down / stride mod

            rx = 127
            if 'j' in held: rx = 40    # Yaw left
            if 'l' in held: rx = 215   # Yaw right

            # --- Step 3: Drain one-shot command queue ---
            while True:
                try:
                    cmd = self._cmd_queue.get_nowait()
                    # Send each one-shot command for 3 consecutive packets (150ms)
                    cmd["remaining"] = 3
                    self._active_cmds.append(cmd)
                except queue.Empty:
                    break
            
            # --- Step 4: Build packet values ---
            btn1 = btn2 = btn3 = btn4 = 0
            sel1 = sel2 = 0
            p1 = int(self.speed_val)
            p2 = 0
            
            # Apply active one-shot commands
            still_active = []
            for cmd in self._active_cmds:
                if "sel2" in cmd:
                    sel2 = cmd["sel2"]
                if "p2" in cmd:
                    p2 = cmd["p2"]
                cmd["remaining"] -= 1
                if cmd["remaining"] > 0:
                    still_active.append(cmd)
            self._active_cmds = still_active
            
            # --- Step 5: Format and send packet ---
            # Format: <lx,ly,rx,ry,btn1,btn2,btn3,btn4,sel1,sel2,p1,p2>
            packet = f"<{lx},{ly},{rx},{ry},{btn1},{btn2},{btn3},{btn4},{sel1},{sel2},{p1},{p2}>\n"
            
            # Print detailed log only when state actually changes
            if packet != self.last_sent_packet:
                parts = []
                if ry != 127: parts.append(f"ry={ry}({'FWD' if ry < 127 else 'BACK'})")
                if lx != 127: parts.append(f"lx={lx}({'LEFT' if lx > 127 else 'RIGHT'})")
                if ly != 127: parts.append(f"ly={ly}")
                if rx != 127: parts.append(f"rx={rx}")
                parts.append(f"spd={p1}ms")
                if btn1: parts.append("BTN1")
                if btn2: parts.append("BTN2")
                if btn3: parts.append("BTN3")
                if btn4: parts.append("BTN4")
                if sel1: parts.append("SEL1")
                if sel2: parts.append("START/STOP(sel2)")
                if p2 >= 11: parts.append(f"MODE={MODE_NAMES.get(p2-10, '?')}(p2={p2})")
                elif p2 == 1: parts.append("HOME(p2=1)")
                elif p2 == 2: parts.append("MPU_TOGGLE(p2=2)")
                elif p2 == 3: parts.append("SIT(p2=3)")
                elif p2 == 4: parts.append("LAY_DOWN(p2=4)")
                elif p2 == 5: parts.append("CUSTOM_IMG(p2=5)")
                desc = ", ".join(parts) if parts else "IDLE (all centered)"
                print(f"[TX] {desc}  ->  {packet.strip()}")
                self.last_sent_packet = packet
                
            # Update UI safely from this thread
            try:
                self.data_var.set(f"Tx: {packet.strip()}")
            except:
                pass
            
            # Update mode display
            try:
                mode_name = MODE_NAMES.get(self.local_mode, f"#{self.local_mode}")
                started = "ACTIVE" if self.local_started else "STOPPED"
                mpu_str = "ON" if self.robot_mpu else "OFF"
                if self.last_ack_time == 0:
                    robot_status = "⚠ ROBOT OFFLINE"
                elif time.time() - self.last_ack_time > 5:
                    robot_status = "⚠ ROBOT OFFLINE"
                else:
                    robot_status = "✓ ROBOT ONLINE"
                self.mode_var.set(f"Mode: {mode_name} ({started})  |  MPU: {mpu_str}  |  {robot_status}")
                self.master.after_idle(self.update_mpu_ui, self.robot_mpu)
            except:
                pass
                    
            # Send over serial
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.write(packet.encode('utf-8'))
                except:
                    pass
            
            # Send at ~20Hz (50ms)
            time.sleep(0.05)

    def receive_loop(self):
        """Read ACK data from transmitter to show robot status and USS data."""
        last_ack_mode = -1
        last_ack_start = -1
        last_ack_mpu = -1
        last_uss_l = -1
        last_uss_r = -1
        
        while self.is_running:
            if self.serial_port and self.serial_port.is_open:
                try:
                    while self.serial_port.in_waiting > 0:
                        line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        if line.startswith("[ACK:") and line.endswith("]"):
                            parts = line[5:-1].split(",")
                            if len(parts) >= 3:
                                new_mode = int(parts[0])
                                new_start = int(parts[1])
                                new_mpu = int(parts[2])
                                
                                new_uss_l = 0
                                new_uss_r = 0

                                # Parse USS data if available
                                if len(parts) >= 5:
                                    new_uss_l = int(parts[3])
                                    new_uss_r = int(parts[4])

                                # --- Reject corrupted ACK packets ---
                                ack_vals = [new_mode, new_start, new_mpu, new_uss_l, new_uss_r]
                                all_same = len(set(ack_vals)) == 1 and ack_vals[0] != 0
                                invalid_mode = new_mode > 5
                                invalid_start = new_start > 5
                                
                                if all_same or invalid_mode or invalid_start:
                                    continue

                                # Log when state or USS data changes significantly
                                state_changed = (new_mode != last_ack_mode or new_start != last_ack_start or new_mpu != last_ack_mpu)
                                uss_changed = (abs(new_uss_l - last_uss_l) > 2 or abs(new_uss_r - last_uss_r) > 2)
                                
                                if state_changed or uss_changed:
                                    mode_name = MODE_NAMES.get(new_mode, f"#{new_mode}")
                                    started = "ACTIVE" if new_start > 0 else "STOPPED"
                                    mpu_str = "ON" if new_mpu else "OFF"
                                    
                                    if state_changed:
                                        prev_mode_name = MODE_NAMES.get(last_ack_mode, f"#{last_ack_mode}")
                                        prev_started = "ACTIVE" if last_ack_start > 0 else "STOPPED"
                                        print(f"[ROBOT] {prev_mode_name}({prev_started}) -> {mode_name}({started})  |  MPU: {mpu_str}  |  raw_ack=[{new_mode},{new_start},{new_mpu},{new_uss_l},{new_uss_r}]")
                                    if uss_changed:
                                        print(f"[SENSOR] L: {new_uss_l}cm  |  R: {new_uss_r}cm")
                                        
                                    last_ack_mode = new_mode
                                    last_ack_start = new_start
                                    last_ack_mpu = new_mpu
                                    last_uss_l = new_uss_l
                                    last_uss_r = new_uss_r

                                self.robot_mode = new_mode
                                self.robot_start_mode = new_start
                                self.robot_mpu = new_mpu
                                self.uss_left = new_uss_l
                                self.uss_right = new_uss_r
                                self.last_ack_time = time.time()
                                try:
                                    self.master.after_idle(self.update_mpu_ui, new_mpu)
                                except:
                                    pass

                                # Sync local mode from robot ACK for accurate display
                                if new_mode > 0 and new_mode <= 5:
                                    self.local_mode = new_mode
                                self.local_started = (new_start > 0)
                        elif line and not line.startswith("[ACK:"):
                            # Print any non-ACK serial messages from the transmitter
                            print(f"[NANO] {line}")
                except:
                    pass
            time.sleep(0.05)

    def on_closing(self):
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    print("Starting Nova SM3 Python Controller...")
    app = NovaController(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

