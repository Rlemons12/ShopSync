#!/usr/bin/env python3
# scanner.py
# Stand-alone: MASTER→VERIFY workflow + SQLite, with BOTH inputs:
#  - HID keyboard wedge (Entry box)
#  - Serial/COM scanner (auto-detect + manual connect)
#
# Stores ONLY (read_value, master_code, created_at) in table 'scans'.
#
# Deps:
#   pip install pillow pyzbar rapidfuzz pyserial
# ZBar native lib required by pyzbar (Windows: winget install lwolf.zbar)

import io
import time
import sqlite3
import threading
import queue
from pathlib import Path
from typing import Optional, List, Tuple

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from PIL import Image
from pyzbar.pyzbar import decode as zbar_decode, ZBarSymbol
from rapidfuzz import fuzz

# ----------------------------- Globals -----------------------------
APP = None
LOG = None
DB_PATH_VAR = None
MASTER_VAR = None
STATUS_VAR = None
SCAN_ENTRY = None
FUZZY_VAR = None
THRESHOLD_SCALE = None

CURRENT_MASTER: Optional[str] = None
ARM_NEXT_SCAN_AS_MASTER = False

# Serial scanner globals
SER = None                     # serial.Serial instance or None
SER_STOP = threading.Event()   # stop flag for reader thread
SER_QUEUE = queue.Queue()      # scanned lines from serial -> Tk thread

# ----------------------------- Logging -----------------------------
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - {msg}\n"
    if LOG is not None:
        LOG.configure(state="normal")
        LOG.insert("end", line)
        LOG.see("end")
        LOG.configure(state="disabled")
    else:
        print(line, end="")

def set_status(text: str):
    if STATUS_VAR is not None:
        STATUS_VAR.set(text)

# ----------------------------- SQLite -----------------------------
def open_db(db_path: str) -> sqlite3.Connection:
    first = not Path(db_path).exists()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY,
            read_value  TEXT NOT NULL,
            master_code TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    if first:
        log(f"Initialized DB at {db_path}")
    return conn

def insert_scan(conn: sqlite3.Connection, read_value: str, master_code: str):
    conn.execute("INSERT INTO scans (read_value, master_code) VALUES (?, ?)", (read_value, master_code))
    conn.commit()

# ----------------------------- Barcode decode from image (optional) -----------------------------
def _build_supported_symbols() -> list:
    """Use only ZBar symbols this build supports."""
    want = [
        "EAN13", "EAN8", "UPCA", "UPCE",
        "CODE128", "CODE39", "CODE93",
        "I25",              # Interleaved 2 of 5 (ITF); some builds omit it
        "QRCODE", "PDF417", "CODABAR",
        "DATABAR", "DATABAR_EXP",
    ]
    have = []
    for name in want:
        if hasattr(ZBarSymbol, name):
            have.append(getattr(ZBarSymbol, name))
    return have

SUPPORTED_SYMBOLS = _build_supported_symbols()

def decode_image_file(path: str) -> List[str]:
    """Decode barcodes from an image; return unique values in scan order."""
    with Image.open(path) as im:
        im = im.convert("RGB")
        dec = zbar_decode(im, symbols=SUPPORTED_SYMBOLS)
    vals = [d.data.decode("utf-8", errors="replace") for d in dec]
    out, seen = [], set()
    for v in vals:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out

# ----------------------------- Verify logic -----------------------------
def verify(read_value: str, master_code: str) -> Tuple[bool, int]:
    """(passed, score). Exact if fuzzy off; fuzzy uses token_sort_ratio >= threshold."""
    if not FUZZY_VAR.get():
        ok = (read_value == master_code)
        return ok, (100 if ok else 0)
    thr = int(THRESHOLD_SCALE.get())
    score = fuzz.token_sort_ratio(read_value, master_code)
    return (score >= thr, int(score))

def handle_scan_value(value: str):
    """Main ingestion path (for HID & Serial)."""
    global CURRENT_MASTER, ARM_NEXT_SCAN_AS_MASTER
    value = (value or "").strip()
    if not value:
        return

    # If armed or no master yet -> set master
    if ARM_NEXT_SCAN_AS_MASTER or CURRENT_MASTER is None:
        CURRENT_MASTER = value
        ARM_NEXT_SCAN_AS_MASTER = False
        MASTER_VAR.set(CURRENT_MASTER)
        set_status("MASTER set")
        log(f"MASTER = '{CURRENT_MASTER}'")
        return

    # Verify vs master
    read_value = value
    master_code = CURRENT_MASTER
    passed, score = verify(read_value, master_code)
    mark = "PASS" if passed else "FAIL"
    msg = f"[{mark}] read='{read_value}'  vs  MASTER='{master_code}'"
    if FUZZY_VAR.get():
        msg += f"  (similarity={score})"
    log(msg)
    set_status(mark)

    # Store ONLY (read_value, master_code)
    db = DB_PATH_VAR.get()
    if not db:
        log("WARNING: No DB selected; result NOT saved.")
        return
    try:
        conn = open_db(db)
        insert_scan(conn, read_value, master_code)
        conn.close()
    except Exception as e:
        messagebox.showerror("DB error", str(e))
        log(f"DB ERROR: {e}")

# ----------------------------- HID (Entry) -----------------------------
def on_entry_return(event=None):
    val = SCAN_ENTRY.get()
    SCAN_ENTRY.delete(0, 'end')
    handle_scan_value(val)

def arm_new_master():
    global ARM_NEXT_SCAN_AS_MASTER
    ARM_NEXT_SCAN_AS_MASTER = True
    set_status("Armed: next scan sets MASTER")
    log("Armed: the next scan will be saved as MASTER.")
    SCAN_ENTRY.focus_set()
    SCAN_ENTRY.select_range(0, 'end')

def clear_master():
    global CURRENT_MASTER, ARM_NEXT_SCAN_AS_MASTER
    CURRENT_MASTER = None
    ARM_NEXT_SCAN_AS_MASTER = False
    MASTER_VAR.set("(none)")
    set_status("MASTER cleared")
    log("MASTER cleared.")

def scan_from_image():
    path = filedialog.askopenfilename(
        title="Pick an image to decode",
        filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff"), ("All files", "*.*")]
    )
    if not path:
        return
    try:
        vals = decode_image_file(path)
        if not vals:
            messagebox.showinfo("No barcode", "No barcode found in that image.")
            return
        value = vals[0] if len(vals) == 1 else choose_from_list("Multiple codes found — pick one", vals)
        if value:
            handle_scan_value(value)
    except Exception as e:
        messagebox.showerror("Image decode error", str(e))
        log(f"DECODE ERROR: {e}")

def choose_from_list(title: str, options: list) -> Optional[str]:
    top = tk.Toplevel(APP)
    top.title(title)
    top.grab_set()
    tk.Label(top, text=title).pack(padx=10, pady=(10,4))
    lb = tk.Listbox(top, height=min(12, len(options)), width=60)
    for o in options:
        lb.insert('end', o)
    lb.selection_set(0)
    lb.pack(padx=10, pady=6)
    result = {"val": None}
    def ok():
        sel = lb.curselection()
        if sel:
            result["val"] = options[sel[0]]
        top.destroy()
    def cancel():
        result["val"] = None
        top.destroy()
    btns = tk.Frame(top); btns.pack(pady=(0,10))
    tk.Button(btns, text="OK", width=10, command=ok).pack(side="left", padx=6)
    tk.Button(btns, text="Cancel", width=10, command=cancel).pack(side="left", padx=6)
    top.bind("<Return>", lambda e: ok()); top.bind("<Escape>", lambda e: cancel())
    APP.wait_window(top)
    return result["val"]

# ----------------------------- Serial / COM (pyserial) -----------------------------
def list_serial_ports_with_meta():
    """Return list of (device, description, manufacturer, vid, pid)."""
    try:
        from serial.tools import list_ports
    except Exception:
        return []
    ports = []
    for p in list_ports.comports():
        vid = getattr(p, "vid", None)
        pid = getattr(p, "pid", None)
        ports.append((p.device, p.description or "", p.manufacturer or "", vid, pid))
    return ports

def score_serial_port(meta: Tuple[str, str, str, Optional[int], Optional[int]]) -> int:
    """
    Heuristic score to guess which port is a barcode scanner.
    Keywords from description/manufacturer, and common USB-serial chips.
    """
    device, desc, mfg, vid, pid = meta
    text = f"{device} {desc} {mfg}".lower()
    score = 0
    # Strong hints
    for kw in ["barcode", "scanner", "honeywell", "zebra", "datalogic", "symbol"]:
        if kw in text: score += 50
    # Common USB-serial chip vendors (helpful if the scanner uses an adapter)
    for kw in ["cp210", "silicon labs", "ftdi", "prolific", "ch340", "usb-serial", "usb serial"]:
        if kw in text: score += 10
    # TTY/COM patterns (Windows COM, Unix ttyUSB/ACM)
    for kw in ["com", "ttyusb", "ttyacm"]:
        if kw in text: score += 2
    # Prefer stable COM numbers (arbitrary, small boost)
    try:
        if device.lower().startswith("com"):
            n = int(device[3:])
            score += max(0, 10 - min(n, 10))
    except Exception:
        pass
    return score

def autodetect_serial_port() -> Optional[str]:
    metas = list_serial_ports_with_meta()
    if not metas:
        return None
    scored = sorted(((score_serial_port(m), m[0], m) for m in metas), reverse=True)
    best_score, best_dev, best_meta = scored[0]
    log("Serial ports discovered:")
    for s, dev, m in scored:
        device, desc, mfg, vid, pid = m
        log(f"  {dev:<12} score={s:<3}  desc='{desc}'  mfg='{mfg}'  vid={vid} pid={pid}")
    if best_score <= 0:
        return None
    return best_dev

def serial_reader_loop():
    """Background thread: read bytes, push full lines (CR or LF) into SER_QUEUE."""
    buf = bytearray()
    while not SER_STOP.is_set():
        try:
            b = SER.read(1)
            if not b:
                continue
            if b in (b'\r', b'\n'):
                if buf:
                    line = buf.decode("utf-8", errors="replace").strip()
                    SER_QUEUE.put(line)
                    buf.clear()
            else:
                buf.extend(b)
        except Exception:
            break

def start_serial(port: str, baud: int = 9600):
    """Open COM port and spawn reader thread."""
    global SER
    stop_serial()
    try:
        import serial
        SER = serial.Serial(port=port, baudrate=baud, timeout=0.2)
    except Exception as e:
        messagebox.showerror("Serial error", f"Could not open {port}: {e}")
        SER = None
        return
    SER_STOP.clear()
    t = threading.Thread(target=serial_reader_loop, daemon=True)
    t.start()
    log(f"Serial connected: {port} @ {baud} baud")

def stop_serial():
    """Stop reader and close port if open."""
    SER_STOP.set()
    try:
        if SER and SER.is_open:
            SER.close()
    except Exception:
        pass
    finally:
        globals()['SER'] = None
        log("Serial disconnected.")

def poll_serial_queue():
    """Deliver queued serial scans to the main handler (runs in Tk loop)."""
    try:
        while True:
            line = SER_QUEUE.get_nowait()
            if line:
                handle_scan_value(line)
    except queue.Empty:
        pass
    APP.after(50, poll_serial_queue)

# ----------------------------- DB chooser -----------------------------
def choose_db():
    path = filedialog.asksaveasfilename(
        title="Choose or create SQLite DB",
        defaultextension=".sqlite",
        filetypes=[("SQLite DB", "*.sqlite;*.db"), ("All files", "*.*")]
    )
    if not path:
        return
    DB_PATH_VAR.set(path)
    with open_db(path) as _:
        pass
    log(f"DB selected: {path}")

# ----------------------------- GUI -----------------------------
def build_gui():
    global APP, LOG, DB_PATH_VAR, MASTER_VAR, STATUS_VAR, SCAN_ENTRY, FUZZY_VAR, THRESHOLD_SCALE

    APP = tk.Tk()
    APP.title("Master → Verify Scans (SQLite, HID + Serial, Auto-Detect)")
    APP.geometry("1000x620")

    # Top row: DB + status
    top = tk.Frame(APP); top.pack(fill="x", padx=10, pady=8)
    DB_PATH_VAR = tk.StringVar()
    tk.Label(top, text="DB:").pack(side="left")
    tk.Entry(top, textvariable=DB_PATH_VAR, width=62).pack(side="left", padx=6)
    tk.Button(top, text="Choose/Create DB", command=choose_db).pack(side="left", padx=6)

    STATUS_VAR = tk.StringVar(value="Ready")
    tk.Label(top, textvariable=STATUS_VAR, relief="sunken", width=16).pack(side="right")

    # Master row
    mrow = tk.Frame(APP); mrow.pack(fill="x", padx=10)
    MASTER_VAR = tk.StringVar(value="(none)")
    tk.Label(mrow, text="MASTER:").pack(side="left")
    tk.Label(mrow, textvariable=MASTER_VAR, fg="blue").pack(side="left", padx=6)
    tk.Button(mrow, text="New Master (next scan)", command=arm_new_master).pack(side="left", padx=6)
    tk.Button(mrow, text="Clear Master", command=clear_master).pack(side="left", padx=6)

    # Fuzzy options
    fz = tk.Frame(APP); fz.pack(fill="x", padx=10, pady=(4,0))
    FUZZY_VAR = tk.IntVar(value=0)
    tk.Checkbutton(fz, text="Enable fuzzy match", variable=FUZZY_VAR).pack(side="left")
    tk.Label(fz, text="Threshold").pack(side="left", padx=(12,4))
    THRESHOLD_SCALE = tk.Scale(fz, from_=50, to=100, orient="horizontal", length=220)
    THRESHOLD_SCALE.set(95)
    THRESHOLD_SCALE.pack(side="left")

    # HID Entry input
    scan = tk.Frame(APP); scan.pack(fill="x", padx=10, pady=(6,0))
    tk.Label(scan, text="HID scan here:").pack(side="left")
    SCAN_ENTRY = tk.Entry(scan, width=62)
    SCAN_ENTRY.pack(side="left", padx=6)
    SCAN_ENTRY.focus_set()
    SCAN_ENTRY.bind("<Return>", on_entry_return)
    tk.Button(scan, text="Scan From Image…", command=scan_from_image).pack(side="left", padx=6)

    # Serial controls
    ser_row = tk.Frame(APP); ser_row.pack(fill="x", padx=10, pady=(6,0))
    tk.Label(ser_row, text="Serial scanner:").pack(side="left")
    ser_port_var = tk.StringVar()
    ser_baud_var = tk.IntVar(value=9600)

    port_box = ttk.Combobox(ser_row, textvariable=ser_port_var, width=18, state="readonly")
    port_box.pack(side="left", padx=6)

    def refresh_ports_ui():
        metas = list_serial_ports_with_meta()
        ports = [m[0] for m in metas]
        port_box["values"] = ports
        if ports and not ser_port_var.get():
            ser_port_var.set(ports[0])
        # Log all ports
        if metas:
            log("Ports available:")
            for m in metas:
                device, desc, mfg, vid, pid = m
                log(f"  {device:<12} desc='{desc}' mfg='{mfg}' vid={vid} pid={pid}")

    tk.Button(ser_row, text="Refresh", command=refresh_ports_ui).pack(side="left")

    tk.Label(ser_row, text="Baud:").pack(side="left", padx=(12,0))
    baud_box = ttk.Combobox(ser_row, textvariable=ser_baud_var,
                            values=[9600,19200,38400,57600,115200],
                            width=10, state="readonly")
    baud_box.pack(side="left", padx=6)

    ser_btn_var = tk.StringVar(value="Connect")
    def toggle_serial():
        if ser_btn_var.get() == "Connect":
            port = ser_port_var.get()
            if not port:
                messagebox.showwarning("Serial", "Select a COM port first.")
                return
            start_serial(port, ser_baud_var.get())
            ser_btn_var.set("Disconnect")
        else:
            stop_serial()
            ser_btn_var.set("Connect")
    tk.Button(ser_row, textvariable=ser_btn_var, command=toggle_serial).pack(side="left", padx=8)

    # Auto-detect / Auto-connect
    auto_row = tk.Frame(APP); auto_row.pack(fill="x", padx=10, pady=(4,0))
    def try_autodetect_connect():
        dev = autodetect_serial_port()
        if not dev:
            log("Auto-detect: no likely serial scanner found. If your scanner types into Notepad, it's HID — use the Entry above.")
            return
        ser_port_var.set(dev)
        start_serial(dev, ser_baud_var.get())
        ser_btn_var.set("Disconnect")
    tk.Button(auto_row, text="Auto-Detect & Connect", command=try_autodetect_connect).pack(side="left")

    refresh_ports_ui()

    # Log
    LOG = ScrolledText(APP, width=120, height=24, state="disabled")
    LOG.pack(fill="both", expand=True, padx=10, pady=(8,10))
    log("Ready. Choose/Create a DB. Click 'Auto-Detect & Connect' or 'Refresh' + 'Connect'.")
    log("Tip: If your scanner behaves like a keyboard, use the 'HID scan here' box. First scan becomes MASTER unless you click 'New Master (next scan)'.")
    # Deliver serial scans into handler
    APP.after(50, poll_serial_queue)

    # Clean shutdown
    def on_close():
        stop_serial()
        APP.destroy()
    APP.protocol("WM_DELETE_WINDOW", on_close)

    return APP

# ----------------------------- Main -----------------------------
def main():
    app = build_gui()
    app.mainloop()

if __name__ == "__main__":
    main()
