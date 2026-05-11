"""
Roe's POS — Administrator Dashboard
A full-featured Tkinter admin panel.
Run with: python roes_admin.py
"""

from os import name
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
from unicodedata import name
import requests
from requests.exceptions import RequestException

# ─────────────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────────────
DARK = {
    "bg":         "#090e1a",
    "surface":    "#0f1629",
    "card":       "#131d35",
    "border":     "#1e2d4a",
    "accent":     "#f59e0b",
    "accent_dim": "#78491a",
    "text":       "#f0f4ff",
    "text_sub":   "#6b7fa3",
    "text_muted": "#3d4f6e",
    "green":      "#10b981",
    "red":        "#ef4444",
    "blue":       "#3b82f6",
    "purple":     "#8b5cf6",
    "nav_bg":     "#0a1020",
    "input_bg":   "#0d1628",
    "row_hover":  "#1a2744",
    "tag_bg":     "#1a2744",
}
LIGHT = {
    "bg":         "#f4f6fb",
    "surface":    "#ffffff",
    "card":       "#ffffff",
    "border":     "#dde3ef",
    "accent":     "#d97706",
    "accent_dim": "#fde68a",
    "text":       "#0f172a",
    "text_sub":   "#4a5568",
    "text_muted": "#94a3b8",
    "green":      "#059669",
    "red":        "#dc2626",
    "blue":       "#2563eb",
    "purple":     "#7c3aed",
    "nav_bg":     "#ffffff",
    "input_bg":   "#f8fafc",
    "row_hover":  "#f0f4ff",
    "tag_bg":     "#f1f5f9",
}

# ─────────────────────────────────────────────────────────────────────────────
# STATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fmt(n):
    try:
        return f"₦{int(n):,}"
    except (TypeError, ValueError):
        return "₦0"


def stock_status(item):
    qty       = item.get("quantityInStock", item.get("qty", 0))
    threshold = item.get("lowStockThreshold", item.get("threshold", 0))
    try:
        qty       = float(qty)
        threshold = float(threshold)
    except (TypeError, ValueError):
        qty = threshold = 0

    if qty == 0:
        return "Out"
    if threshold and qty <= threshold:
        return "Low"
    return "OK"


def normalize_response(data):
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []

STATUS_COLORS = {
    "Paid":       ("green",  "#10b981"),
    "Preparing":  ("accent", "#f59e0b"),
    "Ready":      ("blue",   "#3b82f6"),
    "Cancelled":  ("red",    "#ef4444"),
    "Active":     ("green",  "#10b981"),
    "Inactive":   ("muted",  "#6b7fa3"),
    "Draft":      ("muted",  "#6b7fa3"),
    "Ordered":    ("blue",   "#3b82f6"),
    "Received":   ("green",  "#10b981"),
    "OK":         ("green",  "#10b981"),
    "Low":        ("accent", "#f59e0b"),
    "Out":        ("red",    "#ef4444"),
}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class RoesAdmin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Roe's Food — Admin Dashboard")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.is_dark = True
        self.t = DARK
        self.configure(bg=self.t["bg"])
        self.active_page = None
        self.api_base = "https://roe-s-pos-production.up.railway.app/api/v1"
        self.token = None
        self.refresh_token = None
        self.user = None
        self.session = requests.Session()
        self.orders = []
        self.store = []
        self.menu_items = []
        self.inventory_items = []
        self.suppliers = []
        self.purchase_orders = []
        self.notifications = []
        self.staff_list = []
        self.categories = []
        self._setup_headers()
        self.admin_exists = True
        self._check_admin_setup()
        self._show_intro()

    @staticmethod
    def safe_float(v):
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    def _get_order_total(self, order):
        amount = order.get("totalAmount") or order.get("amount") or 0
        if self.safe_float(amount) <= 0:
            items = order.get("items") or []
            amount = sum(
                self.safe_float(item.get("lineTotal") or item.get("unitPrice"))
                * self.safe_float(item.get("quantity"))
                for item in items
            )
        return amount

    def _setup_headers(self):
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def _api_request(self, method, path, **kwargs):
        url = f"{self.api_base}{path}"
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            if response.status_code >= 400:
                try:
                    error = response.json()
                except ValueError:
                    text = response.text
                    if '<html' in text.lower():
                        raise Exception({'error': f"Server Error {response.status_code}"})
                    error = {'error': text}
                raise Exception(error)
            if response.status_code == 204:
                return {}
            return response.json()
        except RequestException as exc:
            raise Exception(str(exc))
    
    def _refresh_token(self):
        try:
            resp = self.session.post(
                f"{self.api_base}/token/refresh/",
                json={"refresh": self.refresh_token},
                timeout=10
            )
            if resp.status_code == 200:
                self.token = resp.json()["access"]
                return True
        except Exception:
            pass
        return False

    def _fmt_error(self, exc):
        message = exc.args[0] if exc.args else str(exc)
        if isinstance(message, dict):
            if 'detail' in message:
                return message['detail']
            if 'error' in message:
                return message['error']
            return str(message)
        return str(message)

    def _check_admin_setup(self):
        try:
            data = self._api_request('get', '/accounts/staff/setup/')
            self.admin_exists = bool(data.get('admin_exists', True))
        except Exception:
            self.admin_exists = True

    def _fetch_current_user(self):
        if not self.token:
            return
        try:
            self.user = self._api_request('get', '/accounts/staff/me/')
        except Exception:
            self.user = None

    def _api_list(self, path):
        data = self._api_request('get', path)
        return normalize_response(data)

    def _load_orders(self):
        try:
            self.orders = self._api_list('/orders/orders/')
        except Exception:
            self.orders = []

    def _load_menu_items(self):
        try:
            self.menu_items = self._api_list('/menu/items/')
        except Exception:
            self.menu_items = []

    def _load_inventory_items(self):
        try:
            self.inventory_items = self._api_list('/inventory/items/')
        except Exception:
            self.inventory_items = []

    def _load_suppliers(self):
        try:
            self.suppliers = self._api_list('/inventory/suppliers/')
        except Exception:
            self.suppliers = []

    def _load_purchase_orders(self):
        try:
            self.purchase_orders = self._api_list('/inventory/purchase-orders/')
        except Exception:
            self.purchase_orders = []
    
    def _load_store(self):
        try:
            self.store = self._api_list('/store/store-items/')
        except Exception:
            self.store = []
    
    def _load_store(self):
        try:
            self.store = self._api_list('/store/store-transaction/')
        except Exception:
            self.store = []

    def _load_notifications(self):
        try:
            self.notifications = self._api_list('/notifications/')
        except Exception:
            self.notifications = []

    def _load_staff(self):
        try:
            data = self._api_request('get', '/accounts/staff/')
            if isinstance(data, dict) and 'results' in data:
                data = data['results']
            self.staff_list = []
            for item in data:
                self.staff_list.append({
                    'staffId': item.get('staffId') or str(item.get('id')),
                    'name': item.get('staffName') or item.get('email'),
                    'role': item.get('role'),
                    'role_display': item.get('role_display') or item.get('role'),
                    'email': item.get('email'),
                    'status': 'Active' if item.get('is_active', True) else 'Inactive',
                    'orders': item.get('orders', 0)
                })
            return
        except Exception:
            self.staff_list = []

    # ── BUG FIX #1: Analytics ─────────────────────────────────────────────
    # OLD: returned None silently → page showed "Loading..." then returned
    # NEW: returns the data dict OR raises so the page can show a real error
    def _load_analytics(self):
        return self._api_request('get', '/analytics/dashboard/')


    def _show_intro(self):
        for w in self.winfo_children():
            w.destroy()
        t = self.t

        outer = tk.Frame(self, bg=t["bg"])
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=t["card"], bd=0,
                         highlightthickness=1, highlightbackground=t["border"])
        card.place(relx=0.5, rely=0.5, anchor="center", width=520, height=520)

        tk.Label(card, text="🍽️", font=("Arial", 48), bg=t["card"], fg=t["accent"]).pack(pady=(36, 8))
        tk.Label(card, text="Welcome to Roe's POS Admin", font=("Georgia", 24, "bold"),
                 bg=t["card"], fg=t["text"]).pack(pady=(0, 12))
        tk.Label(card,
                 text="A clean admin console for staff, inventory, orders, analytics and notifications.",
                 font=("Arial", 11), bg=t["card"], fg=t["text_sub"], wraplength=440, justify="center").pack(padx=30)

        if not self.admin_exists:
            tk.Label(card,
                     text="No administrator account exists yet. Create the first admin account now.",
                     font=("Arial", 11, "bold"), bg=t["card"], fg=t["accent"], wraplength=420,
                     justify="center").pack(pady=(18, 24), padx=20)
            self._btn(card, "Create Administrator Account", self._show_setup, color=t["accent"]).pack(fill="x", padx=70, pady=(0, 12))
            self._btn(card, "Already have an account? Sign In", self._show_login, color=t["surface"]).pack(fill="x", padx=70)
        else:
            tk.Label(card,
                     text="Sign in with your administrator email and PIN to continue.",
                     font=("Arial", 11), bg=t["card"], fg=t["text_sub"], wraplength=420,
                     justify="center").pack(pady=(18, 24), padx=20)
            self._btn(card, "Sign In", self._show_login, color=t["accent"]).pack(fill="x", padx=110, pady=(0, 12))
            self._btn(card, "Create admin account", self._show_setup, color=t["surface"]).pack(fill="x", padx=110)

    # ── Theme helpers ──────────────────────────────────────────────────────
    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.t = DARK if self.is_dark else LIGHT
        self.configure(bg=self.t["bg"])
        self._build_main()

    # ── Login ──────────────────────────────────────────────────────────────
    def _show_login(self):
        for w in self.winfo_children():
            w.destroy()
        t = self.t

        outer = tk.Frame(self, bg=t["bg"])
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=t["card"], bd=0, highlightthickness=1, highlightbackground=t["border"])
        card.place(relx=0.5, rely=0.5, anchor="center", width=420, height=500)

        tk.Label(card, text="🍽️", font=("Arial", 36), bg=t["card"], fg=t["accent"]).pack(pady=(40, 4))
        tk.Label(card, text="Roe's POS", font=("Georgia", 22, "bold"), bg=t["card"], fg=t["text"]).pack()
        tk.Label(card, text="Administrator Portal", font=("Arial", 11), bg=t["card"], fg=t["text_sub"]).pack(pady=(2, 28))

        tk.Label(card, text="EMAIL ADDRESS", font=("Arial", 9, "bold"), bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=40)
        email_var = tk.StringVar(value="admin@roes.com")
        email_entry = tk.Entry(card, textvariable=email_var, font=("Arial", 12),
                               bg=t["input_bg"], fg=t["text"], insertbackground=t["text"],
                               relief="flat", bd=0, highlightthickness=1, highlightbackground=t["border"])
        email_entry.pack(fill="x", padx=40, ipady=8, pady=(4, 16))

        tk.Label(card, text="PASSWORD", font=("Arial", 9, "bold"), bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=40)
        pass_var = tk.StringVar()
        pass_frame = tk.Frame(card, bg=t["input_bg"],
                              highlightthickness=1, highlightbackground=t["border"])
        pass_frame.pack(fill="x", padx=40, pady=(4, 16))
        pass_entry = tk.Entry(pass_frame, textvariable=pass_var, show="●", font=("Arial", 12),
                              bg=t["input_bg"], fg=t["text"], insertbackground=t["text"],
                              relief="flat", bd=0, highlightthickness=0)
        pass_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(8, 0))

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

        err_label = tk.Label(card, text="", font=("Arial", 10), bg=t["card"], fg=t["red"])
        err_label.pack(pady=(0, 4))

        def do_login(event=None):
            if not email_var.get() or not pass_var.get():
                err_label.config(text="⚠  Please fill in all fields.", fg=t["red"])
                return

            btn.config(state="disabled", text="Signing in…")
            err_label.config(text="")

            def login_request():
                try:
                    data = self._api_request('post', '/accounts/staff/login/', json={
                        'email': email_var.get().strip(),
                        'pin': pass_var.get().strip()
                    })
                    self.token = data.get('access')
                    self.refresh_token = data.get('refresh')
                    self.user = data.get('user')
                    if not self.user:
                        self._fetch_current_user()
                    self.after(0, self._build_main)
                except Exception as exc:
                    message = exc.args[0]
                    if isinstance(message, dict):
                        message = message.get('error') or message.get('detail') or str(message)
                    self.after(0, lambda: err_label.config(text=f"⚠  {message}", fg=t["red"]))
                    self.after(0, lambda: btn.config(state="normal", text="Sign In  →"))

            threading.Thread(target=login_request, daemon=True).start()

        pass_entry.bind("<Return>", do_login)

        btn = tk.Button(card, text="Sign In  →", font=("Arial", 13, "bold"),
                        bg=t["accent"], fg="#000000",
                        activebackground="#e08c00", activeforeground="#000000",
                        relief="flat", bd=0, cursor="hand2", command=do_login)
        btn.pack(fill="x", padx=40, ipady=12, pady=(4, 0))
        def _btn_enter(e): btn.config(bg="#e08c00")
        def _btn_leave(e): btn.config(bg=t["accent"])
        btn.bind("<Enter>", _btn_enter)
        btn.bind("<Leave>", _btn_leave)

        div_frame = tk.Frame(card, bg=t["card"])
        div_frame.pack(fill="x", padx=40, pady=(16, 0))
        tk.Frame(div_frame, bg=t["border"], height=1).pack(fill="x", side="left", expand=True, pady=8)
        tk.Label(div_frame, text="  or  ", font=("Arial", 9), bg=t["card"], fg=t["text_muted"]).pack(side="left")
        tk.Frame(div_frame, bg=t["border"], height=1).pack(fill="x", side="left", expand=True, pady=8)

        self._btn(card, "Create Admin Account", self._show_setup, color=t["surface"]).pack(fill="x", padx=40, pady=(8, 0))

        tk.Label(card, text="🔒  Restricted access · Roe's Restaurant Management System",
                 font=("Arial", 9), bg=t["card"], fg=t["text_muted"]).pack(pady=(18, 0))

        email_entry.focus()

    def _show_setup(self):
        for w in self.winfo_children():
            w.destroy()
        t = self.t

        outer = tk.Frame(self, bg=t["bg"])
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=t["card"], bd=0,
                         highlightthickness=1, highlightbackground=t["border"])
        card.place(relx=0.5, rely=0.5, anchor="center", width=520, height=660)

        tk.Label(card, text="Create Administrator", font=("Georgia", 24, "bold"),
                 bg=t["card"], fg=t["text"]).pack(pady=(32, 8))
        tk.Label(card, text="Set up the first administrator account for Roe's POS.",
                 font=("Arial", 11), bg=t["card"], fg=t["text_sub"], wraplength=440, justify="center").pack(padx=30)

        fields = [
            ("Full Name", ""),
            ("Email Address", ""),
            ("6-digit PIN", ""),
            ("Confirm PIN", ""),
            ("Phone (optional)", ""),
        ]
        vars_ = []
        for label, default in fields:
            tk.Label(card, text=label.upper(), font=("Arial", 8, "bold"),
                     bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=40)
            v = tk.StringVar(value=default)
            is_pin = "PIN" in label

            row_frame = tk.Frame(card, bg=t["input_bg"],
                                 highlightthickness=1, highlightbackground=t["border"])
            row_frame.pack(fill="x", padx=40, pady=(4, 12))

            e = tk.Entry(row_frame, textvariable=v, show="●" if is_pin else "", font=("Arial", 12),
                         bg=t["input_bg"], fg=t["text"], insertbackground=t["text"],
                         relief="flat", bd=0, highlightthickness=0)
            e.pack(side="left", fill="x", expand=True, ipady=8, padx=(8, 0))

            if is_pin:
                sv = tk.BooleanVar(value=False)
                eye = tk.Button(row_frame, text="👁", font=("Arial", 13),
                                bg=t["input_bg"], fg=t["text_sub"],
                                relief="flat", bd=0, cursor="hand2",
                                activebackground=t["input_bg"], activeforeground=t["accent"])
                eye.config(command=lambda e=e, sv=sv, b=eye: (
                    sv.set(not sv.get()),
                    e.config(show="" if sv.get() else "●"),
                    b.config(text="🙈" if sv.get() else "👁")
                ))
                eye.pack(side="right", padx=6)

            vars_.append(v)

        err_label = tk.Label(card, text="", font=("Arial", 10), bg=t["card"], fg=t["red"])
        err_label.pack()

        def create_admin():
            if not vars_[0].get().strip() or not vars_[1].get().strip() or not vars_[2].get().strip() or not vars_[3].get().strip():
                err_label.config(text="Please fill in every required field.")
                return
            if vars_[2].get().strip() != vars_[3].get().strip():
                err_label.config(text="PINs do not match.")
                return

            btn = create_btn
            btn.config(state="disabled")
            err_label.config(text="Creating administrator…", fg=t["text_sub"])

            def request_setup():
                try:
                    payload = {
                        'staffName': vars_[0].get().strip(),
                        'email': vars_[1].get().strip(),
                        'pin': vars_[2].get().strip(),
                        'confirm_pin': vars_[3].get().strip(),
                        'phone': vars_[4].get().strip(),
                    }
                    data = self._api_request('post', '/accounts/staff/setup/', json=payload)
                    self.token = data.get('access')
                    self.user = data.get('user')
                    self.admin_exists = True
                    self.after(0, self._build_main)
                except Exception as exc:
                    message = exc.args[0]
                    if isinstance(message, dict):
                        message = message.get('error') or message.get('detail') or str(message)
                    self.after(0, lambda: err_label.config(text=str(message), fg=t["red"]))
                    self.after(0, lambda: btn.config(state="normal"))

            threading.Thread(target=request_setup, daemon=True).start()

        create_btn = tk.Button(card, text="Create Administrator  →", font=("Arial", 12, "bold"),
                               bg=t["accent"], fg="#000000",
                               activebackground="#e08c00", activeforeground="#000000",
                               relief="flat", bd=0, cursor="hand2", command=create_admin)
        create_btn.pack(fill="x", padx=40, ipady=12, pady=(8, 0))
        def _cb_enter(e): create_btn.config(bg="#e08c00")
        def _cb_leave(e): create_btn.config(bg=t["accent"])
        create_btn.bind("<Enter>", _cb_enter)
        create_btn.bind("<Leave>", _cb_leave)
        self._btn(card, "← Back to Sign In", self._show_login, color=t["surface"]).pack(fill="x", padx=40, pady=(10, 0))

    # ── Main shell ─────────────────────────────────────────────────────────
    def _build_main(self):
        for w in self.winfo_children():
            w.destroy()
        t = self.t
        self.configure(bg=t["bg"])

        self._load_notifications()

        self._nav = tk.Frame(self, bg=t["nav_bg"], height=56)
        self._nav.pack(fill="x", side="top")
        self._nav.pack_propagate(False)
        self._build_nav()

        self._content = tk.Frame(self, bg=t["bg"])
        self._content.pack(fill="both", expand=True)

        self.show_page("dashboard")

    def _build_nav(self):
        t = self.t
        for w in self._nav.winfo_children():
            w.destroy()

        logo = tk.Label(self._nav, text="🍽️  Roe's POS", font=("Georgia", 14, "bold"),
                        bg=t["nav_bg"], fg=t["accent"], cursor="arrow")
        logo.pack(side="left", padx=(20, 30))

        pages = [
            ("dashboard",     "Dashboard"),
            ("orders",        "Orders"),
            ("menu",          "Menu"),
            ("inventory",     "Inventory"),
            ("analytics",     "Analytics"),
            ("staff",         "Staff"),
            ("notifications", "Notifications"),
        ]
        self._nav_btns = {}
        for key, label in pages:
            btn = tk.Button(self._nav, text=label, font=("Arial", 10, "bold"),
                            bg=t["nav_bg"], fg=t["text_sub"],
                            activebackground=t["surface"], relief="flat", bd=0,
                            cursor="hand2", padx=12, pady=4,
                            command=lambda k=key: self.show_page(k))
            btn.pack(side="left", padx=2)
            self._nav_btns[key] = btn

        right = tk.Frame(self._nav, bg=t["nav_bg"])
        right.pack(side="right", padx=16)

        theme_btn = tk.Button(right, text="☀ Light" if self.is_dark else "☽ Dark",
                              font=("Arial", 9, "bold"),
                              bg=t["tag_bg"], fg=t["text_sub"],
                              relief="flat", bd=0, cursor="hand2", padx=10, pady=4,
                              command=self.toggle_theme)
        theme_btn.pack(side="right", padx=4)

        unread_count = sum(1 for n in self.notifications if not n.get("read", False))
        notif_text = f"🔔 ({unread_count})" if unread_count else "🔔"
        notif_btn = tk.Button(right, text=notif_text, font=("Arial", 10),
                              bg=t["tag_bg"], fg=t["red"] if unread_count else t["text_sub"],
                              relief="flat", bd=0, cursor="hand2", padx=8, pady=4,
                              command=lambda: self.show_page("notifications"))
        notif_btn.pack(side="right", padx=4)

        user_label = "👤 Admin"
        if self.user:
            uname = self.user.get('staffName') or self.user.get('email')
            role = self.user.get('role_display') or self.user.get('role', '')
            user_label = f"👤 {uname} — {role}" if role else f"👤 {uname}"

        tk.Label(right, text=user_label, font=("Arial", 10, "bold"),
                 bg=t["tag_bg"], fg=t["text"], padx=10, pady=4).pack(side="right", padx=4)

        logout_btn = tk.Button(right, text="Logout", font=("Arial", 9),
                               bg=t["nav_bg"], fg=t["text_muted"],
                               relief="flat", bd=0, cursor="hand2", padx=8,
                               command=self._show_login)
        logout_btn.pack(side="right")

    def _highlight_nav(self, key):
        t = self.t
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.config(bg=t["accent_dim"] if self.is_dark else t["accent_dim"],
                           fg=t["accent"], font=("Arial", 10, "bold"))
            else:
                btn.config(bg=t["nav_bg"], fg=t["text_sub"], font=("Arial", 10, "bold"))

    def show_page(self, key):
        self.active_page = key
        self._highlight_nav(key)
        for w in self._content.winfo_children():
            w.destroy()
        if key == "notifications":
            # ── BUG FIX #2: also load orders so pending orders list is populated
            self._load_notifications()
            self._load_orders()
        elif key == "orders":
            self._load_orders()
        elif key == "dashboard":
            self._load_orders()
            self._load_notifications()
        elif key == 'store':
            self._load_store()
            self._page_store()
        pages = {
            "dashboard":     self._page_dashboard,
            "orders":        self._page_orders,
            "menu":          self._page_menu,
            "inventory":     self._page_inventory,
            "store":         self._page_store,
            "analytics":     self._page_analytics,
            "staff":         self._page_staff,
            "notifications": self._page_notifications,
        }
        pages.get(key, self._page_dashboard)()

    # ── Shared widgets ──────────────────────────────────────────────────────
    def _scrollable(self, parent):
        t = self.t
        canvas = tk.Canvas(parent, bg=t["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=t["bg"])
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        def safe_scroll(e):
            try:
                canvas.yview_scroll(-1*(e.delta//120), "units")
            except:
                pass
        canvas.bind("<MouseWheel>", safe_scroll)
        frame.bind("<MouseWheel>", safe_scroll)
        return frame

    def _card(self, parent, title=None, **grid_kw):
        t = self.t
        outer = tk.Frame(parent, bg=t["card"], bd=0,
                         highlightthickness=1, highlightbackground=t["border"])
        outer.grid(**grid_kw, padx=8, pady=8, sticky="nsew")
        if title:
            tk.Label(outer, text=title, font=("Arial", 12, "bold"),
                     bg=t["card"], fg=t["text"]).pack(anchor="w", padx=16, pady=(14, 6))
        return outer

    def _metric_card(self, parent, label, value, sub="", sub_color=None, col=0, row=0):
        t = self.t
        f = tk.Frame(parent, bg=t["card"], bd=0,
                     highlightthickness=1, highlightbackground=t["border"])
        f.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        tk.Label(f, text=label.upper(), font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(f, text=value, font=("Arial", 22, "bold"),
                 bg=t["card"], fg=t["text"]).pack(anchor="w", padx=16)
        if sub:
            tk.Label(f, text=sub, font=("Arial", 10),
                     bg=t["card"], fg=sub_color or t["text_sub"]).pack(anchor="w", padx=16, pady=(2, 14))

    def _make_tree(self, parent, cols, col_widths=None):
        t = self.t
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                         background=t["card"],
                         foreground=t["text"],
                         fieldbackground=t["card"],
                         rowheight=34,
                         borderwidth=0,
                         font=("Arial", 10))
        style.configure("Custom.Treeview.Heading",
                         background=t["surface"],
                         foreground=t["text_sub"],
                         relief="flat",
                         font=("Arial", 9, "bold"))
        style.map("Custom.Treeview",
                  background=[("selected", t["accent_dim"])],
                  foreground=[("selected", t["accent"])])

        tree = ttk.Treeview(parent, columns=cols, show="headings",
                            style="Custom.Treeview", selectmode="browse")
        for i, col in enumerate(cols):
            w = col_widths[i] if col_widths else 120
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="w")

        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True, padx=(0, 0))
        sb.pack(side="right", fill="y")
        return tree

    def _status_tag(self, tree):
        t = self.t
        for s, (_, color) in STATUS_COLORS.items():
            tree.tag_configure(s, foreground=color)

    def _btn(self, parent, text, cmd, color=None, small=False, danger=False):
        t = self.t
        if danger:
            bg = t["red"]
            fg = "#ffffff"
            hover_bg = "#c0392b"
        elif color and color not in (t["accent"], None):
            bg = color
            fg = t["text"]
            hover_bg = t["border"]
        else:
            bg = color or t["accent"]
            fg = "#000000"
            hover_bg = "#e08c00"

        b = tk.Button(parent, text=text, font=("Arial", 9 if small else 10, "bold"),
                      bg=bg, fg=fg, activebackground=hover_bg, activeforeground=fg,
                      relief="flat", bd=0, cursor="hand2",
                      padx=10 if small else 16, pady=4 if small else 8,
                      command=cmd)

        def on_enter(e, _bg=hover_bg): b.config(bg=_bg)
        def on_leave(e, _bg=bg): b.config(bg=_bg)
        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)
        return b

    def _field(self, parent, label, var, secret=False, padx=32):
        t = self.t
        tk.Label(parent, text=label.upper(), font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=padx)
        row = tk.Frame(parent, bg=t["input_bg"],
                       highlightthickness=1, highlightbackground=t["border"])
        row.pack(fill="x", padx=padx, pady=(3, 10))
        e = tk.Entry(row, textvariable=var, show="●" if secret else "",
                     font=("Arial", 11), bg=t["input_bg"], fg=t["text"],
                     insertbackground=t["text"], relief="flat", bd=0, highlightthickness=0)
        e.pack(side="left", fill="x", expand=True, ipady=8, padx=(8, 0))
        if secret:
            sv = tk.BooleanVar(value=False)
            eye = tk.Button(row, text="👁", font=("Arial", 12),
                            bg=t["input_bg"], fg=t["text_sub"],
                            relief="flat", bd=0, cursor="hand2",
                            activebackground=t["input_bg"], activeforeground=t["accent"])
            eye.config(command=lambda: (
                sv.set(not sv.get()),
                e.config(show="" if sv.get() else "●"),
                eye.config(text="🙈" if sv.get() else "👁")
            ))
            eye.pack(side="right", padx=6)
        return e

    def _form_save_btn(self, parent, text, cmd, padx=32):
        t = self.t
        b = tk.Button(parent, text=text, font=("Arial", 11, "bold"),
                      bg=t["accent"], fg="#000000",
                      activebackground="#e08c00", activeforeground="#000000",
                      relief="flat", bd=0, cursor="hand2", command=cmd)
        b.pack(fill="x", padx=padx, ipady=10, pady=(6, 16))
        b.bind("<Enter>", lambda e: b.config(bg="#e08c00"))
        b.bind("<Leave>", lambda e: b.config(bg=t["accent"]))
        return b

    def _search_bar(self, parent, var, placeholder="Search…"):
        t = self.t
        f = tk.Frame(parent, bg=t["surface"], highlightthickness=1, highlightbackground=t["border"])
        f.pack(side="left")
        tk.Label(f, text="⌕", font=("Arial", 13), bg=t["surface"], fg=t["text_sub"]).pack(side="left", padx=(8, 2))
        e = tk.Entry(f, textvariable=var, font=("Arial", 11),
                     bg=t["surface"], fg=t["text"], insertbackground=t["text"],
                     relief="flat", bd=0, width=22)
        e.pack(side="left", ipady=7, padx=(0, 8))
        return e

    # ──────────────────────────────────────────────────────────────────────
    # PAGES
    # ──────────────────────────────────────────────────────────────────────

    # ── DASHBOARD ─────────────────────────────────────────────────────────
    def _page_dashboard(self):
        t = self.t
        root = tk.Frame(self._content, bg=t["bg"])
        root.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(root, text="Dashboard", font=("Georgia", 18, "bold"),
                 bg=t["bg"], fg=t["text"]).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
        now = datetime.now().strftime("%A, %d %B %Y  •  %H:%M")
        tk.Label(root, text=now, font=("Arial", 10),
                 bg=t["bg"], fg=t["text_sub"]).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 16))

        self._load_orders()
        self._load_menu_items()
        self._load_inventory_items()
        self._load_notifications()

        def safe_num(v):
            try:
                return float(v) if v is not None else 0
            except (TypeError, ValueError):
                return 0

        low = [i for i in self.inventory_items if 0 < safe_num(i.get("quantityInStock", i.get("qty", 0))) <= safe_num(i.get("lowStockThreshold", i.get("threshold", 0)))]
        out = [i for i in self.inventory_items if safe_num(i.get("quantityInStock", i.get("qty", 0))) == 0]
        if low or out:
            af = tk.Frame(root, bg=t["bg"])
            af.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 12))
            for item in out:
                a = tk.Label(af, text=f"⚠  {item.get('name', 'Item')} — Out of Stock",
                             font=("Arial", 10, "bold"), bg="#fee2e2", fg=t["red"],
                             padx=12, pady=6)
                a.pack(side="left", padx=(0, 8))
            for item in low:
                a = tk.Label(af, text=f"▲  {item.get('name', 'Item')} — Low Stock ({item.get('quantityInStock', item.get('qty', 0))} {item.get('unit', '')})",
                             font=("Arial", 10, "bold"), bg="#fef3c7", fg=t["accent"],
                             padx=12, pady=6)
                a.pack(side="left", padx=(0, 8))

        pending_orders = [o for o in self.orders if o.get("status") in ["Pending", "Confirmed", "Preparing"]][:3]
        if pending_orders:
            nf = tk.Frame(root, bg=t["bg"])
            nf.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(12, 0))
            tk.Label(nf, text="📋 Pending Orders", font=("Arial", 11, "bold"),
                     bg=t["bg"], fg=t["text"]).pack(anchor="w", pady=(0, 8))
            for order in pending_orders:
                n_frame = tk.Frame(nf, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
                n_frame.pack(fill="x", pady=(0, 4))
                order_number = order.get("orderNumber") or order.get("orderId") or order.get("id", "—")
                amount = self._get_order_total(order)
                table = order.get("tableNumber") or order.get("table") or "—"
                tk.Label(n_frame, text=f"Order {order_number} - ₦{fmt(amount)}", font=("Arial", 10, "bold"),
                         bg=t["card"], fg=t["accent"]).pack(anchor="w", padx=12, pady=(8, 2))
                tk.Label(n_frame, text=f"Table: {table} • {order.get('status', 'Unknown')}", font=("Arial", 9),
                         bg=t["card"], fg=t["text_sub"], wraplength=600, justify="left").pack(anchor="w", padx=12, pady=(0, 8))

        for c in range(4):
            root.columnconfigure(c, weight=1)
        revenue = sum(self.safe_float(self._get_order_total(o)) for o in self.orders)
        orders_today = len(self.orders)
        available = sum(1 for m in self.menu_items if m.get("available", m.get("isAvailable", False)))
        total_menu = len(self.menu_items)
        metrics = [
            ("Today's Revenue", fmt(revenue), f"Based on {orders_today} orders", t["green"]),
            ("Orders Today",    str(orders_today),                     "",              t["blue"]),
            ("Menu Items",      f"{available} / {total_menu}",       "Available",      t["accent"]),
            ("Stock Alerts",    str(len(low) + len(out)),              f"{len(out)} out of stock", t["red"]),
        ]
        for col, (lbl, val, sub, sc) in enumerate(metrics):
            self._metric_card(root, lbl, val, sub, sc, col=col, row=3)

        chart_card = self._card(root, "Orders by Status", row=4, column=0, columnspan=3)
        chart_card.grid(padx=(8, 4), pady=8, sticky="nsew")
        root.rowconfigure(4, weight=1)
        status_counts = {}
        for o in self.orders:
            status = o.get("status", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        chart_labels = list(status_counts.keys()) or ["No Data"]
        chart_values = list(status_counts.values()) or [1]
        self._draw_bar_chart(chart_card, chart_labels, chart_values, t["accent"], value_formatter=lambda v: str(int(v)))

        orders_card = self._card(root, "Recent Orders", row=4, column=3, columnspan=1)
        orders_card.grid(padx=(4, 8), pady=8, sticky="nsew")
        for o in self.orders[:6]:
            row_f = tk.Frame(orders_card, bg=t["card"])
            row_f.pack(fill="x", padx=12, pady=3)
            order_number = o.get("orderNumber") or o.get("orderId") or o.get("id", "—")
            table = o.get("tableNumber") or o.get("table") or "—"
            amount = o.get("totalAmount") or o.get("amount") or 0
            status = o.get("status", "Unknown")
            _, sc = STATUS_COLORS.get(status, ("", t["text_sub"]))
            tk.Label(row_f, text=order_number, font=("Courier", 9, "bold"),
                     bg=t["card"], fg=t["accent"], width=12, anchor="w").pack(side="left")
            tk.Label(row_f, text=table, font=("Arial", 9),
                     bg=t["card"], fg=t["text_sub"], width=10, anchor="w").pack(side="left")
            tk.Label(row_f, text=fmt(amount), font=("Arial", 9, "bold"),
                     bg=t["card"], fg=t["text"], width=10, anchor="e").pack(side="left")
            tk.Label(row_f, text=status, font=("Arial", 9, "bold"),
                     bg=t["card"], fg=sc).pack(side="right")

    def _draw_bar_chart(self, parent, labels, values, bar_color, value_formatter=None):
        t = self.t
        canvas = tk.Canvas(parent, bg=t["card"], highlightthickness=0, height=200)
        canvas.pack(fill="x", padx=16, pady=(4, 16))

        if value_formatter is None:
            value_formatter = lambda v: f"₦{int(v/1000)}k"

        def draw(event=None):
            canvas.delete("all")
            W = canvas.winfo_width() or 600
            H = canvas.winfo_height() or 200
            pad_l, pad_r, pad_b, pad_t = 44, 16, 36, 12
            chart_w = W - pad_l - pad_r
            chart_h = H - pad_b - pad_t
            max_val = max(values) or 1
            n = len(values)
            bar_w = chart_w / n * 0.55
            gap = chart_w / n

            for i in range(5):
                y = pad_t + chart_h - (i / 4) * chart_h
                canvas.create_line(pad_l, y, W - pad_r, y, fill=t["border"], dash=(3, 4))
                label = value_formatter(int(max_val * i / 4))
                canvas.create_text(pad_l - 4, y, text=label, anchor="e",
                                   fill=t["text_sub"], font=("Arial", 8))

            for i, (lbl, val) in enumerate(zip(labels, values)):
                x = pad_l + i * gap + gap / 2
                bh = (val / max_val) * chart_h
                x0, y0 = x - bar_w / 2, pad_t + chart_h - bh
                x1, y1 = x + bar_w / 2, pad_t + chart_h

                canvas.create_rectangle(x0 + 2, y0 + 2, x1 + 2, y1, fill=t["border"], outline="")
                canvas.create_rectangle(x0, y0, x1, y1, fill=bar_color, outline="")
                canvas.create_text(x, y0 - 6, text=value_formatter(val),
                                   fill=t["text_sub"], font=("Arial", 7))
                canvas.create_text(x, H - 8, text=lbl, fill=t["text_sub"], font=("Arial", 9))

        canvas.bind("<Configure>", draw)
        canvas.after(100, draw)

    # ── ORDERS ────────────────────────────────────────────────────────────
    def _page_orders(self):
        t = self.t
        root = tk.Frame(self._content, bg=t["bg"])
        root.pack(fill="both", expand=True, padx=24, pady=20)

        self._load_orders()

        hf = tk.Frame(root, bg=t["bg"])
        hf.pack(fill="x", pady=(0, 16))
        tk.Label(hf, text="Orders", font=("Georgia", 18, "bold"),
                 bg=t["bg"], fg=t["text"]).pack(side="left")

        bf = tk.Frame(root, bg=t["bg"])
        bf.pack(fill="x", pady=(0, 12))
        search_var = tk.StringVar()
        self._search_bar(bf, search_var, "Search order ID, table…")

        filter_var = tk.StringVar(value="All")
        for status in ["All", "Pending", "Confirmed", "Preparing", "Ready", "Served", "Completed", "Cancelled"]:
            rb = tk.Radiobutton(bf, text=status, variable=filter_var,
                                value=status, font=("Arial", 10),
                                bg=t["bg"], fg=t["text_sub"],
                                selectcolor=t["accent_dim"],
                                activebackground=t["bg"],
                                cursor="hand2",
                                command=lambda: self._refresh_orders(tree, filter_var, search_var))
            rb.pack(side="left", padx=(12, 0))

        tf = tk.Frame(root, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        tf.pack(fill="both", expand=True)

        cols = ("Order ID", "Table", "Items", "Amount", "Status", "Staff", "Time")
        widths = [110, 90, 60, 110, 100, 130, 80]
        tree = self._make_tree(tf, cols, widths)
        self._status_tag(tree)
        self._refresh_orders(tree, filter_var, search_var)

        search_var.trace_add("write", lambda *_: self._refresh_orders(tree, filter_var, search_var))

        def on_select(event):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0])["values"]
            oid = vals[0]
            order = next((o for o in self.orders if (o.get("orderNumber") or o.get("orderId") or o.get("id")) == oid), None)
            if order:
                self._order_detail(order)

        tree.bind("<Double-1>", on_select)

    def _refresh_orders(self, tree, filter_var, search_var):
        tree.delete(*tree.get_children())
        f = filter_var.get()
        q = search_var.get().lower()
        for o in self.orders:
            status = o.get("status", "Unknown")
            order_number = o.get("orderNumber") or o.get("orderId") or o.get("id", "")
            table = o.get("tableNumber") or o.get("table") or ""
            if f != "All" and status != f:
                continue
            if q and q not in str(order_number).lower() and q not in str(table).lower():
                continue
            tag = status
            amount = self._get_order_total(o)
            items_list = o.get("items", [])
            items_count = len(items_list) if items_list else 0
            staff = o.get("takenByName") or o.get("staffName") or o.get("staff") or ""
            time_str = o.get("createdAt", "")
            if time_str:
                try:
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    time = dt.strftime("%H:%M")
                except:
                    time = time_str[:5] if len(time_str) > 5 else time_str
            else:
                time = ""
            tree.insert("", "end", values=(
                order_number, table, items_count,
                fmt(amount), status, staff, time
            ), tags=(tag,))

    def _order_detail(self, order):
        t = self.t
        order_id = order.get("orderNumber") or order.get("orderId") or order.get("id", "—")
        table = order.get("tableNumber") or order.get("table") or "—"
        items_list = order.get("items", [])
        amount = self._get_order_total(order)
        status = order.get("status", "Unknown")
        taken_by = order.get("takenByName") or "—"
        served_by = order.get("servedByName") or "—"
        time = order.get("createdAt", "")
        if time:
            try:
                dt = datetime.fromisoformat(time.replace('Z', '+00:00'))
                time_display = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_display = time
        else:
            time_display = "—"

        win = tk.Toplevel(self)
        win.title(f"Order — {order_id}")
        win.geometry("500x400")
        win.configure(bg=t["card"])
        win.resizable(True, True)

        tk.Label(win, text=order_id, font=("Courier", 16, "bold"),
                 bg=t["card"], fg=t["accent"]).pack(pady=(24, 4))
        tk.Label(win, text=f"Table: {table}", font=("Arial", 12),
                 bg=t["card"], fg=t["text_sub"]).pack()

        items_frame = tk.Frame(win, bg=t["card"])
        items_frame.pack(fill="x", padx=32, pady=(16, 8))
        tk.Label(items_frame, text="Items:", font=("Arial", 11, "bold"),
                 bg=t["card"], fg=t["text"]).pack(anchor="w")

        if items_list:
            for item in items_list:
                item_name = item.get("menuItemName") or item.get("name") or "Unknown Item"
                quantity = item.get("quantity", 1)
                item_text = f"• {quantity}x {item_name}"
                tk.Label(items_frame, text=item_text, font=("Arial", 10),
                         bg=t["card"], fg=t["text_sub"]).pack(anchor="w", pady=2)
        else:
            tk.Label(items_frame, text="No items found", font=("Arial", 10),
                     bg=t["card"], fg=t["text_muted"]).pack(anchor="w")

        info_frame = tk.Frame(win, bg=t["card"])
        info_frame.pack(fill="x", padx=32, pady=(8, 16))

        info = [
            ("Total Amount", fmt(amount)),
            ("Status", status),
            ("Taken By", taken_by),
            ("Served By", served_by),
            ("Created", time_display),
        ]
        for k, v in info:
            row = tk.Frame(info_frame, bg=t["card"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{k}:", font=("Arial", 10), bg=t["card"],
                     fg=t["text_sub"], width=12, anchor="w").pack(side="left")
            color_entry = STATUS_COLORS.get(v, ("", t["text"]))
            sc = color_entry[1] if len(color_entry) > 1 else t["text"]
            fc = sc if k == "Status" else t["text"]
            tk.Label(row, text=v, font=("Arial", 10, "bold"),
                     bg=t["card"], fg=fc).pack(side="left")

        # ── Status changer ───────────────────────────────────────────────────
        current_status = order.get("status", "")
        changeable = ["Pending", "Confirmed", "Preparing", "Ready", "Served"]
        all_statuses = ["Pending", "Confirmed", "Preparing", "Ready", "Served", "Completed", "Cancelled"]

        status_frame = tk.Frame(win, bg=t["card"])
        status_frame.pack(fill="x", padx=32, pady=(0, 8))
        tk.Label(status_frame, text="Change Status:", font=("Arial", 10, "bold"),
                bg=t["card"], fg=t["text_sub"]).pack(side="left")

        status_var = tk.StringVar(value=current_status)
        status_cb = ttk.Combobox(status_frame, textvariable=status_var,
                             values=all_statuses, state="readonly",
                             font=("Arial", 10), width=14)
        status_cb.pack(side="left", padx=(10, 0))

        def update_status():
            new_status = status_var.get()
            if new_status == current_status:
                messagebox.showinfo("No Change", "Status is already set to that value.", parent=win)
                return
            order_id_val = order.get("orderId") or order.get("id")
            try:
                self._api_request('patch', f'/orders/orders/{order_id_val}/', json={"status": new_status})
                messagebox.showinfo("Updated", f"Order status changed to {new_status}.", parent=win)
                self._load_orders()
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Failed", self._fmt_error(exc), parent=win)

        tk.Button(status_frame, text="Update", font=("Arial", 10, "bold"),
                bg=t["green"], fg="#fff", relief="flat", padx=12, pady=4,
                cursor="hand2", command=update_status).pack(side="left", padx=(10, 0))

        tk.Button(win, text="Close", font=("Arial", 10, "bold"),
                bg=t["accent"], fg="#000", relief="flat", padx=20, pady=8,
                cursor="hand2", command=win.destroy).pack(pady=16)
        

    def _tree_context_menu(self, tree, items_list, id_field, edit_fn, delete_fn):
        t = self.t
        menu = tk.Menu(self, tearoff=0, bg=t["card"], fg=t["text"],
                       activebackground=t["accent_dim"], activeforeground=t["accent"],
                       font=("Arial", 10))

        def on_right_click(event):
            row = tree.identify_row(event.y)
            if not row:
                return
            tree.selection_set(row)
            iid = row

            item = next((x for x in items_list
                     if str(x.get(id_field) or x.get("id") or x.get("name")) == iid), None)
            if not item:
                return

            menu.delete(0, "end")
            menu.add_command(label="✏️  Edit", command=lambda: edit_fn(item))
            menu.add_separator()
            menu.add_command(label="🗑️  Delete", foreground="red",
                         command=lambda: delete_fn(item))
            menu.tk_popup(event.x_root, event.y_root)

        tree.bind("<Button-3>", on_right_click)
        tree.bind("<Button-2>", on_right_click)

    # ── MENU ─────────────────────────────────────────────────────────────
    def _page_menu(self):
        t = self.t
        root = tk.Frame(self._content, bg=t["bg"])
        root.pack(fill="both", expand=True, padx=24, pady=20)

        self._load_menu_items()

        hf = tk.Frame(root, bg=t["bg"])
        hf.pack(fill="x", pady=(0, 16))
        tk.Label(hf, text="Menu", font=("Georgia", 18, "bold"),
             bg=t["bg"], fg=t["text"]).pack(side="left")
        self._btn(hf, "+ Add Item", lambda: self._menu_form()).pack(side="right")

        tf = tk.Frame(root, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        tf.pack(fill="both", expand=True)

        cols = ("Name", "Type", "Price", "Available", "Actions")
        widths = [200, 120, 100, 100, 160]
        tree = self._make_tree(tf, cols, widths)
        self._status_tag(tree)

        for item in self.menu_items:
            name = item.get("name") or "Untitled"
            item_type = item.get("itemType", "")
            price = item.get("price") or 0
            available = item.get("isAvailable", False)
            avail_text = "✔ Available" if available else "✘ Unavailable"
            tag = "Active" if available else "Inactive"
            tree.insert("", "end",
                        iid=str(item.get("menuItemId") or name),
                        values=(name, item_type, fmt(price), avail_text, "Edit | Toggle"),
                        tags=(tag,))

        tree.bind("<Double-1>", lambda e: self._edit_menu_item(tree))
        self._tree_context_menu(
            tree,
            items_list=self.menu_items,
            id_field="menuItemId",
            edit_fn=lambda item: self._menu_form(item),
            delete_fn=lambda item: self._delete_menu_item(item),
        )

    def _menu_form(self, item=None):
        t = self.t
        win = tk.Toplevel(self)
        win.title("Add Menu Item" if not item else "Edit Menu Item")
        win.geometry("480x520")
        win.configure(bg=t["card"])
        win.resizable(True, True)

        hdr = tk.Frame(win, bg=t["green"], height=6)
        hdr.pack(fill="x")
        icon = "🍽️" if not item else "✏️"
        tk.Label(win, text=f"{icon}  {'Add' if not item else 'Edit'} Menu Item",
                 font=("Georgia", 15, "bold"), bg=t["card"], fg=t["text"]).pack(pady=(20, 4), padx=32, anchor="w")
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=32, pady=(0, 14))

        name_var = tk.StringVar(value=item["name"] if item else "")
        self._field(win, "Item Name", name_var)

        tk.Label(win, text="ITEM TYPE", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        item_type_options = ["Food", "Drink", "Combo", "Other"]
        current_item_type = item.get('itemType', 'Food') if item else "Food"
        item_type_var = tk.StringVar(value=current_item_type)
        type_frame = tk.Frame(win, bg=t["input_bg"], highlightthickness=1, highlightbackground=t["border"])
        type_frame.pack(fill="x", padx=32, pady=(3, 10))
        type_cb = ttk.Combobox(type_frame, textvariable=item_type_var,
                               values=item_type_options, state="readonly", font=("Arial", 11))
        type_cb.pack(fill="x", padx=4, ipady=6)

        price_var = tk.StringVar(value=str(item["price"]) if item else "")
        self._field(win, "Price (₦)", price_var)

        self._load_inventory_items()
        inventory_display_map = {}
        ingredient_values = ["None"]
        for inv in self.inventory_items:
            display = f"{inv.get('name', 'Unknown')} ({inv.get('quantityInStock', inv.get('qty', 0))} {inv.get('unit', '')})"
            inventory_display_map[display] = str(inv.get('inventoryItemId') or inv.get('id'))
            ingredient_values.append(display)

        selected_ingredient = "None"
        ingredient_qty = ""
        if item:
            item_detail = item
            item_id = str(item.get("menuItemId") or item.get("id") or "")
            if item_id:
                try:
                    item_detail = self._api_request('get', f'/menu/items/{item_id}/')
                except Exception:
                    pass
            first_ingredient = (item_detail.get('ingredients') or [None])[0]
            if first_ingredient:
                inv_id = str(first_ingredient.get('inventoryItem') or first_ingredient.get('inventoryItemId') or "")
                for label, value in inventory_display_map.items():
                    if value == inv_id:
                        selected_ingredient = label
                        break
                ingredient_qty = str(first_ingredient.get('quantityUsed', ''))

        tk.Label(win, text="INGREDIENT LINK", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        ingredient_var = tk.StringVar(value=selected_ingredient)
        ingredient_frame = tk.Frame(win, bg=t["input_bg"], highlightthickness=1, highlightbackground=t["border"])
        ingredient_frame.pack(fill="x", padx=32, pady=(3, 10))
        ingredient_cb = ttk.Combobox(ingredient_frame, textvariable=ingredient_var,
                                     values=ingredient_values, state="readonly", font=("Arial", 11))
        ingredient_cb.pack(fill="x", padx=4, ipady=6)

        quantity_var = tk.StringVar(value=ingredient_qty)
        self._field(win, "Ingredient Qty Used", quantity_var)

        def save():
            selected_item_type = item_type_var.get().strip()
            if not selected_item_type:
                messagebox.showwarning("Validation", "Please select an item type.", parent=win)
                return
            if ingredient_var.get() != "None" and not quantity_var.get().strip():
                messagebox.showwarning("Validation", "Please enter ingredient quantity used.", parent=win)
                return
            payload = {
                'name': name_var.get().strip(),
                'itemType': selected_item_type,
                'price': float(price_var.get() or 0),
            }
            if ingredient_var.get() != "None":
                ingredient_id = inventory_display_map.get(ingredient_var.get())
                payload['ingredients'] = [{
                    'inventoryItem': ingredient_id,
                    'quantityUsed': float(quantity_var.get() or 0),
                }]
            else:
                payload['ingredients'] = []
            if not payload['name']:
                messagebox.showwarning("Validation", "Name is required.", parent=win)
                return
            try:
                if item:
                    self._api_request('patch', f'/menu/items/{item["menuItemId"] or item.get("id")}/', json=payload)
                else:
                    self._api_request('post', '/menu/items/', json=payload)
                messagebox.showinfo("Saved", f"Menu item '{payload['name']}' saved.", parent=win)
                win.destroy()
                self.show_page('menu')
            except Exception as exc:
                message = exc.args[0] if exc.args else str(exc)
                if isinstance(message, dict):
                    message = message.get('error') or message.get('detail') or str(message)
                messagebox.showerror("Save Failed", str(message), parent=win)

        self._form_save_btn(win, "💾  Save Item", save)

    def _edit_menu_item(self, tree):
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        item = next((m for m in self.menu_items if str(m.get("menuItemId") or m.get("id") or m.get("name")) == iid), None)
        if item:
            self._menu_form(item)

    def _delete_menu_item(self, item):
        name = item.get("name", "this item")
        if not messagebox.askyesno("Delete", f"Delete '{name}' from the menu?"):
            return
        iid = str(item.get("menuItemId") or item.get("id"))
        ok, err = self._api_delete(f"/menu/items/{iid}/")
        if ok:
            messagebox.showinfo("Deleted", f"'{name}' deleted.")
            self.show_page("menu")
        else:
            messagebox.showerror("Error", err or "Could not delete item.")

    def _delete_inventory_item(self, item):
        name = item.get("name", "this item")
        if not messagebox.askyesno("Delete", f"Delete '{name}' from inventory?"):
            return
        iid = str(item.get("inventoryItemId") or item.get("id"))
        ok, err = self._api_delete(f"/inventory/items/{iid}/")
        if ok:
            messagebox.showinfo("Deleted", f"'{name}' deleted.")
            self.show_page("inventory")
        else:
            messagebox.showerror("Error", err or "Could not delete item.")

    def _api_delete(self, endpoint):
        try:
            r = self.session.delete(f"{self.api_base}{endpoint}")
            if r.status_code in (200, 204):
                return True, None
            try:
                return False, r.json().get("detail", "Delete failed.")
            except Exception:
                return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)

    def _inventory_item_form(self, item=None):
        t = self.t
        win = tk.Toplevel(self)
        win.title("Add Inventory Item" if not item else "Edit Inventory Item")
        win.geometry("480x600")
        win.configure(bg=t["card"])
        win.resizable(True, True)

        hdr = tk.Frame(win, bg=t["accent"], height=6)
        hdr.pack(fill="x")
        icon = "📦" if not item else "✏️"
        tk.Label(win, text=f"{icon}  {'Add' if not item else 'Edit'} Inventory Item",
                 font=("Georgia", 15, "bold"), bg=t["card"], fg=t["text"]).pack(pady=(20, 4), padx=32, anchor="w")
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=32, pady=(0, 16))

        inventory_categories = [
            "Ingredients", "Sauces", "Beverages", "Utensils", "Packaging",
            "Cleaning Supplies", "Spices & Seasonings", "Oils & Fats",
            "Bakery Items", "Frozen Foods",
        ]
        name_var = tk.StringVar(value=item["name"] if item else "")
        self._field(win, "Item Name", name_var)

        tk.Label(win, text="CATEGORY", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        category_var = tk.StringVar(value=item.get("category", "") if item else "Ingredients")
        cat_frame = tk.Frame(win, bg=t["input_bg"], highlightthickness=1, highlightbackground=t["border"])
        cat_frame.pack(fill="x", padx=32, pady=(3, 10))
        category_cb = ttk.Combobox(cat_frame, textvariable=category_var,
                                   values=inventory_categories, state="readonly", font=("Arial", 11))
        category_cb.pack(fill="x", padx=4, ipady=6)

        cost_var = tk.StringVar(value=str(item.get("costPerUnit", item.get("cost", item.get("unitCost", 0)))) if item else "0")
        self._field(win, "Unit Cost (₦)", cost_var)

        tk.Label(win, text="UNIT", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        _unit_values = ["kg", "g", "L", "ml", "units", "bags", "cartons", "bottles", "packs"]
        _current_unit = item.get("unit", "units") if item else "units"
        unit_var = tk.StringVar(value=_current_unit)
        unit_frame = tk.Frame(win, bg=t["input_bg"], highlightthickness=1, highlightbackground=t["border"])
        unit_frame.pack(fill="x", padx=32, pady=(3, 10))
        unit_cb = ttk.Combobox(unit_frame, textvariable=unit_var,
                               values=_unit_values, state="readonly", font=("Arial", 11))
        unit_cb.pack(fill="x", padx=4, ipady=6)

        qty_var = tk.StringVar(value=str(item.get("quantityInStock", 0)) if item else "0")
        self._field(win, "Qty in Stock", qty_var)

        threshold_var = tk.StringVar(value=str(item.get("lowStockThreshold", 5)) if item else "5")
        self._field(win, "Low Stock Threshold", threshold_var)

        def save():
            try:
                name = name_var.get().strip()
                unit = unit_var.get().strip()
                if not name:
                    messagebox.showwarning("Validation", "Item name is required.", parent=win)
                    return
                if not unit:
                    messagebox.showwarning("Validation", "Please select a unit.", parent=win)
                    return
                payload = {
                    'name':              name,
                    'category':          category_var.get().strip(),
                    'costPerUnit':       float(cost_var.get() or 0),
                    'unit':              unit,
                    'quantityInStock':   float(qty_var.get() or 0),
                    'lowStockThreshold': float(threshold_var.get() or 0),
                }
                item_id = item.get("inventoryItemId") or item.get("id") if item else None
                if item and item_id:
                    self._api_request('patch', f'/inventory/items/{item_id}/', json=payload)
                else:
                    self._api_request('post', '/inventory/items/', json=payload)
                messagebox.showinfo("Saved", f"Item '{name}' saved.", parent=win)
                win.destroy()
                self.show_page('inventory')
            except Exception as exc:
                messagebox.showerror("Save Failed", self._fmt_error(exc), parent=win)

        self._form_save_btn(win, "💾  Save Item", save)

    def _supplier_form(self, supplier=None):
        t = self.t
        win = tk.Toplevel(self)
        win.title("Add Supplier" if not supplier else "Edit Supplier")
        win.geometry("520x550")
        win.configure(bg=t["card"])
        win.resizable(True, True)

        hdr = tk.Frame(win, bg=t["blue"], height=6)
        hdr.pack(fill="x")
        icon = "🏭" if not supplier else "✏️"
        tk.Label(win, text=f"{icon}  {'Add' if not supplier else 'Edit'} Supplier",
                 font=("Georgia", 15, "bold"), bg=t["card"], fg=t["text"]).pack(pady=(20, 4), padx=32, anchor="w")
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=32, pady=(0, 14))

        fields = [
            ("Supplier Name",  supplier["name"] if supplier else ""),
            ("Contact Person", supplier.get("contactName", "") if supplier else ""),
            ("Phone",          supplier.get("phone", "") if supplier else ""),
            ("Email",          supplier.get("email", "") if supplier else ""),
            ("Address",        supplier.get("address", "") if supplier else "")
        ]
        vars_ = []
        for label, default in fields:
            v = tk.StringVar(value=default)
            self._field(win, label, v)
            vars_.append(v)

        active_var = tk.BooleanVar(value=supplier.get("isActive", True) if supplier else True)
        chk_frame = tk.Frame(win, bg=t["card"])
        chk_frame.pack(anchor="w", padx=32, pady=(0, 12))
        tk.Label(chk_frame, text="STATUS", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w")
        ttk.Checkbutton(chk_frame, text="Active supplier", variable=active_var).pack(anchor="w", pady=(4, 0))

        def save():
            try:
                payload = {
                    'name':        vars_[0].get().strip(),
                    'contactName': vars_[1].get().strip(),
                    'phone':       vars_[2].get().strip(),
                    'email':       vars_[3].get().strip(),
                    'address':     vars_[4].get().strip(),
                    'isActive':    active_var.get(),
                }
                if not payload['name']:
                    messagebox.showwarning("Validation", "Supplier name is required.", parent=win)
                    return
                supplier_id = supplier.get("supplierId") or supplier.get("id") if supplier else None
                if supplier and supplier_id:
                    self._api_request('patch', f'/inventory/suppliers/{supplier_id}/', json=payload)
                else:
                    self._api_request('post', '/inventory/suppliers/', json=payload)
                messagebox.showinfo("Saved", f"Supplier '{payload['name']}' saved.", parent=win)
                win.destroy()
                self.show_page('inventory')
            except Exception as exc:
                messagebox.showerror("Save Failed", self._fmt_error(exc), parent=win)

        self._form_save_btn(win, "💾  Save Supplier", save)

    def _po_form(self, po=None):
        t = self.t
        win = tk.Toplevel(self)
        win.title("New Purchase Order" if not po else "Edit Purchase Order")
        win.geometry("480x540")
        win.configure(bg=t["card"])
        win.resizable(True, True)

        hdr = tk.Frame(win, bg=t["purple"], height=6)
        hdr.pack(fill="x")
        tk.Label(win, text=f"{'🛒  New' if not po else '✏️  Edit'} Purchase Order",
                 font=("Georgia", 15, "bold"), bg=t["card"], fg=t["text"]).pack(pady=(20, 4), padx=32, anchor="w")
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=32, pady=(0, 14))

        tk.Label(win, text="SUPPLIER", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        supplier_var = tk.StringVar(value=po.get("supplierName", "") if po else "")
        supplier_names = [s.get("name", "") for s in self.suppliers]
        sup_frame = tk.Frame(win, bg=t["input_bg"], highlightthickness=1, highlightbackground=t["border"])
        sup_frame.pack(fill="x", padx=32, pady=(3, 10))
        supplier_cb = ttk.Combobox(sup_frame, textvariable=supplier_var,
                               values=supplier_names, state="readonly", font=("Arial", 11))
        supplier_cb.pack(fill="x", padx=4, ipady=6)

        date_var = tk.StringVar(value=po.get("deliveryDate", "") if po else "")
        self._field(win, "Expected Delivery Date  (YYYY-MM-DD)", date_var)

        items_var = tk.StringVar(value=po.get("items", "") if po else "")
        self._field(win, "Items  (comma-separated IDs or names)", items_var)

        qty_var = tk.StringVar(value=po.get("quantities", "") if po else "")
        self._field(win, "Quantities  (e.g. 10, 20, 30)", qty_var)

        notes_var = tk.StringVar(value=po.get("notes", "") if po else "")
        self._field(win, "Notes", notes_var)

        def save():
            try:
                payload = {
                    'supplier':     supplier_var.get(),
                    'deliveryDate': date_var.get().strip(),
                    'items':        items_var.get().strip(),
                    'notes':        notes_var.get().strip(),
                }
                if not payload['supplier']:
                    messagebox.showwarning("Validation", "Please select a supplier.", parent=win)
                    return
                if po:
                    self._api_request('patch', f'/inventory/purchase-orders/{po.get("id")}/', json=payload)
                else:
                    self._api_request('post', '/inventory/purchase-orders/', json=payload)
                messagebox.showinfo("Saved", "Purchase order created.", parent=win)
                win.destroy()
                self.show_page('inventory')
            except Exception as exc:
                message = exc.args[0] if exc.args else str(exc)
                if isinstance(message, dict):
                    message = message.get('error') or message.get('detail') or str(message)
                messagebox.showerror("Save Failed", str(message), parent=win)

        self._form_save_btn(win, "💾  Save Order", save)

    # ── INVENTORY ─────────────────────────────────────────────────────────
    def _page_inventory(self):
        t = self.t
        root = tk.Frame(self._content, bg=t["bg"])
        root.pack(fill="both", expand=True, padx=24, pady=20)

        self._load_inventory_items()
        self._load_suppliers()
        self._load_purchase_orders()

        tk.Label(root, text="Inventory", font=("Georgia", 18, "bold"),
             bg=t["bg"], fg=t["text"]).pack(anchor="w", pady=(0, 4))

        nb = ttk.Notebook(root)
        style = ttk.Style()
        style.configure("TNotebook", background=t["bg"])
        style.configure("TNotebook.Tab", font=("Arial", 10, "bold"),
                    background=t["surface"], foreground=t["text_sub"], padding=(14, 6))
        style.map("TNotebook.Tab",
              background=[("selected", t["accent_dim"])],
              foreground=[("selected", t["accent"])])
        nb.pack(fill="both", expand=True, pady=10)

        tab1 = tk.Frame(nb, bg=t["bg"])
        nb.add(tab1, text="  Stock Items  ")
        self._inventory_stock_tab(tab1)

        tab2 = tk.Frame(nb, bg=t["bg"])
        nb.add(tab2, text="  Suppliers  ")
        self._inventory_suppliers_tab(tab2)

        tab3 = tk.Frame(nb, bg=t["bg"])
        nb.add(tab3, text="  Purchase Orders  ")
        self._inventory_po_tab(tab3)

    def _inventory_stock_tab(self, parent):
        t = self.t
        hf = tk.Frame(parent, bg=t["bg"])
        hf.pack(fill="x", pady=(12, 8), padx=4)
        search_var = tk.StringVar()
        self._search_bar(hf, search_var)
        self._btn(hf, "+ Add Item", lambda: self._inventory_item_form()).pack(side="right")

        tf = tk.Frame(parent, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        tf.pack(fill="both", expand=True, padx=4)

        cols = ("Name", "Qty", "Unit", "Threshold", "Status", "Cost/Unit", "Supplier")
        widths = [180, 80, 70, 90, 100, 110, 150]
        tree = self._make_tree(tf, cols, widths)
        self._status_tag(tree)

        def load(q=""):
            tree.delete(*tree.get_children())
            for item in self.inventory_items:
                name = item.get("name") or "Item"
                if q and q not in name.lower():
                    continue
                s = stock_status(item)
                qty       = item.get("quantityInStock", 0)
                unit      = item.get("unit", "")
                threshold = item.get("lowStockThreshold", 0)
                cost      = item.get("costPerUnit", 0)
                supplier  = item.get("supplierName") or ""
                iid       = str(item.get("inventoryItemId") or item.get("id") or name)
                tree.insert("", "end", iid=iid, values=(
                    name, qty, unit, threshold, s, fmt(cost), supplier
                ), tags=(s,))

        load()
        search_var.trace_add("write", lambda *_: load(search_var.get().lower()))

        def on_edit_item(event):
            sel = tree.selection()
            if not sel:
                return
            iid = sel[0]
            item = next((x for x in self.inventory_items
                     if str(x.get("inventoryItemId") or x.get("id") or x.get("name")) == iid), None)
            if item:
                self._inventory_item_form(item)
                load()

        tree.bind("<Double-1>", on_edit_item)
        self._tree_context_menu(
            tree,
            items_list=self.inventory_items,
            id_field="inventoryItemId",
            edit_fn=lambda item: self._inventory_item_form(item),
            delete_fn=lambda item: self._delete_inventory_item(item),
        )

    def _inventory_suppliers_tab(self, parent):
        t = self.t
        hf = tk.Frame(parent, bg=t["bg"])
        hf.pack(fill="x", pady=(12, 8), padx=4)
        tk.Label(hf, text=f"{len(self.suppliers)} suppliers", font=("Arial", 10),
                 bg=t["bg"], fg=t["text_sub"]).pack(side="left")
        self._btn(hf, "+ Add Supplier", lambda: self._supplier_form()).pack(side="right")

        tf = tk.Frame(parent, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        tf.pack(fill="both", expand=True, padx=4)

        cols = ("Name", "Contact", "Phone", "Email", "Status")
        widths = [160, 140, 120, 200, 90]
        tree = self._make_tree(tf, cols, widths)
        self._status_tag(tree)

        for s in self.suppliers:
            active = s.get("isActive", s.get("active", False))
            tree.insert("", "end", iid=str(s.get("supplierId") or s.get("id", "")), values=(
                s.get("name", "Supplier"),
                s.get("contactName", s.get("contact", "")),
                s.get("phone", ""),
                s.get("email", ""),
                "Active" if active else "Inactive"
            ), tags=("Active" if active else "Inactive",))

        def on_edit_supplier(event):
            sel = tree.selection()
            if not sel:
                return
            iid = sel[0]
            s = next((x for x in self.suppliers if str(x.get("supplierId") or x.get("id", "")) == iid), None)
            if s:
                self._supplier_form(s)

        tree.bind("<Double-1>", on_edit_supplier)

    def _inventory_po_tab(self, parent):
        t = self.t
        hf = tk.Frame(parent, bg=t["bg"])
        hf.pack(fill="x", pady=(12, 8), padx=4)
        self._btn(hf, "+ New Purchase Order", lambda: self._po_form()).pack(side="right")
        
        tf = tk.Frame(parent, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        tf.pack(fill="both", expand=True, padx=4)

        cols = ("PO Number", "Supplier", "Items", "Total", "Status", "Date")
        widths = [110, 160, 70, 110, 100, 100]
        tree = self._make_tree(tf, cols, widths)
        self._status_tag(tree)

        for po in self.purchase_orders:
            tree.insert("", "end", iid=str(po.get("purchaseOrderId") or po.get("id") or ""),
                        values=(
                            po.get("poNumber") or po.get("id") or "PO-?",
                            po.get("supplier") or po.get("supplierName") or "",
                            po.get("items") or po.get("itemCount") or 0,
                            fmt(po.get("totalCost") or po.get("total") or po.get("amount") or 0),
                            po.get("status") or "Unknown",
                            po.get("createdAt") or po.get("date") or ""
                            ), tags=(po.get("status") or "Unknown",))
            # ── Mark as Received button ───────────────────────────────────────────
        btn_frame = tk.Frame(parent, bg=t["bg"])
        btn_frame.pack(fill="x", pady=(8, 4), padx=4)

        def mark_received():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("No Selection", "Please select a Purchase Order first.")
                return
            iid = sel[0]
            po = next((p for p in self.purchase_orders
                       if str(p.get("purchaseOrderId") or p.get("id") or "") == iid), None)
            if not po:
                messagebox.showerror("Error", "Could not find selected Purchase Order.")
                return
            if po.get("status") == "Received":
                messagebox.showinfo("Already Received", f"{po.get('poNumber')} has already been received.")
                return
            if not messagebox.askyesno("Confirm",
                                       f"Mark {po.get('poNumber')} as Received?\n\nThis will update inventory stock levels."):
                return
            
            po_id = po.get("purchaseOrderId") or po.get("id")
            try:
                self._api_request('post', f'/inventory/purchase-orders/{po_id}/receive/')
                messagebox.showinfo("Success", f"{po.get('poNumber')} marked as Received. Inventory updated.")
                self.show_page('inventory')
            except Exception as exc:
                messagebox.showerror("Failed", self._fmt_error(exc))
                
        receive_btn = tk.Button(
            btn_frame,
            text="✅  Mark Selected as Received",
            font=("Arial", 10, "bold"),
            bg=t["green"], fg="#ffffff",
            activebackground="#059669", activeforeground="#ffffff",
            relief="flat", bd=0, cursor="hand2", padx=14, pady=6,
            command=mark_received
            )
        receive_btn.pack(side="left")
        tk.Label(btn_frame, text="Select a Purchase Order above, then click to receive and update stock.",
            font=("Arial", 9), bg=t["bg"], fg=t["text_muted"]).pack(side="left", padx=12)

    # ─────────────────────────────────────────────────────────────────────────────
#  Store Page — drop these methods into the RoesAdmin class
#  Requires: tkinter, ttk, messagebox (already imported in the main app)
#  API endpoints consumed:
#    GET    /store/items/             → list all items
#    GET    /store/items/low_stock/   → low-stock items
#    POST   /store/items/             → create item
#    PATCH  /store/items/{id}/        → update item
#    DELETE /store/items/{id}/        → delete item
#    POST   /store/items/{id}/transact/ → log a movement
#    GET    /store/transactions/      → full transaction log
# ─────────────────────────────────────────────────────────────────────────────

# ── Data loading ──────────────────────────────────────────────────────────────

    def _load_store_items(self):
        try:
            self.store_items = self._api_list('/store/items/')
        except Exception:
            self.store_items = []

    def _load_store_transactions(self):
        try:
            self.store_transactions = self._api_list('/store/transactions/')
        except Exception:
            self.store_transactions = []

# ── Main Store page ───────────────────────────────────────────────────────────

    def _page_store(self):
        t = self.t
        root = tk.Frame(self._content, bg=t["bg"])
        root.pack(fill="both", expand=True, padx=24, pady=20)

        # ── initialise store data lists if not present ────────────────────
        if not hasattr(self, 'store_items'):
            self.store_items = []
        if not hasattr(self, 'store_transactions'):
            self.store_transactions = []

        self._load_store_items()
        self._load_store_transactions()

        # ── header row ────────────────────────────────────────────────────
        hf = tk.Frame(root, bg=t["bg"])
        hf.pack(fill="x", pady=(0, 14))
        tk.Label(hf, text="Store", font=("Georgia", 18, "bold"),
                 bg=t["bg"], fg=t["text"]).pack(side="left")

        btn_frame = tk.Frame(hf, bg=t["bg"])
        btn_frame.pack(side="right")
        self._btn(btn_frame, "📋 Transaction Log",
                  lambda: self._store_transactions_window()).pack(side="right", padx=(6, 0))
        self._btn(btn_frame, "⚠ Low Stock",
                  lambda: self._store_low_stock_window()).pack(side="right", padx=(6, 0))
        self._btn(btn_frame, "+ Add Item",
                  lambda: self._store_item_form()).pack(side="right")

        # ── summary cards ─────────────────────────────────────────────────
        sf = tk.Frame(root, bg=t["bg"])
        sf.pack(fill="x", pady=(0, 16))

        total_items   = len(self.store_items)
        active_items  = sum(1 for i in self.store_items if i.get("isActive", True))
        low_stock_ct  = sum(1 for i in self.store_items if self._store_is_low(i))
        total_txns    = len(self.store_transactions)

        cards = [
            ("📦 Total Items",    str(total_items),  t.get("accent",  "#f59e0b")),
            ("✅ Active",          str(active_items), t.get("green",   "#22c55e")),
            ("⚠ Low Stock",       str(low_stock_ct), t.get("red",     "#ef4444")),
            ("🔄 Transactions",    str(total_txns),   t.get("blue",    "#3b82f6")),
        ]
        for label, value, color in cards:
            card = tk.Frame(sf, bg=t["card"], highlightthickness=1,
                            highlightbackground=t["border"])
            card.pack(side="left", expand=True, fill="x", padx=(0, 10))
            tk.Frame(card, bg=color, height=4).pack(fill="x")
            tk.Label(card, text=value, font=("Georgia", 22, "bold"),
                     bg=t["card"], fg=t["text"]).pack(pady=(10, 0))
            tk.Label(card, text=label, font=("Arial", 9),
                     bg=t["card"], fg=t["text_sub"]).pack(pady=(2, 10))

        # ── filter bar ────────────────────────────────────────────────────
        ff = tk.Frame(root, bg=t["bg"])
        ff.pack(fill="x", pady=(0, 8))

        tk.Label(ff, text="Filter:", font=("Arial", 9),
                 bg=t["bg"], fg=t["text_sub"]).pack(side="left")

        self._store_filter_var = tk.StringVar(value="All")
        for opt in ("All", "Low Stock", "Active", "Inactive"):
            rb = tk.Radiobutton(ff, text=opt, variable=self._store_filter_var,
                                value=opt, font=("Arial", 9),
                                bg=t["bg"], fg=t["text_sub"],
                                selectcolor=t["card"],
                                activebackground=t["bg"],
                                command=lambda: self._refresh_store_tree(tree))
            rb.pack(side="left", padx=6)

        search_var = tk.StringVar()
        search_entry = tk.Entry(ff, textvariable=search_var, font=("Arial", 10),
                                bg=t["input_bg"], fg=t["text"],
                                insertbackground=t["text"],
                                relief="flat", bd=0,
                                highlightthickness=1,
                                highlightbackground=t["border"])
        search_entry.pack(side="right", ipadx=8, ipady=4, padx=(0, 0))
        tk.Label(ff, text="🔍", font=("Arial", 10),
                 bg=t["bg"], fg=t["text_sub"]).pack(side="right", padx=(0, 4))

        search_var.trace_add("write",
            lambda *_: self._refresh_store_tree(tree, search=search_var.get()))

        # ── items table ───────────────────────────────────────────────────
        tf = tk.Frame(root, bg=t["card"], highlightthickness=1,
                      highlightbackground=t["border"])
        tf.pack(fill="both", expand=True)

        cols   = ("Name", "Unit", "Qty", "Threshold", "Default Use", "Status", "Actions")
        widths = [220, 80, 90, 100, 110, 110, 160]
        tree   = self._make_tree(tf, cols, widths)
        self._status_tag(tree)

        # custom tags for low-stock highlight
        tree.tag_configure("LowStock", foreground=t.get("red", "#ef4444"))

        self._store_tree      = tree
        self._store_search_var = search_var
        self._refresh_store_tree(tree)

        tree.bind("<Double-1>", lambda e: self._store_edit_selected(tree))
        self._tree_context_menu(
            tree,
            items_list=self.store_items,
            id_field="id",
            edit_fn=lambda item: self._store_item_form(item),
            delete_fn=lambda item: self._store_delete_item(item),
        )

    # ── helpers ───────────────────────────────────────────────────────────

    def _store_is_low(self, item):
        threshold = float(item.get("lowStockThreshold") or item.get("low_stock_threshold") or 0)
        qty       = float(item.get("currentQuantity") or item.get("current_quantity") or 0)
        return threshold > 0 and qty <= threshold

    def _refresh_store_tree(self, tree, search=""):
        tree.delete(*tree.get_children())
        filt   = getattr(self, "_store_filter_var", None)
        f_val  = filt.get() if filt else "All"
        search = (search or getattr(self, "_store_search_var",
                                     tk.StringVar()).get()).lower().strip()

        for item in self.store_items:
            name      = item.get("name", "Untitled")
            qty       = float(item.get("currentQuantity") or item.get("current_quantity") or 0)
            threshold = float(item.get("lowStockThreshold") or item.get("low_stock_threshold") or 0)
            def_use   = float(item.get("defaultUsageQuantity") or item.get("default_usage_quantity") or 0)
            unit      = item.get("unit", "")
            is_active = item.get("isActive", item.get("is_active", True))
            low       = self._store_is_low(item)

            # apply filter
            if f_val == "Low Stock"  and not low:      continue
            if f_val == "Active"     and not is_active: continue
            if f_val == "Inactive"   and is_active:     continue

            # apply search
            if search and search not in name.lower():
                continue

            status_text = "⚠ Low Stock" if low else ("✔ Active" if is_active else "✘ Inactive")
            tag         = "LowStock" if low else ("Active" if is_active else "Inactive")
            iid         = str(item.get("id") or name)

            tree.insert("", "end", iid=iid,
                        values=(name, unit, qty, threshold, def_use, status_text, "Edit | Transact"),
                        tags=(tag,))

    def _store_edit_selected(self, tree):
        sel = tree.selection()
        if not sel:
            return
        iid  = sel[0]
        item = next(
            (s for s in self.store_items
             if str(s.get("id") or s.get("name")) == iid),
            None
        )
        if item:
            self._store_item_form(item)

# ── Add / Edit item form ──────────────────────────────────────────────────────

    def _store_item_form(self, item=None):
        t = self.t
        win = tk.Toplevel(self)
        win.title("Add Store Item" if not item else "Edit Store Item")
        win.geometry("500x580")
        win.configure(bg=t["card"])
        win.resizable(True, True)

        tk.Frame(win, bg=t.get("purple", "#8b5cf6"), height=6).pack(fill="x")
        icon = "📦" if not item else "✏️"
        tk.Label(win, text=f"{icon}  {'Add' if not item else 'Edit'} Store Item",
                 font=("Georgia", 15, "bold"), bg=t["card"], fg=t["text"]
                 ).pack(pady=(20, 4), padx=32, anchor="w")
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=32, pady=(0, 14))

        # ── Name ──────────────────────────────────────────────────────────
        name_var = tk.StringVar(value=item.get("name", "") if item else "")
        self._field(win, "Item Name", name_var)

        # ── Unit ──────────────────────────────────────────────────────────
        unit_choices = ["kg", "g", "L", "ml", "units", "bags", "cartons",
                        "bottles", "packs", "crates", "pieces"]
        cur_unit = item.get("unit", "units") if item else "units"
        unit_var = tk.StringVar(value=cur_unit)
        tk.Label(win, text="UNIT", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        uf = tk.Frame(win, bg=t["input_bg"], highlightthickness=1,
                      highlightbackground=t["border"])
        uf.pack(fill="x", padx=32, pady=(3, 10))
        ttk.Combobox(uf, textvariable=unit_var, values=unit_choices,
                     state="readonly", font=("Arial", 11)
                     ).pack(fill="x", padx=4, ipady=6)

        # ── Qty / Threshold / Default usage ──────────────────────────────
        qty_var = tk.StringVar(
            value=str(item.get("currentQuantity") or item.get("current_quantity") or 0) if item else "0")
        self._field(win, "Current Quantity", qty_var)

        threshold_var = tk.StringVar(
            value=str(item.get("lowStockThreshold") or item.get("low_stock_threshold") or 0) if item else "0")
        self._field(win, "Low Stock Threshold", threshold_var)

        def_use_var = tk.StringVar(
            value=str(item.get("defaultUsageQuantity") or item.get("default_usage_quantity") or 0) if item else "0")
        self._field(win, "Default Usage Qty", def_use_var)

        # ── Note ──────────────────────────────────────────────────────────
        note_var = tk.StringVar(value=item.get("note", "") if item else "")
        self._field(win, "Note (optional)", note_var)

        # ── Active toggle ─────────────────────────────────────────────────
        active_var = tk.BooleanVar(
            value=item.get("isActive", item.get("is_active", True)) if item else True)
        chk_frame = tk.Frame(win, bg=t["card"])
        chk_frame.pack(anchor="w", padx=32, pady=(0, 12))
        tk.Label(chk_frame, text="STATUS", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w")
        ttk.Checkbutton(chk_frame, text="Active item",
                        variable=active_var).pack(anchor="w", pady=(4, 0))

        # ── Save ─────────────────────────────────────────────────────────
        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Validation", "Item name is required.", parent=win)
                return
            unit = unit_var.get().strip()
            if not unit:
                messagebox.showwarning("Validation", "Please select a unit.", parent=win)
                return
            try:
                payload = {
                    "name":                 name,
                    "unit":                 unit,
                    "currentQuantity":      float(qty_var.get() or 0),
                    "lowStockThreshold":    float(threshold_var.get() or 0),
                    "defaultUsageQuantity": float(def_use_var.get() or 0),
                    "note":                 note_var.get().strip(),
                    "isActive":             active_var.get(),
                }
                item_id = item.get("id") if item else None
                if item and item_id:
                    self._api_request('patch', f'/store/items/{item_id}/', json=payload)
                else:
                    self._api_request('post', '/store/items/', json=payload)
                messagebox.showinfo("Saved", f"'{name}' saved.", parent=win)
                win.destroy()
                self.show_page('store')
            except Exception as exc:
                messagebox.showerror("Save Failed", self._fmt_error(exc), parent=win)

        self._form_save_btn(win, "💾  Save Item", save)

# ── Delete item ───────────────────────────────────────────────────────────────

    def _store_delete_item(self, item):
        name = item.get("name", "this item")
        if not messagebox.askyesno("Delete", f"Delete '{name}' from store?"):
            return
        iid = str(item.get("id", ""))
        ok, err = self._api_delete(f"/store/items/{iid}/")
        if ok:
            messagebox.showinfo("Deleted", f"'{name}' deleted.")
            self.show_page("store")
        else:
            messagebox.showerror("Error", err or "Could not delete item.")

# ── Transact form (stock movement) ────────────────────────────────────────────

    def _store_transact_form(self, item):
        t   = self.t
        win = tk.Toplevel(self)
        win.title(f"Log Movement — {item.get('name', '')}")
        win.geometry("420x400")
        win.configure(bg=t["card"])
        win.resizable(False, False)

        tk.Frame(win, bg=t.get("green", "#22c55e"), height=6).pack(fill="x")
        tk.Label(win,
                 text=f"🔄  Stock Movement",
                 font=("Georgia", 15, "bold"), bg=t["card"], fg=t["text"]
                 ).pack(pady=(20, 2), padx=32, anchor="w")
        tk.Label(win,
                 text=item.get("name", ""),
                 font=("Arial", 11), bg=t["card"], fg=t["text_sub"]
                 ).pack(pady=(0, 4), padx=32, anchor="w")

        cur_qty = float(
            item.get("currentQuantity") or item.get("current_quantity") or 0)
        unit = item.get("unit", "")
        tk.Label(win,
                 text=f"Current stock: {cur_qty} {unit}",
                 font=("Arial", 10, "bold"), bg=t["card"],
                 fg=t.get("accent", "#f59e0b")
                 ).pack(padx=32, anchor="w", pady=(0, 12))

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=32, pady=(0, 14))

        # ── Transaction type ──────────────────────────────────────────────
        tx_types = ["received", "used", "damaged", "adjusted"]
        tx_labels = {
            "received": "➕ Received — adds to stock",
            "used":     "➖ Used — subtracts from stock",
            "damaged":  "💔 Damaged — subtracts from stock",
            "adjusted": "🔧 Adjusted — sets absolute value",
        }
        tk.Label(win, text="TRANSACTION TYPE", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        tx_var = tk.StringVar(value="received")
        txf = tk.Frame(win, bg=t["input_bg"], highlightthickness=1,
                       highlightbackground=t["border"])
        txf.pack(fill="x", padx=32, pady=(3, 10))
        tx_cb = ttk.Combobox(txf, textvariable=tx_var,
                              values=list(tx_labels.values()),
                              state="readonly", font=("Arial", 11))
        tx_cb.pack(fill="x", padx=4, ipady=6)

        # ── Quantity ──────────────────────────────────────────────────────
        qty_var = tk.StringVar()
        self._field(win, f"Quantity ({unit})", qty_var)

        # ── Note ──────────────────────────────────────────────────────────
        note_var = tk.StringVar()
        self._field(win, "Note (optional)", note_var)

        # ── Submit ────────────────────────────────────────────────────────
        def submit():
            raw_label = tx_var.get().strip()
            # map display label back to api value
            tx_type = next(
                (k for k, v in tx_labels.items() if v == raw_label), raw_label)
            try:
                qty = float(qty_var.get() or 0)
            except ValueError:
                messagebox.showwarning("Validation", "Quantity must be a number.", parent=win)
                return
            if qty <= 0:
                messagebox.showwarning("Validation", "Quantity must be greater than 0.", parent=win)
                return
            payload = {
                "transaction_type": tx_type,
                "quantity":         qty,
                "note":             note_var.get().strip(),
            }
            item_id = str(item.get("id", ""))
            try:
                self._api_request('post', f'/store/items/{item_id}/transact/', json=payload)
                messagebox.showinfo("Logged",
                                    f"Movement logged: {tx_type} {qty} {unit}",
                                    parent=win)
                win.destroy()
                self.show_page('store')
            except Exception as exc:
                messagebox.showerror("Failed", self._fmt_error(exc), parent=win)

        self._form_save_btn(win, "✔  Log Movement", submit)

# ── Low-stock popup ───────────────────────────────────────────────────────────

    def _store_low_stock_window(self):
        t   = self.t
        win = tk.Toplevel(self)
        win.title("Low Stock Items")
        win.geometry("620x420")
        win.configure(bg=t["bg"])

        tk.Label(win, text="⚠  Low Stock Items",
                 font=("Georgia", 15, "bold"), bg=t["bg"], fg=t["text"]
                 ).pack(pady=(18, 4), padx=24, anchor="w")
        tk.Label(win,
                 text="Items at or below their low-stock threshold.",
                 font=("Arial", 10), bg=t["bg"], fg=t["text_sub"]
                 ).pack(padx=24, anchor="w", pady=(0, 12))

        tf = tk.Frame(win, bg=t["card"], highlightthickness=1,
                      highlightbackground=t["border"])
        tf.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        cols   = ("Name", "Unit", "Qty", "Threshold")
        widths = [240, 80, 100, 120]
        tree   = self._make_tree(tf, cols, widths)
        tree.tag_configure("Low", foreground=t.get("red", "#ef4444"))

        low_items = [i for i in self.store_items if self._store_is_low(i)]
        if not low_items:
            tree.insert("", "end", values=("No low-stock items 🎉", "", "", ""))
        else:
            for item in low_items:
                qty       = float(item.get("currentQuantity") or item.get("current_quantity") or 0)
                threshold = float(item.get("lowStockThreshold") or item.get("low_stock_threshold") or 0)
                tree.insert("", "end",
                            values=(item.get("name", ""), item.get("unit", ""), qty, threshold),
                            tags=("Low",))

# ── Transaction log popup ─────────────────────────────────────────────────────

    def _store_transactions_window(self):
        t   = self.t
        win = tk.Toplevel(self)
        win.title("Store Transaction Log")
        win.geometry("860x520")
        win.configure(bg=t["bg"])

        hdr = tk.Frame(win, bg=t["bg"])
        hdr.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(hdr, text="📋  Transaction Log",
                 font=("Georgia", 15, "bold"), bg=t["bg"], fg=t["text"]
                 ).pack(side="left")
        self._btn(hdr, "⟳ Refresh",
                  lambda: _reload()).pack(side="right")

        tf = tk.Frame(win, bg=t["card"], highlightthickness=1,
                      highlightbackground=t["border"])
        tf.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        cols   = ("Date / Time", "Item", "Type", "Qty", "Before", "After", "Note", "Recorded By")
        widths = [140, 180, 90, 70, 70, 70, 160, 130]
        tree   = self._make_tree(tf, cols, widths)

        # colour-code transaction types
        tree.tag_configure("received", foreground=t.get("green", "#22c55e"))
        tree.tag_configure("used",     foreground=t.get("accent","#f59e0b"))
        tree.tag_configure("damaged",  foreground=t.get("red",   "#ef4444"))
        tree.tag_configure("adjusted", foreground=t.get("blue",  "#3b82f6"))

        def _populate():
            tree.delete(*tree.get_children())
            for tx in self.store_transactions:
                tx_type   = tx.get("transactionType") or tx.get("transaction_type", "")
                item_name = (tx.get("item") or {}).get("name") if isinstance(tx.get("item"), dict) \
                            else tx.get("itemName", "")
                recorded  = tx.get("recordedBy") or tx.get("recorded_by") or "—"
                if isinstance(recorded, dict):
                    recorded = recorded.get("staffName") or recorded.get("email", "—")
                created   = str(tx.get("createdAt") or tx.get("created_at", ""))[:19].replace("T", " ")

                tree.insert("", "end",
                            values=(
                                created,
                                item_name,
                                tx_type,
                                tx.get("quantity", ""),
                                tx.get("quantityBefore") or tx.get("quantity_before", ""),
                                tx.get("quantityAfter")  or tx.get("quantity_after",  ""),
                                tx.get("note", ""),
                                recorded,
                            ),
                            tags=(tx_type,))

        def _reload():
            self._load_store_transactions()
            _populate()

        _populate()

# ── Wire store into show_page ─────────────────────────────────────────────────
# In your existing show_page method, add this branch:
#
#   elif page == 'store':
#       self._page_store()
#
# And in _build_nav, add ("store", "Store") to the pages list.

    # ── ANALYTICS ─────────────────────────────────────────────────────────
    # ── BUG FIX #1 (continued): Wrap in try/except, show specific error,
    #    load in background thread so UI doesn't freeze
    def _page_analytics(self):
        t = self.t
        root = tk.Frame(self._content, bg=t["bg"])
        root.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(root, text="Analytics", font=("Georgia", 18, "bold"),
                 bg=t["bg"], fg=t["text"]).pack(anchor="w", pady=(0, 16))

        # Placeholder while loading
        status_label = tk.Label(root, text="⏳  Loading analytics…",
                                font=("Arial", 12), bg=t["bg"], fg=t["text_sub"])
        status_label.pack(anchor="w", pady=(20, 0))

        def fetch_and_render():
            try:
                analytics_data = self._load_analytics()
                self.after(0, lambda: _render(analytics_data))
            except Exception as exc:
                # ── Shows the REAL error instead of silent blank screen
                err_msg = self._fmt_error(exc)
                self.after(0, lambda: status_label.config(
                    text=f"⚠  Could not load analytics: {err_msg}",
                    fg=t["red"]
                ))

        def _render(analytics_data):
            status_label.destroy()

            summary              = analytics_data.get('summary', {})
            top_items            = analytics_data.get('top_items', [])
            highest_priced_items = analytics_data.get('highest_priced_items', [])

            weekly_revenue = summary.get('today_revenue', 0)
            total_orders   = summary.get('today_orders', 0)
            avg_order      = summary.get('average_order_value', 0)
            top_item       = top_items[0].get('menuItem__name', '—') if top_items else '—'
            highest_priced = highest_priced_items[0].get('name', '—') if highest_priced_items else '—'

            # Metric cards
            metrics_f = tk.Frame(root, bg=t["bg"])
            metrics_f.pack(fill="x", pady=(0, 16))
            for i in range(4):
                metrics_f.columnconfigure(i, weight=1)

            cards = [
                ("Today's Revenue",  fmt(weekly_revenue), f"{total_orders} orders",  t["green"]),
                ("Total Orders",     str(total_orders),   "Today",                   t["blue"]),
                ("Avg Order Value",  fmt(avg_order),      "Per transaction",          t["accent"]),
                ("Highest Priced",   highest_priced,      "Most expensive item",      t["purple"]),
            ]
            for col, (lbl, val, sub, sc) in enumerate(cards):
                self._metric_card(metrics_f, lbl, val, sub, sc, col=col, row=0)

            # Charts row
            charts_f = tk.Frame(root, bg=t["bg"])
            charts_f.pack(fill="both", expand=True)
            charts_f.columnconfigure(0, weight=3)
            charts_f.columnconfigure(1, weight=2)

            # Hourly revenue chart
            rev_card = tk.Frame(charts_f, bg=t["card"],
                                highlightthickness=1, highlightbackground=t["border"])
            rev_card.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
            tk.Label(rev_card, text="Hourly Revenue", font=("Arial", 11, "bold"),
                     bg=t["card"], fg=t["text"]).pack(anchor="w", padx=16, pady=(14, 4))

            hourly_data = analytics_data.get('hourly_revenue', [])
            if hourly_data:
                hours  = [f"{h['hour']}:00" for h in hourly_data]
                values = [h['revenue'] for h in hourly_data]
                self._draw_bar_chart(rev_card, hours, values, t["accent"], value_formatter=fmt)
            else:
                tk.Label(rev_card, text="No hourly data available", font=("Arial", 10),
                         bg=t["card"], fg=t["text_muted"]).pack(pady=20)

            # Highest priced items panel
            items_card = tk.Frame(charts_f, bg=t["card"],
                                  highlightthickness=1, highlightbackground=t["border"])
            items_card.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")
            tk.Label(items_card, text="Highest Priced Items", font=("Arial", 11, "bold"),
                     bg=t["card"], fg=t["text"]).pack(anchor="w", padx=16, pady=(14, 8))

            if highest_priced_items:
                for itm in highest_priced_items[:5]:
                    row_f = tk.Frame(items_card, bg=t["card"])
                    row_f.pack(fill="x", padx=16, pady=4)
                    name  = itm.get('name', 'Unknown')[:16]
                    price = itm.get('price', 0)
                    tk.Label(row_f, text=name, font=("Arial", 10),
                             bg=t["card"], fg=t["text"], width=16, anchor="w").pack(side="left")
                    tk.Label(row_f, text=fmt(price), font=("Arial", 10, "bold"),
                             bg=t["card"], fg=t["accent"]).pack(side="right")
            else:
                tk.Label(items_card, text="No items found", font=("Arial", 10),
                         bg=t["card"], fg=t["text_muted"]).pack(pady=20)

        threading.Thread(target=fetch_and_render, daemon=True).start()

    # ── STAFF ─────────────────────────────────────────────────────────────
    def _page_staff(self):
        t = self.t
        root = tk.Frame(self._content, bg=t["bg"])
        root.pack(fill="both", expand=True, padx=24, pady=20)

        hf = tk.Frame(root, bg=t["bg"])
        hf.pack(fill="x", pady=(0, 16))
        tk.Label(hf, text="Staff", font=("Georgia", 18, "bold"),
                 bg=t["bg"], fg=t["text"]).pack(side="left")
        self._btn(hf, "+ Add Staff", lambda: self._staff_form()).pack(side="right")

        self._load_staff()

        sf = tk.Frame(root, bg=t["bg"])
        sf.pack(fill="x", pady=(0, 16))
        for i in range(3):
            sf.columnconfigure(i, weight=1)
        active = sum(1 for s in self.staff_list if s["status"] == "Active")
        self._metric_card(sf, "Total Staff",   str(len(self.staff_list)), "", None, col=0)
        self._metric_card(sf, "Active",        str(active),     "", t["green"], col=1)
        self._metric_card(sf, "Inactive",      str(len(self.staff_list) - active), "", t["red"], col=2)

        tf = tk.Frame(root, bg=t["card"], highlightthickness=1, highlightbackground=t["border"])
        tf.pack(fill="both", expand=True)

        cols = ("Name", "Role", "Email", "Status", "Orders Today", "Actions")
        widths = [180, 150, 220, 90, 110, 120]
        tree = self._make_tree(tf, cols, widths)
        self._status_tag(tree)

        for s in self.staff_list:
            tag = s["status"]
            tree.insert("", "end", iid=s["staffId"],
                        values=(s["name"], s["role_display"], s["email"], s["status"], s["orders"], "Edit | Delete | View"),
                        tags=(tag,))

        tree.bind("<Double-1>", lambda e: self._edit_staff(tree))
        tree.bind("<Button-1>", lambda e: self._staff_actions(tree, e))

    def _edit_staff(self, tree):
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        staff = next((s for s in self.staff_list if str(s.get("staffId")) == iid), None)
        if staff:
            self._staff_form(staff)

    def _staff_form(self, staff=None):
        t = self.t
        win = tk.Toplevel(self)
        win.title("Add Staff" if not staff else "Edit Staff")
        win.geometry("460x520" if staff else "460x580")
        win.configure(bg=t["card"])
        win.resizable(True, True)

        hdr = tk.Frame(win, bg=t["blue"], height=6)
        hdr.pack(fill="x")
        icon = "👤  Add" if not staff else "✏️  Edit"
        tk.Label(win, text=f"{icon} Staff Member",
                 font=("Georgia", 15, "bold"), bg=t["card"], fg=t["text"]).pack(pady=(20, 4), padx=32, anchor="w")
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=32, pady=(0, 14))

        if staff:
            fields = [
                ("Full Name", staff["name"], False),
                ("Email", staff["email"], False),
                ("Phone", staff.get("phone", ""), False),
            ]
        else:
            fields = [
                ("Full Name", "", False),
                ("Email", "", False),
                ("6-digit PIN", "", True),
                ("Phone", "", False),
            ]

        vars_ = []
        for label, default, secret in fields:
            v = tk.StringVar(value=default)
            self._field(win, label, v, secret=secret)
            vars_.append(v)

        tk.Label(win, text="ROLE", font=("Arial", 8, "bold"),
                 bg=t["card"], fg=t["text_sub"]).pack(anchor="w", padx=32)
        role_var = tk.StringVar(value=staff["role"] if staff else "Clerk")
        role_frame = tk.Frame(win, bg=t["input_bg"], highlightthickness=1, highlightbackground=t["border"])
        role_frame.pack(fill="x", padx=32, pady=(3, 10))
        role_cb = ttk.Combobox(role_frame, textvariable=role_var,
                               values=["Clerk", "Kitchen", "InventoryManager", "Administrator"],
                               state="readonly", font=("Arial", 11))
        role_cb.pack(fill="x", padx=4, ipady=6)

        if staff:
            tk.Label(win, text="ℹ  To change a staff PIN, use the staff profile page.",
                     font=("Arial", 9), bg=t["card"], fg=t["text_muted"], wraplength=380).pack(padx=32, pady=(4, 8), anchor="w")

        def save():
            payload = {
                'staffName': vars_[0].get().strip(),
                'email': vars_[1].get().strip(),
                'role': role_var.get(),
                'phone': vars_[2].get().strip() if staff else vars_[3].get().strip(),
            }

            if not payload['staffName'] or not payload['email']:
                messagebox.showwarning("Validation", "Full name and email are required.", parent=win)
                return

            if not staff:
                pin = vars_[2].get().strip()
                if not pin or len(pin) != 6 or not pin.isdigit():
                    messagebox.showwarning("Validation", "PIN must be a 6-digit number.", parent=win)
                    return
                payload['pin'] = pin
                payload['confirm_pin'] = pin

            try:
                if staff:
                    self._api_request('patch', f'/accounts/staff/{staff["staffId"]}/', json=payload)
                else:
                    self._api_request('post', '/accounts/staff/', json=payload)
                messagebox.showinfo("Saved", f"Staff '{payload['staffName']}' saved.", parent=win)
                win.destroy()
                self.show_page('staff')
            except Exception as exc:
                message = exc.args[0]
                if isinstance(message, dict):
                    message = message.get('error') or message.get('detail') or str(message)
                messagebox.showerror("Save Failed", str(message), parent=win)

        self._form_save_btn(win, "💾  Save Staff Member", save)

    def _staff_actions(self, tree, event):
        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = tree.identify_column(event.x)
        if col != "#6":
            return
        item = tree.identify_row(event.y)
        if not item:
            return
        staff_id = item
        staff = next((x for x in getattr(self, 'staff_list', []) if x.get('staffId') == staff_id), None)
        if not staff:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Edit Staff", command=lambda: self._edit_staff(tree))
        menu.add_command(label="View Performance", command=lambda: self._view_staff_performance(staff))
        menu.add_separator()
        menu.add_command(label="Delete Staff", command=lambda: self._delete_staff(staff))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _view_staff_performance(self, staff):
        t = self.t
        win = tk.Toplevel(self)
        win.title(f"Performance - {staff['name']}")
        win.geometry("500x520")
        win.configure(bg=t["card"])

        tk.Label(win, text=f"Staff Performance: {staff['name']}",
                font=("Georgia", 16, "bold"), bg=t["card"], fg=t["text"]).pack(pady=(20, 16))

        # ── Fetch live order count for this staff ────────────────────────────
        staff_id = staff.get("staffId")
        completed_orders = []
        total_completed = staff.get("orders", 0)
        try:
            all_orders = self._api_list('/orders/orders/')
            staff_orders = [
                o for o in all_orders
                if (o.get("takenBy") == staff_id or o.get("takenByName") == staff.get("name"))
            ]
            completed_orders = [o for o in staff_orders if o.get("status") == "Completed"]
            total_completed = len(completed_orders)
        except Exception:
            pass

        metrics_frame = tk.Frame(win, bg=t["card"])
        metrics_frame.pack(fill="x", padx=32, pady=(0, 20))

        performance_data = [
            ("Name",             staff.get("name", "N/A")),
            ("Email",            staff.get("email", "N/A")),
            ("Role",             staff.get("role_display") or staff.get("role", "N/A")),
            ("Status",           staff.get("status", "N/A")),
            ("Orders Completed", total_completed),
        ]

        for i, (label, value) in enumerate(performance_data):
            tk.Label(metrics_frame, text=f"{label}:", font=("Arial", 10, "bold"),
                    bg=t["card"], fg=t["text_sub"], anchor="w").grid(row=i, column=0, sticky="w", pady=2)
            tk.Label(metrics_frame, text=str(value), font=("Arial", 10),
                     bg=t["card"], fg=t["text"], anchor="w").grid(row=i, column=1, sticky="w", padx=(20, 0), pady=2)

        # ── 3 Most Recent Orders ─────────────────────────────────────────────
        tk.Label(win, text="3 Most Recent Orders", font=("Arial", 12, "bold"),
                bg=t["card"], fg=t["text"]).pack(anchor="w", padx=32, pady=(8, 6))

        recent = sorted(completed_orders, key=lambda o: o.get("createdAt", ""), reverse=True)[:3]

        if not recent:
            tk.Label(win, text="No completed orders found for this staff.",
                    font=("Arial", 10), bg=t["card"], fg=t["text_sub"],
                    wraplength=420, justify="left").pack(fill="x", padx=32, pady=(0, 12))
        else:
            for o in recent:
                order_num = o.get("orderNumber") or o.get("orderId") or "—"
                table     = o.get("tableNumber") or o.get("table") or "—"
                amount    = self._get_order_total(o)
                time_str  = o.get("createdAt", "")
                try:
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    time_display = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    time_display = time_str[:16] if time_str else "—"

                row = tk.Frame(win, bg=t["surface"],
                           highlightthickness=1, highlightbackground=t["border"])
                row.pack(fill="x", padx=32, pady=3)
                inner = tk.Frame(row, bg=t["surface"])
                inner.pack(fill="x", padx=12, pady=6)
                tk.Label(inner, text=f"Order {order_num}  •  Table {table}",
                     font=("Arial", 10, "bold"), bg=t["surface"], fg=t["text"]).pack(side="left")
                tk.Label(inner, text=fmt(amount), font=("Arial", 10, "bold"),
                     bg=t["surface"], fg=t["green"]).pack(side="right")
                tk.Label(row, text=time_display, font=("Arial", 9),
                     bg=t["surface"], fg=t["text_muted"]).pack(anchor="w", padx=12, pady=(0, 4))

        self._btn(win, "Close", win.destroy).pack(pady=(12, 20), padx=32, fill="x")

    def _mark_all_notifications_read(self):
        try:
            self._api_request('post', '/notifications/mark_all_read/')
            self._load_notifications()
            self._build_nav()          # refresh bell count in nav
            self.show_page('notifications')
        except Exception as exc:
            messagebox.showerror("Error", self._fmt_error(exc))

    def _delete_staff(self, staff):
        if messagebox.askyesno("Confirm Delete",
                              f"Are you sure you want to delete {staff['name']}?\n\nThis action cannot be undone.",
                              icon="warning"):
            try:
                self._api_request('delete', f'/accounts/staff/{staff["staffId"]}/')
                messagebox.showinfo("Deleted", f"Staff '{staff['name']}' has been deleted.")
                self.show_page('staff')
            except Exception as exc:
                message = exc.args[0]
                if isinstance(message, dict):
                    message = message.get('error') or message.get('detail') or str(message)
                messagebox.showerror("Delete Failed", str(message))

    # ── NOTIFICATIONS ──────────────────────────────────────────────────────
    # ── BUG FIX #2: Load orders first so pending list is populated
    # ── BUG FIX #3: Add "Mark all as read" button — it was never rendered
    # ── BUG FIX #5: amount now safely extracted and always shown via fmt()
    def _page_notifications(self):
        t = self.t
        root = tk.Frame(self._content, bg=t["bg"])
        root.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Header row ────────────────────────────────────────────────────
        hf = tk.Frame(root, bg=t["bg"])
        hf.pack(fill="x", pady=(0, 12))
        tk.Label(hf, text="Pending Orders", font=("Georgia", 18, "bold"),
                 bg=t["bg"], fg=t["text"]).pack(side="left")

        # ── BUG FIX #3: "Mark all as read" button now always rendered ────
        unread = [n for n in self.notifications if not n.get("read", False)]
        if unread:
            self._btn(
                hf,
                f"✓  Mark all as read ({len(unread)})",
                self._mark_all_notifications_read,
                color=t["surface"]
            ).pack(side="right")

        # Pending badge
        pending_orders = [o for o in self.orders
                          if o.get("status") in ["Pending", "Confirmed", "Preparing"]]
        if pending_orders:
            tk.Label(hf,
                     text=f"{len(pending_orders)} pending",
                     font=("Arial", 11, "bold"),
                     bg="#fef3c7", fg=t["accent"],
                     padx=10, pady=4).pack(side="left", padx=12)

        # ── System notifications section ───────────────────────────────────
        if self.notifications:
            notif_frame = tk.Frame(root, bg=t["bg"])
            notif_frame.pack(fill="x", pady=(0, 12))
            tk.Label(notif_frame, text="System Notifications",
                     font=("Arial", 12, "bold"), bg=t["bg"], fg=t["text"]).pack(anchor="w", pady=(0, 6))

            for n in self.notifications[:5]:          # show latest 5
                is_read  = n.get("read", False)
                msg      = n.get("message") or n.get("title") or "Notification"
                # ── BUG FIX #5: amount always shown if present ────────────
                amt_raw  = n.get("amount") or n.get("order_amount") or n.get("totalAmount")
                amt_text = f"  ·  {fmt(amt_raw)}" if amt_raw is not None else ""
                created  = n.get("createdAt") or n.get("created_at") or ""
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        time_text = dt.strftime("%H:%M")
                    except Exception:
                        time_text = created[:5]
                else:
                    time_text = ""

                # ── BUG FIX: card bg + text fg now always visible in both themes
                card_bg  = t["card"] if is_read else (t["surface"] if not self.is_dark else "#1a2744")
                text_fg  = t["text_muted"] if is_read else t["text"]  # was blending into bg
                border_c = t["border"] if is_read else t["accent"]

                nc = tk.Frame(notif_frame, bg=card_bg,
                              highlightthickness=1, highlightbackground=border_c)
                nc.pack(fill="x", pady=3)

                row = tk.Frame(nc, bg=card_bg)
                row.pack(fill="x", padx=14, pady=8)

                dot = "●  " if not is_read else "○  "
                dot_color = t["accent"] if not is_read else t["text_muted"]
                tk.Label(row, text=dot, font=("Arial", 10),
                         bg=card_bg, fg=dot_color).pack(side="left")
                tk.Label(row, text=msg + amt_text, font=("Arial", 10, "bold" if not is_read else "normal"),
                         bg=card_bg, fg=text_fg,          # ← always visible
                         wraplength=700, justify="left").pack(side="left", fill="x", expand=True)
                if time_text:
                    tk.Label(row, text=time_text, font=("Arial", 9),
                             bg=card_bg, fg=t["text_muted"]).pack(side="right")

        # ── Pending orders section ────────────────────────────────────────
        tk.Label(root, text="Orders Needing Attention",
                 font=("Arial", 12, "bold"), bg=t["bg"], fg=t["text"]).pack(anchor="w", pady=(4, 6))

        if not pending_orders:
            tk.Label(root, text="✓  No pending orders right now.",
                     font=("Arial", 11), bg=t["bg"], fg=t["green"]).pack(anchor="w", pady=8)
            return

        outer = tk.Frame(root, bg=t["bg"])
        outer.pack(fill="both", expand=True)
        frame = self._scrollable(outer)

        for o in pending_orders:
            card = tk.Frame(frame, bg=t["card"],
                            highlightthickness=1,
                            highlightbackground=t["accent"] if o.get("status") == "Pending" else t["border"])
            card.pack(fill="x", pady=6, padx=4)

            header = tk.Frame(card, bg=t["card"])
            header.pack(fill="x", padx=16, pady=(12, 4))

            order_number  = o.get("orderNumber") or o.get("orderId") or o.get("id", "—")
            table         = o.get("tableNumber") or o.get("table") or "—"
            status        = o.get("status", "Unknown")
            customer_name = o.get("customerName") or o.get("customer_name") or ""
            # ── BUG FIX #5: robust amount extraction ─────────────────────
            amount = self.safe_float(o.get("totalAmount") or o.get("amount") or 0)

            order_label = f"Order {order_number}"
            if customer_name:
                order_label += f"  —  {customer_name}"

            tk.Label(header, text=order_label, font=("Arial", 12, "bold"),
                     bg=t["card"], fg=t["text"], anchor="w").pack(side="left")
            # Amount always visible in green
            tk.Label(header, text=fmt(amount), font=("Arial", 12, "bold"),
                     bg=t["card"], fg=t["green"]).pack(side="right")

            details = tk.Frame(card, bg=t["card"])
            details.pack(fill="x", padx=16, pady=(0, 4))

            _, sc = STATUS_COLORS.get(status, ("", t["text_sub"]))
            tk.Label(details,
                     text=f"Table: {table}",
                     font=("Arial", 10), bg=t["card"], fg=t["text_sub"]).pack(side="left")
            tk.Label(details,
                     text=f"  •  {status}",
                     font=("Arial", 10, "bold"), bg=t["card"], fg=sc).pack(side="left")

            time_str = o.get("createdAt", "")
            if time_str:
                try:
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    time_display = dt.strftime("%H:%M")
                except Exception:
                    time_display = time_str[:5] if len(time_str) > 5 else time_str
            else:
                time_display = ""
            if time_display:
                tk.Label(details, text=time_display, font=("Arial", 10),
                         bg=t["card"], fg=t["text_muted"]).pack(side="right")

            items = o.get("items", [])
            if items:
                items_text = ", ".join(
                    [f"{i.get('quantity', 0)}x {i.get('menuItemName', 'Item')}" for i in items[:3]]
                )
                if len(items) > 3:
                    items_text += f"  +{len(items) - 3} more"
                tk.Label(card, text=items_text, font=("Arial", 9),
                         bg=t["card"], fg=t["text_sub"],
                         wraplength=600, justify="left").pack(anchor="w", padx=16, pady=(0, 12))

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = RoesAdmin()
    app.mainloop()