#!/usr/bin/env python3
"""
Roe's POS — Clerk Terminal
Dual-screen POS client. Primary screen = clerk interface. Secondary screen = customer display.
Designed for OMA POS dual-screen (M121W3 ~1366×768 per panel).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
from requests.exceptions import RequestException
from datetime import datetime
import os
import tempfile

# ─────────────────────────────────────────────────────────────────────────────
# THEME  — warm dark, readable under bright kitchen lighting
# ─────────────────────────────────────────────────────────────────────────────
THEME = {
    "bg":           "#0d1117",
    "surface":      "#161b22",
    "card":         "#1c2333",
    "card2":        "#21293a",
    "border":       "#2d3748",
    "border2":      "#3a4a5c",
    "accent":       "#f59e0b",       # amber — matches admin
    "accent_dim":   "#78350f",
    "accent_hover": "#d97706",
    "green":        "#10b981",
    "green_dim":    "#064e3b",
    "red":          "#ef4444",
    "red_dim":      "#7f1d1d",
    "blue":         "#3b82f6",
    "blue_dim":     "#1e3a5f",
    "purple":       "#8b5cf6",
    "text":         "#f0f4ff",
    "text_sub":     "#8b9ab5",
    "text_muted":   "#4a5568",
    "input_bg":     "#0d1628",
    "tag_bg":       "#1a2744",
    "pin_empty":    "#2d3748",
    "pin_filled":   "#f59e0b",
}
t = THEME   # shorthand used everywhere below


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def fmt(n):
    try:
        return f"₦{float(n):,.0f}"
    except (TypeError, ValueError):
        return "₦0"


def normalize_response(data):
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []


def now_str():
    return datetime.now().strftime("%I:%M %p")


# ─────────────────────────────────────────────────────────────────────────────
# SCROLLABLE FRAME HELPER
# ─────────────────────────────────────────────────────────────────────────────
class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self.inner_id, width=e.width)

    def _on_mousewheel(self, e):
        try:
            self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except tk.TclError:
            # Canvas has been destroyed, unbind the global event
            self.canvas.unbind_all("<MouseWheel>")


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER DISPLAY WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class CustomerDisplay(tk.Toplevel):
    """Second screen shown to the customer. Full-screen on monitor 2."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Roe's POS — Customer Display")
        self.configure(bg=t["bg"])
        self.attributes("-fullscreen", False)
        self.geometry("800x600+1366+0")   # position on second monitor
        self.resizable(True, True)
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=t["accent"], height=10)
        hdr.pack(fill="x")

        logo_f = tk.Frame(self, bg=t["surface"], pady=24)
        logo_f.pack(fill="x")
        tk.Label(logo_f, text="🍽️  Roe's Restaurant", font=("Georgia", 28, "bold"),
                 bg=t["surface"], fg=t["accent"]).pack()
        tk.Label(logo_f, text="Thank you for dining with us!", font=("Arial", 14),
                 bg=t["surface"], fg=t["text_sub"]).pack(pady=(4, 0))

        # Order display area
        self.order_frame = tk.Frame(self, bg=t["bg"])
        self.order_frame.pack(fill="both", expand=True, padx=32, pady=20)

        # Idle state
        self._show_idle()

    def _show_idle(self):
        for w in self.order_frame.winfo_children():
            w.destroy()
        tk.Label(self.order_frame, text="👋", font=("Arial", 64),
                 bg=t["bg"], fg=t["accent"]).pack(pady=(60, 16))
        tk.Label(self.order_frame, text="Welcome!", font=("Georgia", 32, "bold"),
                 bg=t["bg"], fg=t["text"]).pack()
        tk.Label(self.order_frame, text="Your order details will appear here.",
                 font=("Arial", 16), bg=t["bg"], fg=t["text_sub"]).pack(pady=(12, 0))

        # Live clock
        self.clock_lbl = tk.Label(self.order_frame, text="", font=("Arial", 13),
                                   bg=t["bg"], fg=t["text_muted"])
        self.clock_lbl.pack(pady=(24, 0))
        self._tick()

    def _tick(self):
        if self.clock_lbl.winfo_exists():
            self.clock_lbl.config(text=datetime.now().strftime("%A, %d %B %Y  •  %I:%M:%S %p"))
            self.after(1000, self._tick)

    def update_order(self, items, total):
        """Called by clerk screen whenever cart changes."""
        for w in self.order_frame.winfo_children():
            w.destroy()

        if not items:
            self._show_idle()
            return

        tk.Label(self.order_frame, text="Your Order", font=("Georgia", 20, "bold"),
                 bg=t["bg"], fg=t["accent"]).pack(anchor="w", pady=(0, 12))

        # Scrollable list
        sf = ScrollFrame(self.order_frame, bg=t["bg"])
        sf.pack(fill="both", expand=True)

        for entry in items:
            name = entry["name"]
            qty  = entry["qty"]
            price = entry["unit_price"]
            row = tk.Frame(sf.inner, bg=t["card"], pady=10, padx=16)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{qty}×", font=("Arial", 14, "bold"),
                     bg=t["card"], fg=t["accent"], width=4).pack(side="left")
            tk.Label(row, text=name, font=("Arial", 14),
                     bg=t["card"], fg=t["text"]).pack(side="left")
            tk.Label(row, text=fmt(price * qty), font=("Arial", 14, "bold"),
                     bg=t["card"], fg=t["text"]).pack(side="right")

        # Total bar
        tot_f = tk.Frame(self.order_frame, bg=t["accent"], pady=16)
        tot_f.pack(fill="x", pady=(12, 0))
        tk.Label(tot_f, text="TOTAL", font=("Arial", 16, "bold"),
                 bg=t["accent"], fg=t["bg"]).pack(side="left", padx=24)
        tk.Label(tot_f, text=fmt(total), font=("Arial", 22, "bold"),
                 bg=t["accent"], fg=t["bg"]).pack(side="right", padx=24)

    def show_payment_success(self, method, total, change=0):
        """Full-screen thank-you after payment."""
        for w in self.order_frame.winfo_children():
            w.destroy()
        tk.Label(self.order_frame, text="✅", font=("Arial", 72),
                 bg=t["bg"], fg=t["green"]).pack(pady=(40, 8))
        tk.Label(self.order_frame, text="Payment Received!", font=("Georgia", 28, "bold"),
                 bg=t["bg"], fg=t["green"]).pack()
        tk.Label(self.order_frame, text=fmt(total), font=("Arial", 36, "bold"),
                 bg=t["bg"], fg=t["text"]).pack(pady=(8, 0))
        tk.Label(self.order_frame, text=f"via {method.title()}",
                 font=("Arial", 14), bg=t["bg"], fg=t["text_sub"]).pack()
        if change > 0:
            tk.Label(self.order_frame, text=f"Change: {fmt(change)}",
                     font=("Arial", 18, "bold"), bg=t["bg"], fg=t["accent"]).pack(pady=(12, 0))
        tk.Label(self.order_frame, text="Thank you for your patronage! 🙏",
                 font=("Arial", 14), bg=t["bg"], fg=t["text_sub"]).pack(pady=(16, 0))
        # Auto-return to idle after 6 seconds
        self.after(6000, self._show_idle)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class POSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Roe's POS — Clerk Terminal")
        # Sized for one panel of dual-screen OMA POS M121W3 (~1366×768)
        self.geometry("1366x768+0+0")
        self.minsize(1200, 700)
        self.configure(bg=t["bg"])

        # State
        self.api_base    = "http://localhost:8000/api/v1"
        self.session     = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        self.token       = None
        self.staff       = None          # logged-in staff dict
        self.menu_items  = []            # flat list from API
        self.categories  = []            # category list from API
        self.cart        = {}            # menuItemId → {name, unit_price, qty, item_type}
        self.active_cat  = None          # currently selected category filter
        self.current_order_id = None     # open order on backend
        self.table_number     = None

        # Customer display
        self.customer_display = None

        self._show_login()

    # ─── API ──────────────────────────────────────────────────────────────────

    def _api(self, method, path, **kw):
        url = f"{self.api_base}{path}"
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        try:
            r = self.session.request(method, url, timeout=12, **kw)
            if r.status_code >= 400:
                try:
                    err = r.json()
                except ValueError:
                    raise Exception({"error": f"Server error {r.status_code}"})
                raise Exception(err)
            if r.status_code == 204:
                return {}
            return r.json()
        except RequestException as e:
            raise Exception({"error": str(e)})

    def _api_list(self, path):
        return normalize_response(self._api("get", path))

    def _fmt_error(self, exc):
        msg = exc.args[0] if exc.args else str(exc)
        if isinstance(msg, dict):
            if "detail" in msg: return str(msg["detail"])
            if "error"  in msg: return str(msg["error"])
            # join all field errors
            parts = []
            for k, v in msg.items():
                parts.append(f"{k}: {', '.join(v) if isinstance(v, list) else v}")
            return "\n".join(parts) or str(msg)
        return str(msg)

    # ─── DATA LOADERS ─────────────────────────────────────────────────────────

    def _load_menu(self):
        """Fetch categories + all menu items."""
        try:
            self.categories = self._api_list("/menu/categories/?active_only=false")
        except Exception:
            self.categories = []
        try:
            # available_only=true — only show what's in stock / available
            self.menu_items = self._api_list("/menu/items/?available_only=true")
        except Exception:
            self.menu_items = []

    # ─── CLEAR / REBUILD SCREEN ───────────────────────────────────────────────

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    # ═════════════════════════════════════════════════════════════════════════
    #  LOGIN SCREEN
    # ═════════════════════════════════════════════════════════════════════════
    def _show_login(self):
        self._clear()

        outer = tk.Frame(self, bg=t["bg"])
        outer.pack(fill="both", expand=True)

        # Left decorative panel
        deco = tk.Frame(outer, bg=t["accent"], width=420)
        deco.pack(side="left", fill="y")
        deco.pack_propagate(False)

        tk.Label(deco, text="🍽️", font=("Arial", 64),
                 bg=t["accent"], fg=t["bg"]).pack(pady=(120, 16))
        tk.Label(deco, text="Roe's", font=("Georgia", 42, "bold"),
                 bg=t["accent"], fg=t["bg"]).pack()
        tk.Label(deco, text="Restaurant POS", font=("Arial", 18),
                 bg=t["accent"], fg="#78350f").pack()
        tk.Frame(deco, bg="#d97706", height=2).pack(fill="x", padx=40, pady=32)
        tk.Label(deco, text="Point of Sale System\nClerk Terminal",
                 font=("Arial", 13), bg=t["accent"], fg="#78350f",
                 justify="center").pack()

        # Right — Login form
        right = tk.Frame(outer, bg=t["bg"])
        right.pack(side="left", fill="both", expand=True)

        card = tk.Frame(right, bg=t["card"],
                        highlightthickness=1, highlightbackground=t["border"])
        card.place(relx=0.5, rely=0.5, anchor="center", width=380, height=480)

        tk.Label(card, text="Staff Sign In", font=("Georgia", 20, "bold"),
                 bg=t["card"], fg=t["text"]).pack(pady=(32, 4))
        tk.Label(card, text="Enter your credentials", font=("Arial", 11),
                 bg=t["card"], fg=t["text_sub"]).pack(pady=(0, 24))

        # Email
        tk.Label(card, text="EMAIL ADDRESS", font=("Arial", 9, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        email_var = tk.StringVar()
        email_entry = tk.Entry(card, textvariable=email_var, font=("Arial", 11),
                               bg=t["input_bg"], fg=t["text"], insertbackground=t["text"],
                               relief="flat", bd=0, highlightthickness=1, highlightbackground=t["border"])
        email_entry.pack(fill="x", padx=32, ipady=8, pady=(4, 16))

        # Password
        tk.Label(card, text="PASSWORD", font=("Arial", 9, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        pass_var = tk.StringVar()
        pass_frame = tk.Frame(card, bg=t["input_bg"], highlightthickness=1, highlightbackground=t["border"])
        pass_frame.pack(fill="x", padx=32, pady=(4, 16))
        pass_entry = tk.Entry(pass_frame, textvariable=pass_var, show="●", font=("Arial", 11),
                              bg=t["input_bg"], fg=t["text"], insertbackground=t["text"],
                              relief="flat", bd=0, highlightthickness=0)
        pass_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(8, 0))

        # Eye toggle button
        show_pass_var = tk.BooleanVar(value=False)
        def _toggle_pass():
            show_pass_var.set(not show_pass_var.get())
            pass_entry.config(show="" if show_pass_var.get() else "●")
            eye_btn.config(text="🙈" if show_pass_var.get() else "👁")
        eye_btn = tk.Button(pass_frame, text="👁", font=("Arial", 13),
                            bg=t["input_bg"], fg=t["text_sub"],
                            relief="flat", bd=0, cursor="hand2",
                            activebackground=t["input_bg"], activeforeground=t["accent"],
                            command=_toggle_pass)
        eye_btn.pack(side="right", padx=6)

        # Error label
        err_lbl = tk.Label(card, text="", font=("Arial", 10),
                          bg=t["card"], fg=t["red"])
        err_lbl.pack(pady=(0, 12))

        def do_login(event=None):
            if not email_var.get() or not pass_var.get():
                err_lbl.config(text="⚠  Please fill in all fields.", fg=t["red"])
                return

            btn.config(state="disabled", text="Signing in…")
            err_lbl.config(text="")

            def work():
                try:
                    data = self._api("post", "/accounts/staff/login/", json={
                        'email': email_var.get().strip(),
                        'pin': pass_var.get().strip()
                    })
                    self.token = data.get("access")
                    self.staff = data.get("user") or {}
                    self.after(0, self._post_login)
                except Exception as exc:
                    msg = self._fmt_error(exc)
                    self.after(0, lambda: err_lbl.config(text=f"⚠  {msg}", fg=t["red"]))
                    self.after(0, lambda: btn.config(state="normal", text="Sign In  →"))

            threading.Thread(target=work, daemon=True).start()

        pass_entry.bind("<Return>", do_login)

        # Sign in button
        btn = tk.Button(card, text="Sign In  →", font=("Arial", 13, "bold"),
                        bg=t["accent"], fg="#000000",
                        activebackground="#e08c00", activeforeground="#000000",
                        relief="flat", bd=0, cursor="hand2", command=do_login)
        btn.pack(fill="x", padx=32, ipady=12, pady=(4, 0))
        def _btn_enter(e): btn.config(bg="#e08c00")
        def _btn_leave(e): btn.config(bg=t["accent"])
        btn.bind("<Enter>", _btn_enter)
        btn.bind("<Leave>", _btn_leave)

        # Divider
        div_f = tk.Frame(card, bg=t["card"])
        div_f.pack(fill="x", padx=32, pady=(12, 0))
        tk.Frame(div_f, bg=t["border"], height=1).pack(fill="x", side="left", expand=True)
        tk.Label(div_f, text="  or  ", font=("Arial", 9), bg=t["card"], fg=t["text_muted"]).pack(side="left")
        tk.Frame(div_f, bg=t["border"], height=1).pack(fill="x", side="left", expand=True)

        # Sign up button
        tk.Button(card, text="Create Staff Account", font=("Arial", 11),
                 bg=t["surface"], fg=t["text_sub"],
                 relief="flat", bd=0, cursor="hand2",
                 command=self._show_signup).pack(fill="x", padx=32, pady=(8, 16))

        # Open customer display toggle
        cust_f = tk.Frame(right, bg=t["bg"])
        cust_f.pack(side="bottom", pady=16)
        tk.Button(cust_f, text="📺  Open Customer Display",
                  font=("Arial", 10), bg=t["surface"], fg=t["text_sub"],
                  relief="flat", bd=0, cursor="hand2",
                  command=self._open_customer_display).pack()

        email_entry.focus()

    def _show_signup(self):
        """Staff registration screen — Clerk accounts only"""
        self._clear()

        outer = tk.Frame(self, bg=t["bg"])
        outer.pack(fill="both", expand=True)

        # Left decorative panel
        deco = tk.Frame(outer, bg=t["accent"], width=420)
        deco.pack(side="left", fill="y")
        deco.pack_propagate(False)

        tk.Label(deco, text="🍽️", font=("Arial", 64),
                 bg=t["accent"], fg=t["bg"]).pack(pady=(80, 16))
        tk.Label(deco, text="Create", font=("Georgia", 36, "bold"),
                 bg=t["accent"], fg=t["bg"]).pack()
        tk.Label(deco, text="Staff Account", font=("Arial", 16),
                 bg=t["accent"], fg="#78350f").pack()
        tk.Frame(deco, bg="#d97706", height=2).pack(fill="x", padx=40, pady=24)
        tk.Label(deco, text="Quick registration\nfor new staff members",
                 font=("Arial", 12), bg=t["accent"], fg="#78350f",
                 justify="center").pack()

        # Right — Form
        right = tk.Frame(outer, bg=t["bg"])
        right.pack(side="left", fill="both", expand=True)

        # Scrollable form
        canvas = tk.Canvas(right, bg=t["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(right, orient="vertical", command=canvas.yview)
        form_f = tk.Frame(canvas, bg=t["bg"])
        form_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form_f, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Card in the form
        card = tk.Frame(form_f, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        card.pack(padx=24, pady=24, fill="x", expand=True)

        tk.Label(card, text="Create New Account", font=("Georgia", 18, "bold"),
                 bg=t["card"], fg=t["text"]).pack(pady=(24, 4))
        tk.Label(card, text="All fields are required",
                 font=("Arial", 10), bg=t["card"], fg=t["text_sub"]).pack(pady=(0, 20))

        # Form fields
        fields = [
            ("Full Name", "", False),
            ("Email Address", "", False),
            ("Password", "", True),
            ("Confirm Password", "", True),
        ]
        vars_ = {}
        for label, default, is_secret in fields:
            tk.Label(card, text=label.upper(), font=("Arial", 8, "bold"),
                     bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=24)
            v = tk.StringVar(value=default)
            vars_[label] = v
            entry_f = tk.Frame(card, bg=t["input_bg"], highlightthickness=1, highlightbackground=t["border"])
            entry_f.pack(fill="x", padx=24, pady=(3, 12))
            entry = tk.Entry(entry_f, textvariable=v, show="●" if is_secret else "",
                            font=("Arial", 11), bg=t["input_bg"], fg=t["text"],
                            insertbackground=t["text"], relief="flat", bd=0, highlightthickness=0)
            entry.pack(fill="x", ipady=7, padx=6)

        # Error label
        err_lbl = tk.Label(card, text="", font=("Arial", 10), bg=t["card"], fg=t["red"])
        err_lbl.pack(pady=(0, 12))

        def do_signup():
            # Validation
            name = vars_["Full Name"].get().strip()
            email = vars_["Email Address"].get().strip()
            password = vars_["Password"].get().strip()
            password_confirm = vars_["Confirm Password"].get().strip()

            if not all([name, email, password, password_confirm]):
                err_lbl.config(text="⚠  All fields required", fg=t["red"])
                return
            if len(password) < 6:
                err_lbl.config(text="⚠  Password must be at least 6 characters", fg=t["red"])
                return
            if password != password_confirm:
                err_lbl.config(text="⚠  Passwords do not match", fg=t["red"])
                return

            btn.config(state="disabled", text="Creating account…")
            err_lbl.config(text="")

            def work():
                try:
                    # Create clerk account via staff endpoint
                    data = self._api("post", "/accounts/staff/", json={
                        'staffName': name,
                        'email': email,
                        'pin': password,
                        'confirm_pin': password_confirm,
                        'role': 'Clerk'
                    })
                    self.after(0, lambda: messagebox.showinfo(
                        "Success", f"Account created! You can now sign in.", parent=self))
                    self.after(0, self._show_login)
                except Exception as exc:
                    msg = self._fmt_error(exc)
                    self.after(0, lambda: err_lbl.config(text=f"⚠  {msg}", fg=t["red"]))
                    self.after(0, lambda: btn.config(state="normal", text="Create Account  →"))

            threading.Thread(target=work, daemon=True).start()

        # Buttons
        btn_f = tk.Frame(card, bg=t["card"])
        btn_f.pack(fill="x", padx=24, pady=(0, 24))

        btn = tk.Button(btn_f, text="Create Account  →", font=("Arial", 12, "bold"),
                       bg=t["accent"], fg="#000000", relief="flat", bd=0,
                       cursor="hand2", activebackground="#e08c00", activeforeground="#000000",
                       command=do_signup)
        btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        btn.bind("<Enter>", lambda e: btn.config(bg="#e08c00"))
        btn.bind("<Leave>", lambda e: btn.config(bg=t["accent"]))

        tk.Button(btn_f, text="Back", font=("Arial", 12, "bold"),
                 bg=t["surface"], fg=t["text_sub"], relief="flat", bd=0,
                 cursor="hand2", command=self._show_login).pack(side="left", fill="x", expand=True)

    def _post_login(self):
        """After successful login — load menu then show main UI."""
        def work():
            self._load_menu()
            self.after(0, self._show_main)
        threading.Thread(target=work, daemon=True).start()

    # ═════════════════════════════════════════════════════════════════════════
    #  MAIN POS INTERFACE
    # ═════════════════════════════════════════════════════════════════════════
    def _show_main(self):
        self._clear()

        root = tk.Frame(self, bg=t["bg"])
        root.pack(fill="both", expand=True)

        self._build_header(root)

        body = tk.Frame(root, bg=t["bg"])
        body.pack(fill="both", expand=True)

        # ── Left: menu browser (65%) ──────────────────────────────────────
        left = tk.Frame(body, bg=t["bg"])
        left.place(relx=0, rely=0, relwidth=0.63, relheight=1.0)
        self._build_menu_panel(left)

        # ── Right: cart / order panel (35%) ──────────────────────────────
        right = tk.Frame(body, bg=t["surface"],
                         highlightthickness=1, highlightbackground=t["border"])
        right.place(relx=0.63, rely=0, relwidth=0.37, relheight=1.0)
        self._build_cart_panel(right)

    # ─── HEADER ───────────────────────────────────────────────────────────────
    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=t["card"],
                       highlightthickness=1, highlightbackground=t["border"],
                       height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Logo
        tk.Label(hdr, text="🍽️  Roe's POS", font=("Georgia", 17, "bold"),
                 bg=t["card"], fg=t["accent"]).pack(side="left", padx=20)

        # Right controls
        ctrl = tk.Frame(hdr, bg=t["card"])
        ctrl.pack(side="right", padx=16)

        # Staff name
        name = (self.staff or {}).get("staffName") or (self.staff or {}).get("email") or "Staff"
        tk.Label(ctrl, text=f"👤  {name}", font=("Arial", 11),
                 bg=t["card"], fg=t["text_sub"]).pack(side="left", padx=(0, 16))

        # Clock
        self._clock_lbl = tk.Label(ctrl, text="", font=("Arial", 11),
                                    bg=t["card"], fg=t["text_muted"])
        self._clock_lbl.pack(side="left", padx=(0, 16))
        self._tick_header()

        # Reload menu
        self._hdr_btn(ctrl, "↻  Menu", self._reload_menu, t["surface"])

        # Customer display
        self._hdr_btn(ctrl, "📺  Display", self._open_customer_display, t["surface"])

        # Logout
        self._hdr_btn(ctrl, "Sign Out", self._logout, t["red_dim"])

    def _hdr_btn(self, parent, text, cmd, bg):
        b = tk.Button(parent, text=text, font=("Arial", 10, "bold"),
                      bg=bg, fg=t["text_sub"], relief="flat", bd=0,
                      cursor="hand2", padx=10, pady=4,
                      activebackground=t["border"], activeforeground=t["text"],
                      command=cmd)
        b.pack(side="left", padx=4)
        b.bind("<Enter>", lambda e: b.config(bg=t["border"]))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def _tick_header(self):
        if self._clock_lbl.winfo_exists():
            self._clock_lbl.config(text=datetime.now().strftime("%I:%M %p"))
            self.after(30000, self._tick_header)

    # ─── MENU PANEL (left) ────────────────────────────────────────────────────
    def _build_menu_panel(self, parent):
        # Category tab bar
        cat_bar = tk.Frame(parent, bg=t["card"], height=48)
        cat_bar.pack(fill="x")
        cat_bar.pack_propagate(False)

        self._cat_btns = []

        def make_cat_btn(label, cat_id):
            active = (cat_id == self.active_cat)
            bg = t["accent"] if active else t["surface"]
            fg = t["bg"] if active else t["text_sub"]
            b = tk.Button(cat_bar, text=label, font=("Arial", 10, "bold"),
                          bg=bg, fg=fg, relief="flat", bd=0, cursor="hand2",
                          padx=16, pady=0,
                          activebackground=t["accent_hover"], activeforeground=t["bg"],
                          command=lambda c=cat_id: self._filter_category(c))
            b.pack(side="left", fill="y")
            self._cat_btns.append((b, cat_id))

        make_cat_btn("All", None)
        for cat in self.categories:
            make_cat_btn(cat.get("name", ""), cat.get("categoryId"))

        # Search bar
        search_f = tk.Frame(parent, bg=t["bg"], pady=8, padx=12)
        search_f.pack(fill="x")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_menu_grid())
        entry_f = tk.Frame(search_f, bg=t["input_bg"],
                           highlightthickness=1, highlightbackground=t["border"])
        entry_f.pack(fill="x")
        tk.Label(entry_f, text="🔍", font=("Arial", 12), bg=t["input_bg"],
                 fg=t["text_muted"]).pack(side="left", padx=(8, 2))
        tk.Entry(entry_f, textvariable=self._search_var,
                 font=("Arial", 12), bg=t["input_bg"], fg=t["text"],
                 insertbackground=t["text"], relief="flat", bd=0,
                 highlightthickness=0).pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))

        # Grid area
        self._menu_scroll = ScrollFrame(parent, bg=t["bg"])
        self._menu_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._menu_grid_frame = self._menu_scroll.inner

        self._refresh_menu_grid()

    def _filter_category(self, cat_id):
        self.active_cat = cat_id
        # Update button styles
        for b, cid in self._cat_btns:
            if cid == cat_id:
                b.config(bg=t["accent"], fg=t["bg"])
            else:
                b.config(bg=t["surface"], fg=t["text_sub"])
        self._refresh_menu_grid()

    def _refresh_menu_grid(self):
        for w in self._menu_grid_frame.winfo_children():
            w.destroy()

        q = self._search_var.get().strip().lower()

        items = self.menu_items
        if self.active_cat:
            items = [i for i in items
                     if str(i.get("category") or i.get("categoryId") or "") == str(self.active_cat)]
        if q:
            items = [i for i in items if q in (i.get("name") or "").lower()]

        if not items:
            tk.Label(self._menu_grid_frame,
                     text="No items found" if q or self.active_cat else "No menu items loaded.",
                     font=("Arial", 14), bg=t["bg"], fg=t["text_muted"]).pack(pady=60)
            return

        # 4-column grid
        COLS = 4
        row_f = None
        for idx, item in enumerate(items):
            if idx % COLS == 0:
                row_f = tk.Frame(self._menu_grid_frame, bg=t["bg"])
                row_f.pack(fill="x", pady=5)
            self._menu_card(row_f, item)

    def _menu_card(self, parent, item):
        iid   = str(item.get("menuItemId") or item.get("id") or "")
        name  = item.get("name", "Item")
        price = float(item.get("price") or 0)
        cat_name = ""
        if item.get("category"):
            c = next((x for x in self.categories
                      if str(x.get("categoryId")) == str(item.get("category"))), None)
            if c:
                cat_name = c.get("name", "")

        in_cart = iid in self.cart

        card = tk.Frame(parent, bg=t["card"] if not in_cart else t["blue_dim"],
                        highlightthickness=1,
                        highlightbackground=t["blue"] if in_cart else t["border"],
                        width=148, height=110)
        card.pack(side="left", padx=5)
        card.pack_propagate(False)

        def on_click(event=None, i=item, c=card, _iid=iid):
            self._add_to_cart(i)
            # Flash feedback
            if c.winfo_exists():
                c.config(highlightbackground=t["accent"], bg=t["accent_dim"])
                self.after(150, lambda: c.config(
                    highlightbackground=t["blue"] if _iid in self.cart else t["border"],
                    bg=t["blue_dim"] if _iid in self.cart else t["card"]
                ) if c.winfo_exists() else None)

        for widget_or_frame in [card]:
            widget_or_frame.bind("<Button-1>", on_click)
            widget_or_frame.bind("<Enter>", lambda e, c=card, _iid=iid: c.config(
                bg=t["blue_dim"] if _iid in self.cart else t["card2"]))
            widget_or_frame.bind("<Leave>", lambda e, c=card, _iid=iid: c.config(
                bg=t["blue_dim"] if _iid in self.cart else t["card"]))

        # Category badge
        badge_f = tk.Frame(card, bg=t["card"] if not in_cart else t["blue_dim"])
        badge_f.pack(anchor="ne", padx=6, pady=(6, 0))
        if cat_name:
            tk.Label(badge_f, text=cat_name, font=("Arial", 7),
                     bg=t["tag_bg"], fg=t["text_sub"],
                     padx=4, pady=1).pack(side="right")
        badge_f.bind("<Button-1>", on_click)

        # Item name
        nm = tk.Label(card, text=name, font=("Arial", 11, "bold"),
                      bg=card["bg"], fg=t["text"], wraplength=136, justify="center")
        nm.pack(pady=(2, 2), padx=6)
        nm.bind("<Button-1>", on_click)

        # Price
        pr = tk.Label(card, text=fmt(price), font=("Arial", 12, "bold"),
                      bg=card["bg"], fg=t["accent"])
        pr.pack()
        pr.bind("<Button-1>", on_click)

        # Cart qty badge
        if in_cart:
            qty = self.cart[iid]["qty"]
            ql = tk.Label(card, text=f"  {qty} in cart  ",
                          font=("Arial", 8, "bold"),
                          bg=t["blue"], fg="#fff")
            ql.pack(pady=(4, 0))
            ql.bind("<Button-1>", on_click)

    # ─── CART PANEL (right) ───────────────────────────────────────────────────
    def _build_cart_panel(self, parent):
        self._cart_parent = parent

        # Header
        ch = tk.Frame(parent, bg=t["surface"], pady=12)
        ch.pack(fill="x", padx=16)
        tk.Label(ch, text="🛒  Current Order", font=("Georgia", 15, "bold"),
                 bg=t["surface"], fg=t["text"]).pack(side="left")
        tk.Label(ch, textvariable=self._cart_count_var(),
                 font=("Arial", 10), bg=t["surface"], fg=t["text_sub"]).pack(side="right")

        tk.Frame(parent, bg=t["border"], height=1).pack(fill="x")

        # Table / order type row
        meta_f = tk.Frame(parent, bg=t["surface"], pady=8, padx=16)
        meta_f.pack(fill="x")
        tk.Label(meta_f, text="Table / Note:", font=("Arial", 10),
                 bg=t["surface"], fg=t["text_sub"]).pack(side="left")
        self._table_var = tk.StringVar()
        te = tk.Entry(meta_f, textvariable=self._table_var,
                      font=("Arial", 10), bg=t["input_bg"], fg=t["text"],
                      insertbackground=t["text"], relief="flat",
                      highlightthickness=1, highlightbackground=t["border"],
                      width=12)
        te.pack(side="left", padx=(8, 0), ipady=4)

        # Scrollable cart items
        self._cart_scroll_outer = tk.Frame(parent, bg=t["surface"])
        self._cart_scroll_outer.pack(fill="both", expand=True, padx=8, pady=4)
        self._cart_sf = ScrollFrame(self._cart_scroll_outer, bg=t["surface"])
        self._cart_sf.pack(fill="both", expand=True)
        self._cart_inner = self._cart_sf.inner

        # Totals area
        tot_f = tk.Frame(parent, bg=t["card"],
                         highlightthickness=1, highlightbackground=t["border"])
        tot_f.pack(fill="x", padx=8, pady=(0, 4))
        tk.Frame(tot_f, bg=t["border"], height=1).pack(fill="x")
        self._subtotal_lbl = tk.Label(tot_f, text="Subtotal: ₦0",
                                       font=("Arial", 11), bg=t["card"], fg=t["text_sub"])
        self._subtotal_lbl.pack(anchor="e", padx=16, pady=(8, 2))
        self._total_lbl = tk.Label(tot_f, text="TOTAL   ₦0",
                                    font=("Arial", 18, "bold"), bg=t["card"], fg=t["accent"])
        self._total_lbl.pack(anchor="e", padx=16, pady=(0, 10))

        # Action buttons
        btn_f = tk.Frame(parent, bg=t["surface"])
        btn_f.pack(fill="x", padx=8, pady=(0, 8))

        self._pay_btn = self._action_btn(
            btn_f, "💳  Pay Now", self._open_payment, t["green"], "#fff", big=True)
        self._pay_btn.pack(fill="x", ipady=12, pady=(0, 6))

        row2 = tk.Frame(btn_f, bg=t["surface"])
        row2.pack(fill="x")
        self._action_btn(row2, "📋  Hold", self._hold_order, t["blue_dim"], t["blue"]).pack(
            side="left", fill="x", expand=True, ipady=8, padx=(0, 4))
        self._action_btn(row2, "🗑  Clear", self._clear_cart, t["red_dim"], t["red"]).pack(
            side="left", fill="x", expand=True, ipady=8)

        self._refresh_cart()

    def _cart_count_var(self):
        # returns a string describing total items
        self._cart_count = tk.StringVar(value="Empty")
        return self._cart_count

    def _action_btn(self, parent, text, cmd, bg, fg, big=False):
        b = tk.Button(parent, text=text,
                      font=("Arial", 12 if big else 10, "bold"),
                      bg=bg, fg=fg, relief="flat", bd=0, cursor="hand2",
                      activebackground=t["border"], activeforeground=fg,
                      command=cmd)
        b.bind("<Enter>", lambda e: b.config(bg=t["border2"]))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    # ─── CART LOGIC ───────────────────────────────────────────────────────────

    def _add_to_cart(self, item):
        iid   = str(item.get("menuItemId") or item.get("id") or "")
        name  = item.get("name", "Item")
        price = float(item.get("price") or 0)

        if iid in self.cart:
            self.cart[iid]["qty"] += 1
        else:
            self.cart[iid] = {"name": name, "unit_price": price, "qty": 1, "raw": item}

        self._refresh_cart()
        self._refresh_menu_grid()
        self._push_customer_display()

    def _remove_from_cart(self, iid):
        if iid in self.cart:
            del self.cart[iid]
        self._refresh_cart()
        self._refresh_menu_grid()
        self._push_customer_display()

    def _set_qty(self, iid, qty):
        if qty <= 0:
            self._remove_from_cart(iid)
        else:
            self.cart[iid]["qty"] = qty
            self._refresh_cart()
            self._push_customer_display()

    def _cart_total(self):
        return sum(e["unit_price"] * e["qty"] for e in self.cart.values())

    def _refresh_cart(self):
        for w in self._cart_inner.winfo_children():
            w.destroy()

        if not self.cart:
            tk.Label(self._cart_inner,
                     text="Cart is empty\n\nTap menu items to add them",
                     font=("Arial", 12), bg=t["surface"],
                     fg=t["text_muted"], justify="center").pack(pady=48)
            self._cart_count.set("Empty")
            self._subtotal_lbl.config(text="Subtotal: ₦0")
            self._total_lbl.config(text="TOTAL   ₦0")
            return

        total_qty = sum(e["qty"] for e in self.cart.values())
        self._cart_count.set(f"{total_qty} item{'s' if total_qty != 1 else ''}")

        for iid, entry in list(self.cart.items()):
            self._cart_row(self._cart_inner, iid, entry)

        total = self._cart_total()
        self._subtotal_lbl.config(text=f"Subtotal: {fmt(total)}")
        self._total_lbl.config(text=f"TOTAL   {fmt(total)}")

    def _cart_row(self, parent, iid, entry):
        row = tk.Frame(parent, bg=t["card"],
                       highlightthickness=1, highlightbackground=t["border"])
        row.pack(fill="x", pady=3, padx=2)

        # Item name + price
        info = tk.Frame(row, bg=t["card"])
        info.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        tk.Label(info, text=entry["name"], font=("Arial", 11, "bold"),
                 bg=t["card"], fg=t["text"], anchor="w").pack(fill="x")
        tk.Label(info, text=f"{fmt(entry['unit_price'])} each",
                 font=("Arial", 9), bg=t["card"], fg=t["text_sub"], anchor="w").pack(fill="x")

        # Controls
        ctrl = tk.Frame(row, bg=t["card"])
        ctrl.pack(side="right", padx=8, pady=8)

        # Line total
        tk.Label(ctrl, text=fmt(entry["unit_price"] * entry["qty"]),
                 font=("Arial", 11, "bold"), bg=t["card"], fg=t["accent"]).pack(side="right", padx=(8, 0))

        # Qty stepper
        step = tk.Frame(ctrl, bg=t["card"])
        step.pack(side="right")

        _minus = tk.Button(step, text="−", font=("Arial", 13, "bold"),
                           bg=t["surface"], fg=t["red"], relief="flat", bd=0,
                           cursor="hand2", width=2,
                           command=lambda _iid=iid, e=entry: self._set_qty(_iid, e["qty"] - 1))
        _minus.pack(side="left")

        tk.Label(step, text=str(entry["qty"]), font=("Arial", 13, "bold"),
                 bg=t["card"], fg=t["text"], width=3).pack(side="left")

        _plus = tk.Button(step, text="+", font=("Arial", 13, "bold"),
                          bg=t["surface"], fg=t["green"], relief="flat", bd=0,
                          cursor="hand2", width=2,
                          command=lambda _iid=iid, e=entry: self._set_qty(_iid, e["qty"] + 1))
        _plus.pack(side="left")

        # Remove
        tk.Button(ctrl, text="✕", font=("Arial", 10),
                  bg=t["surface"], fg=t["red"], relief="flat", bd=0,
                  cursor="hand2",
                  command=lambda _iid=iid: self._remove_from_cart(_iid)).pack(side="right", padx=(0, 4))

    def _ask_customer_name(self):
        """Show dialog to ask for customer name when holding an order."""
        win = tk.Toplevel(self)
        win.title("Hold Order - Customer Name")
        win.configure(bg=t["card"])
        win.geometry("400x180")
        win.resizable(False, False)
        win.grab_set()
        win.transient(self)
        
        # Accent bar
        tk.Frame(win, bg=t["accent"], height=6).pack(fill="x")
        
        # Label
        tk.Label(win, text="Customer Name", font=("Arial", 12, "bold"),
                 bg=t["card"], fg=t["text"]).pack(pady=(20, 8), padx=20, anchor="w")
        
        # Input field
        name_var = tk.StringVar()
        entry = tk.Entry(win, textvariable=name_var,
                        font=("Arial", 12), bg=t["input_bg"], fg=t["text"],
                        insertbackground=t["text"], relief="flat",
                        highlightthickness=1, highlightbackground=t["border"])
        entry.pack(fill="x", padx=20, ipady=8)
        entry.focus()
        
        result = [None]  # Use list to capture result in nested function
        
        def confirm():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Required", "Please enter a customer name.", parent=win)
                return
            result[0] = name
            win.destroy()
        
        def cancel():
            result[0] = None
            win.destroy()
        
        # Buttons
        btn_f = tk.Frame(win, bg=t["card"])
        btn_f.pack(fill="x", padx=20, pady=(20, 16))
        
        ok_btn = tk.Button(btn_f, text="Confirm", font=("Arial", 11, "bold"),
                          bg=t["green"], fg="#fff", relief="flat", bd=0,
                          cursor="hand2", command=confirm)
        ok_btn.pack(side="right", padx=(4, 0), ipady=6, ipadx=12)
        
        cancel_btn = tk.Button(btn_f, text="Cancel", font=("Arial", 11, "bold"),
                              bg=t["surface"], fg=t["text_sub"], relief="flat", bd=0,
                              cursor="hand2", command=cancel)
        cancel_btn.pack(side="right", ipady=6, ipadx=12)
        
        # Allow Enter to confirm
        entry.bind("<Return>", lambda e: confirm())
        entry.bind("<Escape>", lambda e: cancel())
        
        # Wait for dialog to close
        self.wait_window(win)
        
        return result[0]

    def _clear_cart(self):
        if not self.cart:
            return
        if messagebox.askyesno("Clear Order", "Remove all items from the current order?", parent=self):
            self.cart.clear()
            self.current_order_id = None
            self._refresh_cart()
            self._refresh_menu_grid()
            self._push_customer_display()

    def _hold_order(self):
        """Save the current order to the backend as Pending without paying."""
        if not self.cart:
            messagebox.showwarning("Empty Order", "Nothing in cart to hold.", parent=self)
            return
        
        # Ask for customer name
        customer_name = self._ask_customer_name()
        if customer_name is None:  # User cancelled
            return
        
        def work():
            try:
                payload = self._build_order_payload(status="Pending", customer_name=customer_name)
                result = self._api("post", "/orders/orders/", json=payload)
                self.current_order_id = result.get("orderId") or result.get("id")
                self.after(0, lambda: messagebox.showinfo(
                    "Order Held",
                    f"Order held for {customer_name}\n#{self.current_order_id or 'N/A'}. Cart cleared.",
                    parent=self))
                self.cart.clear()
                self.after(0, self._refresh_cart)
                self.after(0, self._refresh_menu_grid)
                self.after(0, self._push_customer_display)
            except Exception as exc:
                error_msg = self._fmt_error(exc)
                self.after(0, lambda: messagebox.showerror(
                    "Hold Failed", error_msg, parent=self))
        threading.Thread(target=work, daemon=True).start()

    def _build_order_payload(self, status="Pending", payment_method=None, customer_name=None):
        items_payload = []
        for iid, entry in self.cart.items():
            items_payload.append({
                "menuItem": iid,
                "quantity": entry["qty"],
                "unitPrice": entry["unit_price"],
                "notes": ""
            })
        payload = {
            "items":        items_payload,
            "totalAmount":  self._cart_total(),
            "status":       status,
            "tableNumber":  self._table_var.get().strip() or None,
            "orderType":    "DineIn",
        }
        if customer_name:
            payload["customerName"] = customer_name
        if status == "Paid":
            payload["paymentStatus"] = "Paid"
        if payment_method:
            payload["paymentMethod"] = payment_method
        return payload

    # ─── PAYMENT FLOW ─────────────────────────────────────────────────────────
    def _open_payment(self):
        if not self.cart:
            messagebox.showwarning("Empty Order", "Add items before paying.", parent=self)
            return

        total = self._cart_total()
        win = tk.Toplevel(self)
        win.title("Process Payment")
        win.configure(bg=t["card"])
        win.geometry("480x580")
        win.resizable(False, False)
        win.grab_set()

        # Accent bar
        tk.Frame(win, bg=t["accent"], height=6).pack(fill="x")

        tk.Label(win, text="💳  Process Payment", font=("Georgia", 16, "bold"),
                 bg=t["card"], fg=t["text"]).pack(pady=(20, 4), padx=32, anchor="w")
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=32)

        # Order summary
        sum_f = tk.Frame(win, bg=t["surface"],
                         highlightthickness=1, highlightbackground=t["border"])
        sum_f.pack(fill="x", padx=32, pady=(16, 0))
        for iid, e in self.cart.items():
            rf = tk.Frame(sum_f, bg=t["surface"])
            rf.pack(fill="x", padx=12, pady=3)
            tk.Label(rf, text=f"{e['qty']}×  {e['name']}",
                     font=("Arial", 10), bg=t["surface"], fg=t["text"]).pack(side="left")
            tk.Label(rf, text=fmt(e["unit_price"] * e["qty"]),
                     font=("Arial", 10, "bold"), bg=t["surface"], fg=t["text"]).pack(side="right")

        tk.Frame(sum_f, bg=t["border"], height=1).pack(fill="x", padx=12, pady=4)
        tot_row = tk.Frame(sum_f, bg=t["surface"])
        tot_row.pack(fill="x", padx=12, pady=(0, 10))
        tk.Label(tot_row, text="TOTAL", font=("Arial", 13, "bold"),
                 bg=t["surface"], fg=t["text"]).pack(side="left")
        tk.Label(tot_row, text=fmt(total), font=("Arial", 16, "bold"),
                 bg=t["surface"], fg=t["accent"]).pack(side="right")

        # Payment method
        tk.Label(win, text="PAYMENT METHOD", font=("Arial", 9, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32, pady=(18, 4))
        method_var = tk.StringVar(value="Cash")
        methods = [("💵  Cash", "Cash"), ("💳  Card / POS", "Card"), ("📱  Transfer", "Transfer")]
        mf = tk.Frame(win, bg=t["card"])
        mf.pack(padx=32)
        for label, val in methods:
            b = tk.Button(mf, text=label, font=("Arial", 11, "bold"),
                          bg=t["surface"], fg=t["text_sub"],
                          relief="flat", bd=0, cursor="hand2",
                          padx=14, pady=10)
            b.pack(side="left", padx=5)

            def select(v=val, btn=b):
                method_var.set(v)
                for child in mf.winfo_children():
                    child.config(bg=t["surface"], fg=t["text_sub"])
                btn.config(bg=t["accent"], fg=t["bg"])

            b.config(command=select)
            if val == "Cash":
                b.config(bg=t["accent"], fg=t["bg"])

        # Cash tendered (for cash payments)
        tk.Label(win, text="CASH TENDERED  (leave blank to skip)",
                 font=("Arial", 9, "bold"), bg=t["card"], fg=t["text_sub"]).pack(
                 anchor="w", padx=32, pady=(16, 4))
        cash_f = tk.Frame(win, bg=t["input_bg"],
                          highlightthickness=1, highlightbackground=t["border"])
        cash_f.pack(fill="x", padx=32)
        cash_var = tk.StringVar()
        tk.Entry(cash_f, textvariable=cash_var, font=("Arial", 13),
                 bg=t["input_bg"], fg=t["text"], insertbackground=t["text"],
                 relief="flat", bd=0, highlightthickness=0).pack(
                 fill="x", ipady=9, padx=8)

        err_lbl = tk.Label(win, text="", font=("Arial", 10),
                           bg=t["card"], fg=t["red"])
        err_lbl.pack(pady=(8, 0))

        def complete():
            method = method_var.get()
            cash_raw = cash_var.get().strip()
            change = 0.0
            if method == "Cash" and cash_raw:
                try:
                    tendered = float(cash_raw)
                    if tendered < total:
                        err_lbl.config(text=f"⚠  Cash tendered ({fmt(tendered)}) is less than total ({fmt(total)})")
                        return
                    change = tendered - total
                except ValueError:
                    err_lbl.config(text="⚠  Enter a valid cash amount")
                    return

            confirm_btn.config(state="disabled", text="Processing…")

            def work():
                try:
                    payload = self._build_order_payload(status="Completed", payment_method=method)
                    result  = self._api("post", "/orders/orders/", json=payload)
                    order_id = result.get("orderId") or result.get("id")
                    self.after(0, lambda: self._payment_done(win, method, total, change, order_id))
                except Exception as exc:
                    self.after(0, lambda: err_lbl.config(text=f"⚠  {self._fmt_error(exc)}"))
                    self.after(0, lambda: confirm_btn.config(state="normal", text="✅  Confirm Payment"))

            threading.Thread(target=work, daemon=True).start()

        confirm_btn = tk.Button(win, text="✅  Confirm Payment",
                                font=("Arial", 13, "bold"),
                                bg=t["green"], fg="#fff",
                                relief="flat", bd=0, cursor="hand2",
                                command=complete)
        confirm_btn.pack(fill="x", padx=32, ipady=12, pady=(12, 6))
        confirm_btn.bind("<Enter>", lambda e: confirm_btn.config(bg="#059669"))
        confirm_btn.bind("<Leave>", lambda e: confirm_btn.config(bg=t["green"]))

        tk.Button(win, text="Cancel", font=("Arial", 10),
                  bg=t["surface"], fg=t["text_sub"], relief="flat",
                  bd=0, cursor="hand2", command=win.destroy).pack(
                  fill="x", padx=32, ipady=6)

    def _payment_done(self, win, method, total, change, order_id):
        win.destroy()
        # Update customer display first
        if self.customer_display and self.customer_display.winfo_exists():
            self.customer_display.show_payment_success(method, total, change)

        # Generate and print receipt
        if order_id:
            try:
                # Generate receipt
                gen_result = self._api("post", "/orders/receipts/generate_for_order/", 
                                     json={"order_id": order_id, "format": "Thermal"})
                receipt_id = gen_result["receipt"]["receiptId"]
                
                # Get thermal text
                text_result = self._api("get", f"/orders/receipts/{receipt_id}/text_format/")
                receipt_text = text_result["content"]
                
                # Print receipt
                self._print_receipt(receipt_text)
                
            except Exception as e:
                messagebox.showerror("Receipt Error", f"Failed to generate receipt: {self._fmt_error(e)}", parent=self)

        # Receipt summary
        msg = f"Payment received!\n\nAmount: {fmt(total)}\nMethod: {method}"
        if change > 0:
            msg += f"\nChange: {fmt(change)}"
        if order_id:
            msg += f"\nOrder ID: {order_id}"
        messagebox.showinfo("✅  Payment Complete", msg, parent=self)

        # Clear for next order
        self.cart.clear()
        self.current_order_id = None
        self._table_var.set("")
        self._refresh_cart()
        self._refresh_menu_grid()

    def _print_receipt(self, receipt_text):
        """Print receipt to thermal printer"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(receipt_text)
                temp_file = f.name
            
            # Print to thermal printer (assuming printer name)
            # For X-Q200, adjust printer name as needed
            printer_name = "Thermal Printer"  # Change this to your printer name
            result = os.system(f'print /d:"{printer_name}" "{temp_file}"')
            
            # Clean up
            os.unlink(temp_file)
            
            if result != 0:
                # Printing failed, show receipt in messagebox
                messagebox.showinfo("Receipt", receipt_text, parent=self)
            
        except Exception as e:
            # If any error occurs, show receipt in messagebox
            messagebox.showinfo("Receipt", receipt_text, parent=self)

    # ─── CUSTOMER DISPLAY ─────────────────────────────────────────────────────
    def _open_customer_display(self):
        if self.customer_display and self.customer_display.winfo_exists():
            self.customer_display.focus()
            return
        self.customer_display = CustomerDisplay(self)

    def _push_customer_display(self):
        if self.customer_display and self.customer_display.winfo_exists():
            items = [
                {"name": e["name"], "qty": e["qty"], "unit_price": e["unit_price"]}
                for e in self.cart.values()
            ]
            self.customer_display.update_order(items, self._cart_total())

    # ─── MENU RELOAD ──────────────────────────────────────────────────────────
    def _reload_menu(self):
        def work():
            self._load_menu()
            self.after(0, self._refresh_menu_grid)
        threading.Thread(target=work, daemon=True).start()

    # ─── LOGOUT ───────────────────────────────────────────────────────────────
    def _logout(self):
        if self.cart and not messagebox.askyesno(
            "Unsaved Order",
            "You have items in the cart. Log out and lose them?",
            parent=self
        ):
            return
        self.token  = None
        self.staff  = None
        self.cart.clear()
        self.menu_items = []
        self.categories = []
        self.active_cat = None
        self.current_order_id = None
        if self.customer_display and self.customer_display.winfo_exists():
            self.customer_display.destroy()
        self._show_login()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = POSApp()
    app.mainloop()