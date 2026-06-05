"""
gui.py - Macro yönetim arayüzü (Tkinter)
Modern koyu tema ile kullanıcı dostu arayüz.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import os
from PIL import Image, ImageTk
from macro_manager import MacroManager, Macro


# Renk Paleti
COLORS = {
    "bg": "#0f0f1a",
    "surface": "#1a1a2e",
    "surface2": "#16213e",
    "accent": "#7c3aed",
    "accent_hover": "#6d28d9",
    "accent2": "#2563eb",
    "success": "#10b981",
    "danger": "#ef4444",
    "warning": "#f59e0b",
    "text": "#e2e8f0",
    "text_dim": "#94a3b8",
    "border": "#334155",
    "highlight": "#7c3aed33",
}

FONT_FAMILY = "Segoe UI"


def style_button(btn, color=None, hover_color=None, fg=None):
    """Butona hover efekti ekler."""
    bg = color or COLORS["accent"]
    hc = hover_color or COLORS["accent_hover"]
    fg = fg or COLORS["text"]
    btn.configure(bg=bg, fg=fg, activebackground=hc, activeforeground=fg,
                  relief="flat", cursor="hand2", bd=0)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hc))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))


class MacroEditorDialog(tk.Toplevel):
    """Macro ekleme/düzenleme dialog penceresi."""

    def __init__(self, parent, macro: Macro = None, title="Macro Ekle"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        self.macro = macro

        # Merkeze al
        w, h = 520, 660
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._image_tk = None  # PIL ImageTk referans tutmak icin


        self._build(macro)
        self.wait_window()

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(10, 2))

    def _entry(self, parent, textvariable=None, **kwargs):
        e = tk.Entry(parent, textvariable=textvariable, bg=COLORS["surface2"],
                     fg=COLORS["text"], insertbackground=COLORS["text"],
                     relief="flat", font=(FONT_FAMILY, 11),
                     highlightthickness=1, highlightcolor=COLORS["accent"],
                     highlightbackground=COLORS["border"], **kwargs)
        e.pack(fill="x", ipady=6)
        return e

    def _build(self, macro):
        padx = 20

        # ── Üst çubuk (renkli) ─────────────────────────────────
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x", side="top")

        # ── Başlık ─────────────────────────────────────────────
        tk.Label(self, text="⚙  Macro Düzenle" if macro else "➕  Yeni Macro",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 14, "bold")).pack(anchor="w", padx=padx, pady=(16, 0), side="top")

        # ── Alt butonlar (PACK ÖNCE — her zaman görünür) ───────
        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=56)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)

        cancel_btn = tk.Button(btn_frame, text="  İptal  ", font=(FONT_FAMILY, 10),
                               command=self.destroy, padx=12, pady=6)
        cancel_btn.pack(side="right", padx=(6, 16), pady=10)
        style_button(cancel_btn, COLORS["surface2"], COLORS["border"])

        save_btn = tk.Button(btn_frame, text="💾  Kaydet", font=(FONT_FAMILY, 10, "bold"),
                              command=self._save, padx=12, pady=6)
        save_btn.pack(side="right", pady=10)
        style_button(save_btn)

        # ── Scrollable alan ────────────────────────────────────
        outer = tk.Frame(self, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True, side="top")

        canvas = tk.Canvas(outer, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # İçerik frame (canvas içinde)
        frame = tk.Frame(canvas, bg=COLORS["bg"])
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(frame_id, width=e.width)

        frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse scroll desteği
        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # ── İçerik elemanları (frame içine) ────────────────────
        def label(text):
            tk.Label(frame, text=text, bg=COLORS["bg"], fg=COLORS["text_dim"],
                     font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(10, 2), padx=padx)

        def entry(textvariable=None, **kw):
            e = tk.Entry(frame, textvariable=textvariable, bg=COLORS["surface2"],
                         fg=COLORS["text"], insertbackground=COLORS["text"],
                         relief="flat", font=(FONT_FAMILY, 11),
                         highlightthickness=1, highlightcolor=COLORS["accent"],
                         highlightbackground=COLORS["border"], **kw)
            e.pack(fill="x", ipady=6, padx=padx)
            return e

        # Macro Adı
        label("Macro Adı")
        self.name_var = tk.StringVar(value=macro.name if macro else "")
        entry(self.name_var)

        # Hotkey
        label("Hotkey  (örn: ctrl+alt+1, f5, ctrl+shift+m)")
        self.hotkey_var = tk.StringVar(value=macro.hotkey if macro else "")
        hk_row = tk.Frame(frame, bg=COLORS["bg"])
        hk_row.pack(fill="x", padx=padx)
        self.hotkey_entry = tk.Entry(hk_row, textvariable=self.hotkey_var,
                                     bg=COLORS["surface2"], fg=COLORS["text"],
                                     insertbackground=COLORS["text"], relief="flat",
                                     font=(FONT_FAMILY, 11), highlightthickness=1,
                                     highlightcolor=COLORS["accent"],
                                     highlightbackground=COLORS["border"])
        self.hotkey_entry.pack(side="left", fill="x", expand=True, ipady=6)
        cap_btn = tk.Button(hk_row, text="🎹 Yakala", padx=8,
                            font=(FONT_FAMILY, 9), command=self._capture_hotkey)
        cap_btn.pack(side="right", padx=(6, 0))
        style_button(cap_btn, COLORS["surface2"], COLORS["border"])

        # Hedef Uygulamalar
        label("Hedef Uygulamalar  (boş = her yerde, virgülle ayır: Telegram, Chrome)")
        self.apps_var = tk.StringVar(value=", ".join(macro.target_apps) if macro else "")
        entry(self.apps_var)

        # Macro Metni
        label("Macro Metni")
        text_outer = tk.Frame(frame, bg=COLORS["border"], bd=1)
        text_outer.pack(fill="x", padx=padx)
        self.text_widget = tk.Text(text_outer, bg=COLORS["surface2"], fg=COLORS["text"],
                                   insertbackground=COLORS["text"], relief="flat",
                                   font=(FONT_FAMILY, 11), wrap="word",
                                   height=7, padx=8, pady=6)
        self.text_widget.pack(fill="x")
        if macro:
            self.text_widget.insert("1.0", macro.text)

        # Görseller
        label("Görseller  (Sırayla eklenecektir — PNG, JPG, WEBP, GIF, MP4 vb.)")
        img_row = tk.Frame(frame, bg=COLORS["bg"])
        img_row.pack(fill="x", padx=padx)

        self.img_listbox = tk.Listbox(img_row, bg=COLORS["surface2"], fg=COLORS["text"],
                                      selectbackground=COLORS["accent"], relief="flat",
                                      font=(FONT_FAMILY, 9), height=4, highlightthickness=1)
        self.img_listbox.pack(side="left", fill="x", expand=True)

        if macro and macro.image_paths:
            for p in macro.image_paths:
                self.img_listbox.insert("end", p)

        btn_col = tk.Frame(img_row, bg=COLORS["bg"])
        btn_col.pack(side="left", padx=(6, 0))

        add_btn = tk.Button(btn_col, text="➕ Ekle", width=8, font=(FONT_FAMILY, 9),
                            command=self._add_images)
        add_btn.pack(pady=(0, 2))
        style_button(add_btn, COLORS["surface2"], COLORS["border"])

        rm_btn = tk.Button(btn_col, text="🗑️ Sil", width=8, font=(FONT_FAMILY, 9),
                           command=self._remove_image)
        rm_btn.pack(pady=(2, 0))
        style_button(rm_btn, COLORS["danger"], "#b91c1c")

        # ── Telegram Mesajdan Medya Al ──────────────────────────────────
        tg_fetch_frame = tk.Frame(frame, bg="#1a1f2e", bd=0)
        tg_fetch_frame.pack(fill="x", padx=padx, pady=(6, 0))

        hdr_row = tk.Frame(tg_fetch_frame, bg="#1a1f2e")
        hdr_row.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(hdr_row, text="Telegram Mesajindan Medya Al",
                 bg="#1a1f2e", fg="#60a5fa",
                 font=(FONT_FAMILY, 9, "bold")).pack(side="left")
        tk.Label(hdr_row,
                 text="(mesaj linkini yapistir -> fotograf/video otomatik eklenir)",
                 bg="#1a1f2e", fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 8)).pack(side="left", padx=(6, 0))

        link_row = tk.Frame(tg_fetch_frame, bg="#1a1f2e")
        link_row.pack(fill="x", padx=8, pady=(0, 4))

        self._tg_link_var = tk.StringVar()
        tg_link_entry = tk.Entry(link_row, textvariable=self._tg_link_var,
                                 bg=COLORS["surface2"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"], relief="flat",
                                 font=(FONT_FAMILY, 9),
                                 highlightthickness=1,
                                 highlightcolor="#2563eb",
                                 highlightbackground=COLORS["border"])
        tg_link_entry.pack(side="left", fill="x", expand=True, ipady=5)

        # Placeholder efekti
        def _ph_in(e):
            if self._tg_link_var.get() == "https://t.me/kanal/123":
                tg_link_entry.delete(0, "end")
                tg_link_entry.configure(fg=COLORS["text"])
        def _ph_out(e):
            if not self._tg_link_var.get().strip():
                tg_link_entry.insert(0, "https://t.me/kanal/123")
                tg_link_entry.configure(fg=COLORS["text_dim"])
        tg_link_entry.insert(0, "https://t.me/kanal/123")
        tg_link_entry.configure(fg=COLORS["text_dim"])
        tg_link_entry.bind("<FocusIn>", _ph_in)
        tg_link_entry.bind("<FocusOut>", _ph_out)

        fetch_btn = tk.Button(link_row, text="Getir",
                              font=(FONT_FAMILY, 9, "bold"), padx=10,
                              command=self._fetch_tg_media)
        fetch_btn.pack(side="right", padx=(6, 0))
        style_button(fetch_btn, "#2563eb", "#1d4ed8")

        self._tg_fetch_status = tk.StringVar()
        self._tg_status_lbl = tk.Label(tg_fetch_frame, textvariable=self._tg_fetch_status,
                                       bg="#1a1f2e", fg=COLORS["text_dim"],
                                       font=(FONT_FAMILY, 8), anchor="w")
        self._tg_status_lbl.pack(fill="x", padx=8, pady=(0, 6))

        # ── Emoji Paketi Al ─────────────────────────────────────────────
        ep_frame = tk.Frame(frame, bg="#1a1f2e", bd=0)
        ep_frame.pack(fill="x", padx=padx, pady=(4, 0))

        ep_hdr = tk.Frame(ep_frame, bg="#1a1f2e")
        ep_hdr.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(ep_hdr, text="Emoji Paketi Indir",
                 bg="#1a1f2e", fg="#a78bfa",
                 font=(FONT_FAMILY, 9, "bold")).pack(side="left")
        tk.Label(ep_hdr,
                 text="(t.me/addemoji/... linki veya kisaad)",
                 bg="#1a1f2e", fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 8)).pack(side="left", padx=(6, 0))

        ep_input_row = tk.Frame(ep_frame, bg="#1a1f2e")
        ep_input_row.pack(fill="x", padx=8, pady=(0, 3))

        self._ep_var = tk.StringVar()
        ep_entry = tk.Entry(ep_input_row, textvariable=self._ep_var,
                            bg=COLORS["surface2"], fg=COLORS["text"],
                            insertbackground=COLORS["text"], relief="flat",
                            font=(FONT_FAMILY, 9),
                            highlightthickness=1,
                            highlightcolor="#7c3aed",
                            highlightbackground=COLORS["border"])
        ep_entry.pack(side="left", fill="x", expand=True, ipady=5)

        ep_btn = tk.Button(ep_input_row, text="Paketi Getir",
                           font=(FONT_FAMILY, 9, "bold"), padx=10,
                           command=self._fetch_emoji_pack)
        ep_btn.pack(side="right", padx=(6, 0))
        style_button(ep_btn, "#7c3aed", "#6d28d9")

        # Emoji listesi (kaydırılabilir)
        ep_list_frame = tk.Frame(ep_frame, bg="#1a1f2e")
        ep_list_frame.pack(fill="x", padx=8, pady=(0, 4))

        ep_scroll = tk.Scrollbar(ep_list_frame, orient="vertical")
        self._ep_listbox = tk.Listbox(
            ep_list_frame,
            bg=COLORS["surface2"], fg=COLORS["text"],
            selectbackground="#7c3aed", selectforeground="white",
            relief="flat", font=(FONT_FAMILY, 9),
            height=4, selectmode="extended",
            yscrollcommand=ep_scroll.set
        )
        ep_scroll.config(command=self._ep_listbox.yview)
        ep_scroll.pack(side="right", fill="y")
        self._ep_listbox.pack(side="left", fill="x", expand=True)

        ep_add_btn = tk.Button(ep_frame, text="Secilenleri Makroya Ekle",
                               font=(FONT_FAMILY, 9, "bold"),
                               command=self._add_emoji_pack_to_text)
        ep_add_btn.pack(padx=8, pady=(0, 6), anchor="w")
        style_button(ep_add_btn, "#059669", "#047857")

        self._ep_data = []   # [(char, doc_id), ...] — paketin tam listesi

        self._ep_status = tk.StringVar()
        tk.Label(ep_frame, textvariable=self._ep_status,
                 bg="#1a1f2e", fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 8), anchor="w").pack(fill="x", padx=8, pady=(0, 4))

        # Gönderme Modu
        label("Gönderme Modu")
        self.send_mode_var = tk.StringVar(value=(macro.send_mode if macro else "caption"))
        
        # Raw clipboard verisini dialog acikken hafizada tutmak icin
        self._raw_clipboard_data = macro.raw_clipboard_data if macro else ""
        
        mode_frame = tk.Frame(frame, bg=COLORS["bg"])
        mode_frame.pack(anchor="w", padx=padx)
        for val, lbl, clr in [
            ("raw",       "⭐  KOPYALANANI BİREBİR YAPIŞTIR (En İyisi - Premium Emoji/Link destekler)", "#10b981"),
            ("caption",   "🖼  Görsel + Metin birlikte (Normal metin)", COLORS["text"]),
            ("separate",  "✉  Önce görsel, sonra metin (Normal metin)", COLORS["text"]),
            ("text_only", "📝  Sadece metin (Normal metin)",            COLORS["text"]),
            ("api",       "🔵  Telegram API — (Eski Yöntem)", "#60a5fa"),
        ]:
            tk.Radiobutton(mode_frame, text=lbl, variable=self.send_mode_var, value=val,
                           bg=COLORS["bg"], fg=clr, selectcolor=COLORS["accent"],
                           activebackground=COLORS["bg"], activeforeground=clr,
                           font=(FONT_FAMILY, 9, "bold" if val == "raw" else "normal"),
                           cursor="hand2").pack(anchor="w", pady=2)

        # RAW modu için kopyalama butonu
        self.raw_frame = tk.Frame(frame, bg="#064e3b", bd=0)
        self.raw_frame.pack(fill="x", padx=padx, pady=(4, 0))
        tk.Label(self.raw_frame,
                 text=(
                     "⭐ Telegram'dan istediğin mesajı (Premium Emoji ve Linkler dahil) KOPYALA,\n"
                     "ardından aşağıdaki butona basarak makroya KAYDET."
                 ),
                 bg="#064e3b", fg="#a7f3d0", font=(FONT_FAMILY, 8), justify="left",
                 padx=10, pady=8).pack(anchor="w", pady=(8,4))
                 
        self.raw_btn = tk.Button(self.raw_frame, text="📋 ŞU ANKİ PANOYI KAYDET", 
                                font=(FONT_FAMILY, 9, "bold"), command=self._capture_raw_clipboard)
        self.raw_btn.pack(padx=10, pady=(0,8), anchor="w")
        style_button(self.raw_btn, "#10b981", "#047857")

        self.raw_status = tk.Label(self.raw_frame, text="Durum: " + ("✅ Veri var" if self._raw_clipboard_data else "❌ Veri yok"),
                                  bg="#064e3b", fg="#34d399" if self._raw_clipboard_data else "#f87171",
                                  font=(FONT_FAMILY, 8, "bold"))
        self.raw_status.pack(padx=10, pady=(0,8), anchor="w")

        # API modu açıklama kutusu
        api_hint = tk.Frame(frame, bg="#1e3a5f", bd=0)
        api_hint.pack(fill="x", padx=padx, pady=(4, 0))
        tk.Label(api_hint,
                 text=(
                     "🔵  API Modu — Markdown Format:\n"
                     "  [Gamdom](https://t.ly/gamdomcenk)  →  tıklanabilir link\n"
                     "  **kalın metin**  →  kalın\n"
                     "  __italik metin__  →  italik\n"
                     "  ⚠ Ayarlar > Telegram API bölümünden giriş yapılması gerekir."
                 ),
                 bg="#1e3a5f", fg="#93c5fd",
                 font=(FONT_FAMILY, 8), justify="left",
                 padx=10, pady=8).pack(anchor="w")

        # Radio button degisikliginde frame goster/gizle
        def _on_mode_change(*args):
            m = self.send_mode_var.get()
            if m == "raw":
                self.raw_frame.pack(fill="x", padx=padx, pady=(4, 0), after=mode_frame)
                api_hint.pack_forget()
            elif m == "api":
                api_hint.pack(fill="x", padx=padx, pady=(4, 0), after=self.raw_frame if self.raw_frame.winfo_ismapped() else mode_frame)
                self.raw_frame.pack_forget()
            else:
                self.raw_frame.pack_forget()
                api_hint.pack_forget()
                
        self.send_mode_var.trace_add("write", _on_mode_change)
        _on_mode_change()  # İlk durumu ayarla

        # Gecikme
        label("Gecikme")
        delay_row = tk.Frame(frame, bg=COLORS["bg"])
        delay_row.pack(fill="x", padx=padx, pady=(0, 8))
        tk.Label(delay_row, text="Önce (sn):", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="left")
        self.delay_before_var = tk.StringVar(value=str(macro.delay_before if macro else 0))
        tk.Entry(delay_row, textvariable=self.delay_before_var, width=6,
                 bg=COLORS["surface2"], fg=COLORS["text"], relief="flat",
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(4, 20), ipady=4)
        tk.Label(delay_row, text="Sonra (sn):", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="left")
        self.delay_after_var = tk.StringVar(value=str(macro.delay_after if macro else 0))
        tk.Entry(delay_row, textvariable=self.delay_after_var, width=6,
                 bg=COLORS["surface2"], fg=COLORS["text"], relief="flat",
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(4, 0), ipady=4)

        # Metin Genişletme (Text Expansion)
        label("⌨  Metin Genişletme Kısaltması  (ör: !gm → makroyu otomatik tetikler, boş = kapalı)")
        exp_hint = tk.Frame(frame, bg="#1e3a5f")
        exp_hint.pack(fill="x", padx=padx)
        tk.Label(exp_hint,
                 text="Bu kısaltmayı herhangi bir yerde yazınca makro otomatik tetiklenir.\n"
                      "Örn: '!selam' yazınca → tam metni yapıştırır. Hotkey gerektirmez.",
                 bg="#1e3a5f", fg="#93c5fd", font=(FONT_FAMILY, 8),
                 justify="left", padx=8, pady=6).pack(anchor="w")
        self.expansion_var = tk.StringVar(value=macro.expansion_trigger if macro else "")
        entry(self.expansion_var)

        # Alt boşluk
        tk.Frame(frame, bg=COLORS["bg"], height=16).pack()

        # ── Sprint 2 Alanları ──────────────────────────────────────────────
        # Ayırıcı
        tk.Frame(frame, bg=COLORS["accent"], height=2).pack(fill="x", padx=padx, pady=(8, 0))
        tk.Label(frame, text="⚡  Otomasyon Özellikleri",
                 bg=COLORS["bg"], fg=COLORS["accent"],
                 font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", padx=padx, pady=(6, 0))

        # Auto-repeat
        label("🔁  Otomatik Tekrar")
        ar_row = tk.Frame(frame, bg=COLORS["bg"])
        ar_row.pack(fill="x", padx=padx)
        self.auto_repeat_var = tk.BooleanVar(value=macro.auto_repeat if macro else False)
        tk.Checkbutton(ar_row, text="Aktif  (ilk basış başlatır, ikinci basış durdurur)",
                       variable=self.auto_repeat_var,
                       bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["accent"],
                       activebackground=COLORS["bg"], activeforeground=COLORS["text"],
                       font=(FONT_FAMILY, 9), cursor="hand2").pack(side="left")
        tk.Label(ar_row, text="  Aralık (sn):", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="left")
        self.repeat_interval_var = tk.StringVar(
            value=str(macro.repeat_interval if macro else 30))
        tk.Entry(ar_row, textvariable=self.repeat_interval_var, width=6,
                 bg=COLORS["surface2"], fg=COLORS["text"], relief="flat",
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(4, 0), ipady=4)

        # Zamanlanmış gönderim
        label("⏰  Zamanlanmış Gönderim  (boş = kapalı)")
        sched_row = tk.Frame(frame, bg=COLORS["bg"])
        sched_row.pack(fill="x", padx=padx)
        tk.Label(sched_row, text="Saat (SS:DD):", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="left")
        self.schedule_time_var = tk.StringVar(value=macro.schedule_time if macro else "")
        tk.Entry(sched_row, textvariable=self.schedule_time_var, width=8,
                 bg=COLORS["surface2"], fg=COLORS["text"], relief="flat",
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(4, 16), ipady=4)

        # Gün seçimi
        days = [("Pzt", "Mon"), ("Sal", "Tue"), ("Çar", "Wed"), ("Per", "Thu"),
                ("Cum", "Fri"), ("Cmt", "Sat"), ("Paz", "Sun")]
        self.schedule_day_vars = {}
        cur_days = macro.schedule_days if macro else []
        for label_tr, key in days:
            v = tk.BooleanVar(value=(key in cur_days))
            self.schedule_day_vars[key] = v
            tk.Checkbutton(sched_row, text=label_tr, variable=v,
                           bg=COLORS["bg"], fg=COLORS["text_dim"],
                           selectcolor=COLORS["accent"],
                           activebackground=COLORS["bg"], font=(FONT_FAMILY, 8),
                           cursor="hand2").pack(side="left")

        tk.Label(frame, text="  (Gün seçilmezse her gün tetiklenir)",
                 bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 8)).pack(anchor="w", padx=padx)

        # Broadcast
        label("📢  Broadcast Hedefleri  (API modunda, virgülle ayır: Grup1, Kanal2)")
        self.broadcast_var = tk.StringVar(
            value=", ".join(macro.broadcast_targets) if macro else "")
        entry(self.broadcast_var)
        tk.Label(frame, text="  Boş bırakılırsa aktif Telegram penceresine gönderilir.",
                 bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 8)).pack(anchor="w", padx=padx)

        # Retry
        label("🔄  Hata Durumunda Tekrar Dene  (0 = yok, max 5)")
        retry_row = tk.Frame(frame, bg=COLORS["bg"])
        retry_row.pack(fill="x", padx=padx)
        self.retry_count_var = tk.StringVar(value=str(macro.retry_count if macro else 0))
        retry_scale = tk.Scale(retry_row, from_=0, to=5, orient="horizontal",
                               variable=self.retry_count_var,
                               bg=COLORS["bg"], fg=COLORS["text"],
                               troughcolor=COLORS["surface2"],
                               activebackground=COLORS["accent"],
                               highlightthickness=0, length=160)
        retry_scale.pack(side="left")
        tk.Label(retry_row, textvariable=self.retry_count_var,
                 bg=COLORS["bg"], fg=COLORS["accent"],
                 font=(FONT_FAMILY, 11, "bold")).pack(side="left", padx=8)

        # ── Sprint 4: Kategori & Favori ────────────────────────────────────
        tk.Frame(frame, bg=COLORS["accent"], height=2).pack(fill="x", padx=padx, pady=(12, 0))
        tk.Label(frame, text="🏷  Organizasyon",
                 bg=COLORS["bg"], fg=COLORS["accent"],
                 font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", padx=padx, pady=(6, 0))

        cat_row = tk.Frame(frame, bg=COLORS["bg"])
        cat_row.pack(fill="x", padx=padx, pady=(4, 0))
        tk.Label(cat_row, text="Kategori:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="left")
        self.category_var = tk.StringVar(value=macro.category if macro else "Genel")
        cat_entry = tk.Entry(cat_row, textvariable=self.category_var, width=18,
                             bg=COLORS["surface2"], fg=COLORS["text"], relief="flat",
                             font=(FONT_FAMILY, 10))
        cat_entry.pack(side="left", padx=(6, 16), ipady=4)

        self.favorite_var = tk.BooleanVar(value=macro.favorite if macro else False)
        tk.Checkbutton(cat_row, text="⭐ Favori", variable=self.favorite_var,
                       bg=COLORS["bg"], fg=COLORS["text"], selectcolor=COLORS["accent"],
                       activebackground=COLORS["bg"], font=(FONT_FAMILY, 9),
                       cursor="hand2").pack(side="left")

        label("🏷  Etiketler  (virgülle ayır: sabah, satış, vip)")
        self.tags_var = tk.StringVar(
            value=", ".join(macro.tags) if macro else "")
        entry(self.tags_var)

        # Son boşluk
        tk.Frame(frame, bg=COLORS["bg"], height=20).pack()

    def _add_images(self):
        """Çoklu dosya secici acar."""
        paths = filedialog.askopenfilenames(
            parent=self,
            title="Görselleri Seç",
            filetypes=[
                ("Medya Dosyaları", "*.png *.jpg *.jpeg *.bmp *.webp *.gif *.mp4 *.mov *.avi"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        for p in paths:
            self.img_listbox.insert("end", p)

    def _remove_image(self):
        """Secili gorseli listeden kaldirir."""
        sel = self.img_listbox.curselection()
        if sel:
            for i in reversed(sel):
                self.img_listbox.delete(i)

    def _fetch_tg_media(self):
        """
        Telegram mesaj linkindeki medyayı Telethon ile indirir,
        img_listbox'a otomatik ekler.
        """
        link = self._tg_link_var.get().strip()

        # Placeholder içeriğini yoksay
        if not link or link == "https://t.me/kanal/123":
            self._tg_fetch_status.set("⚠ Önce bir Telegram mesaj linki girin.")
            self._tg_status_lbl.configure(fg=COLORS["warning"])
            return

        if not link.startswith("http"):
            self._tg_fetch_status.set("⚠ Link https://t.me/ ile başlamalı.")
            self._tg_status_lbl.configure(fg=COLORS["warning"])
            return

        self._tg_fetch_status.set("⏳ Mesaj indiriliyor, lütfen bekleyin...")
        self._tg_status_lbl.configure(fg=COLORS["text_dim"])

        def _worker():
            try:
                import telethon_sender as tg
                result = tg.fetch_media_from_message(link, timeout=60)
                self.after(0, lambda: self._on_media_fetched(result))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._set_fetch_status(f"❌ {err}", error=True))

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _on_media_fetched(self, result: dict):
        """Medya indirme tamamlandiginda cagirilir."""
        files  = result.get("files", [])
        text   = result.get("text", "")
        mtype  = result.get("type", "none")
        emojis = result.get("emojis", [])   # [(char, doc_id), ...]

        if not files and not text and not emojis:
            self._set_fetch_status("Bu mesajda medya, metin veya emoji bulunamadi.", error=True)
            return

        # Gorselleri listboxe ekle
        for f in files:
            self.img_listbox.insert("end", f)

        parts = []

        # Dosya durum mesaji
        if files:
            type_map = {"photo": "Fotograf", "video": "Video", "sticker": "Sticker",
                        "document": "Dosya", "album": "Album"}
            parts.append(f"{len(files)} {type_map.get(mtype, 'dosya')} eklendi")

        # Premium emoji ozeti
        if emojis:
            parts.append(f"{len(emojis)} premium emoji bulundu")

        # Emoji sozdizimini olustur: [char](tg://emoji?id=doc_id)
        emoji_syntax = ""
        if emojis:
            emoji_syntax = "".join(
                f"[{char}](tg://emoji?id={doc_id})"
                for char, doc_id in emojis
            )

        # Metin + emoji birlestirme stratejisi
        # Eger hem metin hem emoji varsa: emojiler metin icerisinde zaten
        # Sadece emoji varsa: sozdizimini ekle
        final_text = None

        if text.strip() and emojis:
            # Mesaj metni + emoji sozdizimi iceriyor — tamamini al
            preview = text[:200] + ("..." if len(text) > 200 else "")
            ans = messagebox.askyesno(
                "Metin ve Emoji Ekle?",
                f"Mesajda metin ve {len(emojis)} premium emoji var:\n\n"
                f"{preview}\n\n"
                f"Emoji sözdizimiyle birlikte metin kutusuna eklensin mi?\n"
                f"(Makro gönderiminde Telegram API modu seçili olmalı)",
                parent=self
            )
            if ans:
                # Ham metni olduğu gibi koy — API modunda entity'ler korunur
                final_text = text
                parts.append("Metin + emoji metin kutusuna eklendi")

        elif text.strip():
            # Sadece metin (emoji yok)
            ans = messagebox.askyesno(
                "Metin Ekle?",
                f"Mesajda metin var:\n\n{text[:300]}{'...' if len(text)>300 else ''}\n\n"
                "Metin kutusuna eklensin mi?",
                parent=self
            )
            if ans:
                final_text = text
                parts.append("Metin eklendi")

        elif emojis:
            # Sadece emoji (metin yok)
            ans = messagebox.askyesno(
                "Emoji Ekle?",
                f"{len(emojis)} premium emoji bulundu:\n\n"
                f"{'  '.join(c for c, _ in emojis[:10])}{'...' if len(emojis)>10 else ''}\n\n"
                f"Sözdizimleri metin kutusuna eklensin mi?\n{emoji_syntax[:200]}",
                parent=self
            )
            if ans:
                final_text = emoji_syntax
                parts.append("Emoji sozdizimi eklendi")

        if final_text is not None:
            self.text_widget.delete("1.0", "end")
            self.text_widget.insert("1.0", final_text)

        self._set_fetch_status("  |  ".join(parts) if parts else "Islendi", error=False)

    def _set_fetch_status(self, msg: str, error: bool = False):
        self._tg_fetch_status.set(msg)
        self._tg_status_lbl.configure(
            fg=COLORS["danger"] if error else COLORS["success"]
        )

    def _fetch_emoji_pack(self):
        """Emoji paketini indirir ve listboxe doldurur."""
        pack_input = self._ep_var.get().strip()
        if not pack_input:
            self._ep_status.set("Paket linki veya kisa ad girin.")
            return

        self._ep_status.set("Paket indiriliyor...")
        self._ep_listbox.delete(0, "end")
        self._ep_data = []

        try:
            import telethon_sender as tg_api
        except ImportError:
            self._ep_status.set("Telethon yuklu degil.")
            return

        def _worker():
            try:
                result = tg_api.get_emoji_pack(pack_input, timeout=30)
                self.after(0, lambda: self._on_emoji_pack_fetched(result))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._ep_status.set(f"Hata: {err}"))

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _on_emoji_pack_fetched(self, result: dict):
        """Emoji paketi indirme tamamlandığında."""
        emojis = result.get("emojis", [])
        title  = result.get("title", "Paket")
        total  = result.get("total", len(emojis))

        self._ep_data = emojis
        self._ep_listbox.delete(0, "end")

        for char, doc_id in emojis:
            self._ep_listbox.insert("end", f"{char}  |  {doc_id}")

        self._ep_status.set(
            f"{title} — {len(emojis)} emoji yuklendi "
            f"(Ctrl+A ile hepsini sec, sonra 'Makroya Ekle')"
        )

    def _add_emoji_pack_to_text(self):
        """Listboxten secilen emojileri metin kutusuna ekler."""
        sel = self._ep_listbox.curselection()
        if not sel:
            messagebox.showinfo("Secim Yok",
                "Listeden emoji secin (Ctrl+A tumu seer).",
                parent=self)
            return

        syntax = "".join(
            f"[{self._ep_data[i][0]}](tg://emoji?id={self._ep_data[i][1]})"
            for i in sel
        )
        # Mevcut metnin sonuna ekle
        cur = self.text_widget.get("1.0", "end-1c")
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", cur + syntax)
        self._ep_status.set(f"{len(sel)} emoji metin kutusuna eklendi.")

    def _capture_hotkey(self):
        """Bir sonraki basiilan hotkey'i yakalar."""
        self.hotkey_entry.configure(fg=COLORS["warning"])
        self.hotkey_var.set("Tuslara basin...")

        import keyboard as kb

        def wait():
            event = kb.read_hotkey(suppress=False)
            self.hotkey_var.set(event)
            self.hotkey_entry.configure(fg=COLORS["text"])

        threading.Thread(target=wait, daemon=True).start()

    def _save(self):
        name = self.name_var.get().strip()
        hotkey = self.hotkey_var.get().strip()
        text = self.text_widget.get("1.0", "end-1c")
        apps_raw = self.apps_var.get().strip()
        apps = [a.strip() for a in apps_raw.split(",") if a.strip()] if apps_raw else []

        if not name:
            messagebox.showerror("Hata", "Macro adı boş olamaz!", parent=self)
            return
        if not hotkey or hotkey == "⌨ Tuşlara basın...":
            messagebox.showerror("Hata", "Hotkey girilmedi!", parent=self)
            return
            
        is_raw_mode = (self.send_mode_var.get() == "raw")
        if not text and not is_raw_mode:
            messagebox.showerror("Hata", "Macro metni boş olamaz!", parent=self)
            return
        if is_raw_mode and not self._raw_clipboard_data:
            messagebox.showerror("Hata", "RAW modu seçili ancak panodan veri alınmamış!\n\nLütfen önce 'ŞU ANKİ PANOYI KAYDET' butonuna basın.", parent=self)
            return

        try:
            delay_before = float(self.delay_before_var.get() or 0)
            delay_after = float(self.delay_after_var.get() or 0)
            repeat_interval = float(self.repeat_interval_var.get() or 30)
            retry_count = int(float(self.retry_count_var.get() or 0))
        except ValueError:
            messagebox.showerror("Hata", "Gecikme/aralık süreleri sayı olmalıdır.", parent=self)
            return

        # Zamanlanmış gönderim saat formatı kontrolü
        sched_time = self.schedule_time_var.get().strip()
        if sched_time:
            import re as _re
            if not _re.match(r"^\d{2}:\d{2}$", sched_time):
                messagebox.showerror("Hata", "Saat formatı SS:DD olmalıdır. Örn: 14:30", parent=self)
                return

        # Broadcast hedefleri
        broadcast_raw = self.broadcast_var.get().strip()
        broadcast_targets = [t.strip() for t in broadcast_raw.split(",") if t.strip()]

        # Seçilen günler
        schedule_days = [k for k, v in self.schedule_day_vars.items() if v.get()]

        macro = Macro(
            name=name,
            hotkey=hotkey,
            text=text,
            target_apps=apps,
            delay_before=delay_before,
            delay_after=delay_after,
            image_path="",  # Deprecated
            image_paths=list(self.img_listbox.get(0, "end")),
            send_mode=self.send_mode_var.get(),
            raw_clipboard_data=self._raw_clipboard_data,
            expansion_trigger=self.expansion_var.get().strip(),
            # Sprint 2
            auto_repeat=self.auto_repeat_var.get(),
            repeat_interval=repeat_interval,
            schedule_time=sched_time,
            schedule_days=schedule_days,
            broadcast_targets=broadcast_targets,
            retry_count=retry_count,
            # Sprint 4
            category=self.category_var.get().strip() or "Genel",
            tags=[t.strip() for t in self.tags_var.get().split(",") if t.strip()],
            favorite=self.favorite_var.get(),
        )

        if self.macro:
            macro.id = self.macro.id
            macro.enabled = self.macro.enabled
            macro.use_count = self.macro.use_count
            macro.last_used = self.macro.last_used
            macro.chain_macro_ids = self.macro.chain_macro_ids  # chain ayrı dialog'la yönetilir

        self.result = macro
        self.destroy()

    def _capture_raw_clipboard(self):
        """Kullanici butona bastiginda panodaki zengin veriyi dondurup kaydeder."""
        try:
            import clipboard_utils
            data = clipboard_utils.dump_raw_clipboard()
            if not data:
                messagebox.showerror("Hata", "Pano boş veya okunamadı. Önce Telegram'dan kopyala!", parent=self)
                return
            self._raw_clipboard_data = data
            self.raw_status.config(text="Durum: ✅ Pano başarıyla kaydedildi!", fg="#34d399")
        except Exception as e:
            messagebox.showerror("Hata", f"Panoyu alırken hata oluştu:\n{e}", parent=self)



class MacroGUI:
    """Ana uygulama penceresi."""

    def __init__(self, macro_manager: MacroManager, hotkey_listener, on_close_to_tray=None):
        self.manager = macro_manager
        self.listener = hotkey_listener
        self.on_close_to_tray = on_close_to_tray
        self._last_trigger_label = None
        self._execution_log = []   # [(timestamp, macro_name), ...] son 200 kayıt
        self._setup_window()

    def _setup_window(self):
        self.root = tk.Tk()
        self.root.title("KlavyeMacro")
        self.root.configure(bg=COLORS["bg"])
        self.root.geometry("780x580")
        self.root.minsize(650, 450)

        # Merkeze al
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 780) // 2
        y = (self.root.winfo_screenheight() - 580) // 2
        self.root.geometry(f"780x580+{x}+{y}")

        # Kapatma davranışı
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._load_table()

    def _build_ui(self):
        # ─── Sidebar ───────────────────────────────────────────
        sidebar = tk.Frame(self.root, bg=COLORS["surface"], width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo / başlık
        logo_frame = tk.Frame(sidebar, bg=COLORS["accent"], height=60)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        tk.Label(logo_frame, text="⌨  KlavyeMacro", bg=COLORS["accent"],
                 fg="white", font=(FONT_FAMILY, 13, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        # Sidebar butonları
        self._sidebar_btn(sidebar, "➕  Macro Ekle", self._add_macro)
        self._sidebar_btn(sidebar, "✏️  Düzenle", self._edit_macro)
        self._sidebar_btn(sidebar, "🗑  Sil", self._delete_macro, color=COLORS["danger"])
        
        move_frame = tk.Frame(sidebar, bg=COLORS["surface"])
        move_frame.pack(fill="x", padx=8, pady=2)
        up_btn = tk.Button(move_frame, text="⬆️", font=(FONT_FAMILY, 10), command=self._move_up, width=8)
        up_btn.pack(side="left", expand=True, fill="x", padx=(0, 2))
        style_button(up_btn, COLORS["surface2"], COLORS["border"])
        
        dn_btn = tk.Button(move_frame, text="⬇️", font=(FONT_FAMILY, 10), command=self._move_down, width=8)
        dn_btn.pack(side="left", expand=True, fill="x", padx=(2, 0))
        style_button(dn_btn, COLORS["surface2"], COLORS["border"])
        self._sidebar_sep(sidebar)
        self._sidebar_btn(sidebar, "🗂  Kopyala (Duplicate)", self._duplicate_macro)
        self._sidebar_sep(sidebar)
        self._sidebar_btn(sidebar, "⛓  Zincir Yönet", self._open_chain_dialog)
        self._sidebar_btn(sidebar, "📝  Çalıştırma Logları", self._open_log)
        self._sidebar_btn(sidebar, "🗂  Profil Yönetimi", self._open_profiles)
        self._sidebar_btn(sidebar, "⚡  Toplu İşlemler", self._open_bulk_ops)
        self._sidebar_sep(sidebar)
        self._sidebar_btn(sidebar, "🔵  Telegram API", self._open_telegram_api)
        self._sidebar_btn(sidebar, "⭐  Emoji ID Al", self._open_emoji_id)
        self._sidebar_btn(sidebar, "⚙  Ayarlar", self._open_settings)
        self._sidebar_btn(sidebar, "🔄  Yenile", self._refresh)
        self._sidebar_sep(sidebar)
        self._sidebar_btn(sidebar, "📦  Yedekle (Dışa Aktar)", self._export_macros)
        self._sidebar_btn(sidebar, "📥  Yükle (İçe Aktar)", self._import_macros)

        # Son tetiklenen
        tk.Label(sidebar, text="Son Tetiklenen:", bg=COLORS["surface"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="bottom", pady=(0, 4))
        self._last_trigger_label = tk.Label(sidebar, text="—", bg=COLORS["surface"],
                                             fg=COLORS["success"], font=(FONT_FAMILY, 10, "bold"),
                                             wraplength=200)
        self._last_trigger_label.pack(side="bottom", pady=(0, 2))
        tk.Label(sidebar, text="─" * 28, bg=COLORS["surface"],
                 fg=COLORS["border"]).pack(side="bottom")

        # ─── Ana İçerik ────────────────────────────────────────
        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(side="right", fill="both", expand=True)

        # Tablo başlığı + arama kutusu
        header = tk.Frame(main, bg=COLORS["bg"])
        header.pack(fill="x", padx=20, pady=(20, 8))
        tk.Label(header, text="Macro Listesi", bg=COLORS["bg"],
                 fg=COLORS["text"], font=(FONT_FAMILY, 16, "bold")).pack(side="left")

        # Arama kutusu (sağda)
        search_frame = tk.Frame(header, bg=COLORS["bg"])
        search_frame.pack(side="right")
        tk.Label(search_frame, text="🔍", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 11)).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._load_table())
        search_entry = tk.Entry(search_frame, textvariable=self._search_var,
                                bg=COLORS["surface2"], fg=COLORS["text"],
                                insertbackground=COLORS["text"], relief="flat",
                                font=(FONT_FAMILY, 10), width=22,
                                highlightthickness=1, highlightcolor=COLORS["accent"],
                                highlightbackground=COLORS["border"])
        search_entry.pack(side="left", ipady=5, padx=(4, 0))

        # Tablo
        table_frame = tk.Frame(main, bg=COLORS["bg"])
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Macro.Treeview",
                         background=COLORS["surface"],
                         foreground=COLORS["text"],
                         fieldbackground=COLORS["surface"],
                         borderwidth=0, rowheight=36,
                         font=(FONT_FAMILY, 10))
        style.configure("Macro.Treeview.Heading",
                         background=COLORS["surface2"],
                         foreground=COLORS["text_dim"],
                         borderwidth=0,
                         font=(FONT_FAMILY, 9, "bold"))
        style.map("Macro.Treeview",
                   background=[("selected", COLORS["highlight"])],
                   foreground=[("selected", COLORS["text"])])

        cols = ("status", "name", "hotkey", "apps", "preview")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                  style="Macro.Treeview", selectmode="browse")

        self.tree.heading("status", text="")
        self.tree.heading("name", text="Macro Adı")
        self.tree.heading("hotkey", text="Hotkey")
        self.tree.heading("apps", text="Uygulamalar")
        self.tree.heading("preview", text="Metin Önizlemesi")

        self.tree.column("status", width=30, anchor="center", stretch=False)
        self.tree.column("name", width=150, anchor="w")
        self.tree.column("hotkey", width=140, anchor="w")
        self.tree.column("apps", width=120, anchor="w")
        self.tree.column("preview", anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Çift tıklama ile düzenle
        self.tree.bind("<Double-1>", lambda e: self._edit_macro())
        # Sağ tıklama menüsü
        self.tree.bind("<Button-3>", self._show_context_menu)

        # Durum çubuğu
        status_bar = tk.Frame(main, bg=COLORS["surface"], height=32)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        self.status_label = tk.Label(status_bar, text="✅ Dinleyici Aktif",
                                      bg=COLORS["surface"], fg=COLORS["success"],
                                      font=(FONT_FAMILY, 9))
        self.status_label.pack(side="left", padx=12)
        self.count_label = tk.Label(status_bar, text="",
                                     bg=COLORS["surface"], fg=COLORS["text_dim"],
                                     font=(FONT_FAMILY, 9))
        self.count_label.pack(side="right", padx=12)

    def _sidebar_btn(self, parent, text, command, color=None):
        btn = tk.Button(parent, text=text, font=(FONT_FAMILY, 10),
                         command=command, anchor="w", padx=16, pady=10)
        btn.pack(fill="x", padx=8, pady=2)
        style_button(btn, color or COLORS["surface2"], color or COLORS["border"])
        return btn

    def _sidebar_sep(self, parent):
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=8, pady=8)

    def _show_context_menu(self, event):
        """Sağ tıklama bağlam menüsu"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        macro = self._get_selected_macro()
        if not macro:
            return
        menu = tk.Menu(self.root, tearoff=0, bg=COLORS["surface"], fg=COLORS["text"],
                       activebackground=COLORS["accent"], activeforeground="white",
                       font=(FONT_FAMILY, 10), bd=0, relief="flat")
        toggle_text = "⏸ Devre Dışı Bırak" if macro.enabled else "▶ Etkinleştir"
        menu.add_command(label=toggle_text, command=self._toggle_enabled)
        menu.add_separator()
        menu.add_command(label="✏️  Düzenle", command=self._edit_macro)
        menu.add_command(label="✂  Sil", command=self._delete_macro)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _toggle_enabled(self):
        """Seçili makroyu etkinleştir/devre dışı bırak."""
        macro = self._get_selected_macro()
        if not macro:
            return
        macro.enabled = not macro.enabled
        self.manager.save()
        self.listener.refresh()
        self._load_table()
        # Seçili satırı koru
        self.tree.selection_set(macro.id)

    def _load_table(self):
        """Tablo verilerini yeniler (arama filtresiyle)."""
        query = getattr(self, "_search_var", None)
        query = query.get().strip().lower() if query else ""
        for item in self.tree.get_children():
            self.tree.delete(item)
        shown = 0
        for macro in self.manager.macros:
            if query and not (
                query in macro.name.lower()
                or query in macro.hotkey.lower()
                or query in macro.text.lower()
                or query in macro.category.lower()
                or any(query in a.lower() for a in macro.target_apps)
                or any(query in t.lower() for t in macro.tags)
            ):
                continue
            fav = "⭐" if macro.favorite else ""
            status = ("🟢" if macro.enabled else "🔴") + fav
            apps = ", ".join(macro.target_apps) if macro.target_apps else "Tümü"
            preview = macro.text[:55].replace("\n", " ") + ("..." if len(macro.text) > 55 else "")
            cat_badge = f"[{macro.category}] " if macro.category != "Genel" else ""
            self.tree.insert("", "end", iid=macro.id,
                             values=(status, macro.name, macro.hotkey,
                                     cat_badge + apps, preview))
            shown += 1
        count = len(self.manager.macros)
        active = sum(1 for m in self.manager.macros if m.enabled)
        if query:
            self.count_label.configure(text=f"{shown}/{count} sonuç | {active} aktif")
        else:
            self.count_label.configure(text=f"{active}/{count} aktif macro")



    def _get_selected_macro(self):
        sel = self.tree.selection()
        if not sel:
            return None
        macro_id = sel[0]
        return next((m for m in self.manager.macros if m.id == macro_id), None)

    def _add_macro(self):
        dialog = MacroEditorDialog(self.root, title="Yeni Macro Ekle")
        if dialog.result:
            self.manager.add_macro(dialog.result)
            self.listener.refresh()
            self._load_table()

    def _edit_macro(self):
        macro = self._get_selected_macro()
        if not macro:
            messagebox.showinfo("Bilgi", "Önce bir macro seçin.", parent=self.root)
            return
        dialog = MacroEditorDialog(self.root, macro=macro, title="Macro Düzenle")
        if dialog.result:
            self.manager.update_macro(macro.id, dialog.result)
            self.listener.refresh()
            self._load_table()

    def _delete_macro(self):
        macro = self._get_selected_macro()
        if not macro:
            messagebox.showinfo("Bilgi", "Önce bir macro seçin.", parent=self.root)
            return
        if messagebox.askyesno("Sil", f"'{macro.name}' macro'sunu silmek istiyor musun?",
                                parent=self.root):
            self.manager.delete_macro(macro.id)
            self.listener.refresh()
            self._load_table()

    def _duplicate_macro(self):
        """Seçili makroyu kopyalar (Duplicate)."""
        macro = self._get_selected_macro()
        if not macro:
            messagebox.showinfo("Bilgi", "Önce bir macro seçin.", parent=self.root)
            return
        import copy, uuid
        dup = copy.deepcopy(macro)
        dup.id = str(uuid.uuid4())[:8]
        dup.name = macro.name + " (Kopya)"
        dup.enabled = False  # Kopya devre dışı başlar
        self.manager.add_macro(dup)
        self.listener.refresh()
        self._load_table()
        self.tree.selection_set(dup.id)
        self.tree.see(dup.id)

    def _move_up(self):
        macro = self._get_selected_macro()
        if macro and self.manager.move_macro(macro.id, -1):
            self._load_table()
            self.tree.selection_set(macro.id)

    def _move_down(self):
        macro = self._get_selected_macro()
        if macro and self.manager.move_macro(macro.id, 1):
            self._load_table()
            self.tree.selection_set(macro.id)

    def _refresh(self):
        self.manager.load()
        self.listener.force_restart()
        self._load_table()
        self.status_label.configure(text="✅ Dinleyici Yeniden Başlatıldı", fg=COLORS["success"])
        self.root.after(3000, lambda: self.status_label.configure(text="✅ Dinleyici Aktif"))

    def _export_macros(self):
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            title="Macroları Yedekle",
            defaultextension=".kmd",
            filetypes=[("KlavyeMacro Verisi", "*.kmd")]
        )
        if filepath:
            if self.manager.export_macros(filepath):
                messagebox.showinfo("Başarılı", "Makrolar ve tüm içerik başarıyla dışa aktarıldı!\n\nBu dosyayı başka bir bilgisayarda 'Yükle' diyerek kullanabilirsiniz.", parent=self.root)
            else:
                messagebox.showerror("Hata", "Dışa aktarma sırasında bir hata oluştu.", parent=self.root)

    def _import_macros(self):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            parent=self.root,
            title="Macroları Yükle",
            filetypes=[("KlavyeMacro Verisi", "*.kmd")]
        )
        if filepath:
            if messagebox.askyesno("Onay", "Dikkat: Bu işlem mevcut tüm makrolarınızı silip yerine dosyadan yükleyecek. Devam etmek istiyor musunuz?", parent=self.root):
                if self.manager.import_macros(filepath):
                    self._refresh()
                    messagebox.showinfo("Başarılı", "Makrolar başarıyla yüklendi ve aktif edildi!", parent=self.root)
                else:
                    messagebox.showerror("Hata", "Dosya yüklenirken bir sorun oluştu. Dosya bozuk olabilir.", parent=self.root)

    def _open_settings(self):
        SettingsDialog(self.root, self.manager, self.listener)

    def _open_telegram_api(self):
        TelegramAPIDialog(self.root)

    def _open_emoji_id(self):
        EmojiIDDialog(self.root)

    def _on_close(self):
        if self.manager.settings.get("minimize_to_tray", True):
            self.root.withdraw()
            if self.on_close_to_tray:
                self.on_close_to_tray()
        else:
            self.root.destroy()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def notify_trigger(self, macro_name: str):
        """Macro tetiklendiğinde arayüzü günceller ve log'a kaydeder."""
        if self._last_trigger_label:
            self._last_trigger_label.configure(text=macro_name)
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._execution_log.append((ts, macro_name))
        if len(self._execution_log) > 200:
            self._execution_log.pop(0)

    def _open_chain_dialog(self):
        macro = self._get_selected_macro()
        if not macro:
            messagebox.showinfo("Bilgi", "Önce bir macro seçin.", parent=self.root)
            return
        ChainDialog(self.root, macro, self.manager)
        self.manager.save()

    def _open_log(self):
        ExecutionLogDialog(self.root, self._execution_log)

    def _open_profiles(self):
        ProfileDialog(self.root, self.manager, self.listener,
                      on_reload=lambda: (self._refresh(), None))

    def _open_bulk_ops(self):
        BulkOpsDialog(self.root, self.manager, self.listener,
                      on_reload=lambda: (self.listener.refresh(), self._load_table()))

    def run(self):
        self.root.mainloop()


class SettingsDialog(tk.Toplevel):
    """Ayarlar penceresi."""

    def __init__(self, parent, manager: MacroManager, listener):
        super().__init__(parent)
        self.manager = manager
        self.listener = listener
        self.title("Ayarlar")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        w, h = 440, 540
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()

    def _build(self):
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")
        tk.Label(self, text="⚙  Ayarlar", bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 14, "bold")).pack(anchor="w", padx=24, pady=(20, 10))

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=24)

        def checkbox(text, var):
            cb = tk.Checkbutton(frame, text=text, variable=var, bg=COLORS["bg"],
                                 fg=COLORS["text"], selectcolor=COLORS["accent"],
                                 activebackground=COLORS["bg"], activeforeground=COLORS["text"],
                                 font=(FONT_FAMILY, 10), cursor="hand2")
            cb.pack(anchor="w", pady=6)
            return cb

        s = self.manager.settings

        self.restore_var = tk.BooleanVar(value=s.get("restore_clipboard", True))
        checkbox("📋 Clipboard'u geri yükle (yapıştırma sonrası)", self.restore_var)

        self.tray_var = tk.BooleanVar(value=s.get("minimize_to_tray", True))
        checkbox("📌 Kapatınca sistem tepsisine küçült", self.tray_var)

        self.startup_var = tk.BooleanVar(value=s.get("startup_with_windows", False))
        checkbox("🚀 Windows başlangıcında çalıştır", self.startup_var)

        # ── Sprint 6: PIN kilidi ─────────────────────────────────────────
        tk.Frame(frame, bg=COLORS["border"], height=1).pack(fill="x", pady=(10, 6))
        pin_row = tk.Frame(frame, bg=COLORS["bg"])
        pin_row.pack(fill="x")
        tk.Label(pin_row, text="🔒 PIN Kilidi:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="left")
        saved_pin = s.get("pin", "")
        self._pin_var = tk.StringVar(value=saved_pin)
        pin_entry = tk.Entry(pin_row, textvariable=self._pin_var, show="●",
                             bg=COLORS["surface2"], fg=COLORS["text"], relief="flat",
                             font=(FONT_FAMILY, 10), width=10)
        pin_entry.pack(side="left", padx=8, ipady=4)
        tk.Label(pin_row, text="(boş = kapalı)", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 8)).pack(side="left")

        # ── Sprint 5-6 Hızlı Erişim Butonları ─────────────────────────
        tk.Frame(frame, bg=COLORS["border"], height=1).pack(fill="x", pady=(10, 6))
        tk.Label(frame, text="Araçlar:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(anchor="w")

        tools_row1 = tk.Frame(frame, bg=COLORS["bg"])
        tools_row1.pack(fill="x", pady=2)
        ai_btn = tk.Button(tools_row1, text="✨ AI Metin İyileştir",
                           font=(FONT_FAMILY, 9), command=lambda: AITextDialog(self),
                           padx=8, pady=4)
        ai_btn.pack(side="left", padx=(0, 4))
        style_button(ai_btn, "#7c3aed", "#6d28d9")

        upd_btn = tk.Button(tools_row1, text="🔄 Güncelleme Kontrol",
                            font=(FONT_FAMILY, 9), command=lambda: UpdateCheckDialog(self),
                            padx=8, pady=4)
        upd_btn.pack(side="left")
        style_button(upd_btn, COLORS["success"], "#15803d")

        tools_row2 = tk.Frame(frame, bg=COLORS["bg"])
        tools_row2.pack(fill="x", pady=2)
        del_btn = tk.Button(tools_row2, text="🗑 Son Mesajı Sil",
                            font=(FONT_FAMILY, 9), command=lambda: DeleteLastMessageDialog(self),
                            padx=8, pady=4)
        del_btn.pack(side="left", padx=(0, 4))
        style_button(del_btn, COLORS["danger"], "#b91c1c")

        tk.Label(frame, text="⚡ Webhook: http://127.0.0.1:7474",
                 bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 8)).pack(anchor="w", pady=(4, 0))

        btn_frame = tk.Frame(self, bg=COLORS["bg"])
        btn_frame.pack(fill="x", padx=24, pady=16)

        cancel_btn = tk.Button(btn_frame, text="İptal", font=(FONT_FAMILY, 10),
                                command=self.destroy, padx=16, pady=8)
        cancel_btn.pack(side="right", padx=(6, 0))
        style_button(cancel_btn, COLORS["surface2"], COLORS["border"])

        save_btn = tk.Button(btn_frame, text="💾  Kaydet", font=(FONT_FAMILY, 10, "bold"),
                              command=self._save, padx=16, pady=8)
        save_btn.pack(side="right")
        style_button(save_btn)

    def _save(self):
        s = self.manager.settings
        s["restore_clipboard"] = self.restore_var.get()
        s["minimize_to_tray"] = self.tray_var.get()
        s["pin"] = self._pin_var.get().strip()

        if self.startup_var.get() != s.get("startup_with_windows", False):
            self.manager.set_startup(self.startup_var.get())
        else:
            s["startup_with_windows"] = self.startup_var.get()
            self.manager.save()

        messagebox.showinfo("Kaydedildi", "Ayarlar kaydedildi.", parent=self)
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════
# Telegram API Kurulum Dialog'u
# ═══════════════════════════════════════════════════════════════════════════

class TelegramAPIDialog(tk.Toplevel):
    """
    Telegram API kimlik bilgileri girişi ve bağlantı kurma dialog'u.
    API ID + API Hash: https://my.telegram.org → Apps
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Telegram API Kurulumu")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._code_var = None  # OTP kodu için

        w, h = 460, 500
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()

    def _build(self):
        import telethon_sender as tg

        tk.Frame(self, bg="#2563eb", height=4).pack(fill="x")
        tk.Label(self, text="🔵  Telegram API Kurulumu", bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 13, "bold")).pack(anchor="w", padx=24, pady=(16, 0))

        # Bilgi kutusu
        info = tk.Frame(self, bg="#1e3a5f")
        info.pack(fill="x", padx=24, pady=(10, 0))
        tk.Label(info,
                 text=(
                     "1. https://my.telegram.org adresine git\n"
                     "2. Telefon numaranla giriş yap\n"
                     "3. 'API development tools' tıkla\n"
                     "4. App oluştur → API ID ve API Hash al"
                 ),
                 bg="#1e3a5f", fg="#93c5fd",
                 font=(FONT_FAMILY, 9), justify="left",
                 padx=10, pady=8).pack(anchor="w")

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=24, pady=10)

        def lbl(text):
            tk.Label(frame, text=text, bg=COLORS["bg"], fg=COLORS["text_dim"],
                     font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(8, 2))

        def ent(var, **kw):
            e = tk.Entry(frame, textvariable=var, bg=COLORS["surface2"],
                         fg=COLORS["text"], insertbackground=COLORS["text"],
                         relief="flat", font=(FONT_FAMILY, 11),
                         highlightthickness=1, highlightcolor=COLORS["accent"],
                         highlightbackground=COLORS["border"], **kw)
            e.pack(fill="x", ipady=6)
            return e

        creds = tg.load_creds()

        lbl("API ID  (sayısal)")
        self.api_id_var = tk.StringVar(value=creds.get("api_id", ""))
        ent(self.api_id_var)

        lbl("API Hash  (32 haneli hex)")
        self.api_hash_var = tk.StringVar(value=creds.get("api_hash", ""))
        ent(self.api_hash_var)

        lbl("Telefon Numarası  (örn: +905551234567)")
        self.phone_var = tk.StringVar(value=creds.get("phone", ""))
        ent(self.phone_var)

        # OTP alanı (başta gizli)
        self._otp_frame = tk.Frame(frame, bg=COLORS["bg"])
        lbl2 = tk.Label(self._otp_frame, text="Telegram'dan gelen doğrulama kodu:",
                        bg=COLORS["bg"], fg=COLORS["warning"],
                        font=(FONT_FAMILY, 9))
        lbl2.pack(anchor="w", pady=(8, 2))
        self.otp_var = tk.StringVar()
        self._otp_entry = tk.Entry(self._otp_frame, textvariable=self.otp_var,
                                   bg=COLORS["surface2"], fg=COLORS["warning"],
                                   insertbackground=COLORS["warning"], relief="flat",
                                   font=(FONT_FAMILY, 13, "bold"), justify="center",
                                   highlightthickness=1, highlightcolor=COLORS["warning"],
                                   highlightbackground=COLORS["warning"])
        self._otp_entry.pack(fill="x", ipady=8)
        self._otp_send_btn = tk.Button(self._otp_frame, text="✅  Kodu Gönder",
                                       font=(FONT_FAMILY, 10), padx=12, pady=6,
                                       command=self._submit_otp)
        self._otp_send_btn.pack(pady=(6, 0))
        style_button(self._otp_send_btn, COLORS["success"], "#15803d")

        # Durum
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(frame, textvariable=self._status_var,
                                    bg=COLORS["bg"], fg=COLORS["success"],
                                    font=(FONT_FAMILY, 9), wraplength=380,
                                    justify="left")
        self._status_lbl.pack(anchor="w", pady=(10, 0))

        # Butonlar
        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=52)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)

        close_btn = tk.Button(btn_frame, text="Kapat", font=(FONT_FAMILY, 10),
                              command=self.destroy, padx=12, pady=6)
        close_btn.pack(side="right", padx=(6, 16), pady=10)
        style_button(close_btn, COLORS["surface2"], COLORS["border"])

        self._login_btn = tk.Button(btn_frame, text="🔵  Bağlan & Giriş Yap",
                                    font=(FONT_FAMILY, 10, "bold"),
                                    command=self._start_login, padx=12, pady=6)
        self._login_btn.pack(side="right", pady=10)
        style_button(self._login_btn, "#2563eb", "#1d4ed8")

        # Mevcut bağlantı durumunu göster
        self._check_status()

    def _check_status(self):
        import telethon_sender as tg
        try:
            if tg.is_authorized():
                self._status_var.set("✅  Telegram hesabınız bağlı!")
                self._status_lbl.configure(fg=COLORS["success"])
        except Exception:
            pass

    def _start_login(self):
        import telethon_sender as tg
        import threading

        api_id  = self.api_id_var.get().strip()
        api_hash = self.api_hash_var.get().strip()
        phone   = self.phone_var.get().strip()

        if not api_id or not api_hash or not phone:
            self._status_var.set("⚠  API ID, API Hash ve Telefon gerekli!")
            self._status_lbl.configure(fg=COLORS["warning"])
            return

        tg.save_creds(api_id, api_hash, phone)
        self._status_var.set("📱  Telegram'a bağlanılıyor, kod bekleniyor...")
        self._status_lbl.configure(fg=COLORS["text_dim"])
        self._login_btn.configure(state="disabled")
        self._otp_frame.pack(fill="x")
        self._code_event = threading.Event()
        self._code_result = None

        def _do_login():
            try:
                ok, msg = tg.connect(
                    phone,
                    code_cb=self._wait_for_otp,
                    timeout=120
                )
                self.after(0, lambda: self._on_login_done(ok, msg))
            except Exception as e:
                self.after(0, lambda: self._on_login_done(False, str(e)))

        threading.Thread(target=_do_login, daemon=True).start()

    def _wait_for_otp(self):
        """connect() bu fonksiyonu OTP beklerken çağırır."""
        self._code_event.wait(timeout=90)
        return self._code_result or ""

    def _submit_otp(self):
        self._code_result = self.otp_var.get().strip()
        self._code_event.set()
        self._otp_send_btn.configure(state="disabled", text="Gönderildi...")

    def _on_login_done(self, ok: bool, msg: str):
        if ok:
            self._status_var.set(f"✅  {msg}")
            self._status_lbl.configure(fg=COLORS["success"])
            self._otp_frame.pack_forget()
        else:
            self._status_var.set(f"❌  {msg}")
            self._status_lbl.configure(fg=COLORS["danger"])
        self._login_btn.configure(state="normal")


class EmojiIDDialog(tk.Toplevel):
    """
    Premium Emoji ID Al — Telegram mesaj linkinden emoji document_id'lerini çıkarır.
    Makro metninde [🔥](tg://emoji?id=12345) formatında kullanılır.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("⭐ Premium Emoji ID Al")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        w, h = 520, 480
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()

    def _build(self):
        # Üst çubuk
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")
        tk.Label(self, text="⭐  Premium Emoji ID Al",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 14, "bold")).pack(anchor="w", padx=24, pady=(16, 0))

        # Açıklama
        info = tk.Frame(self, bg="#1e3a5f")
        info.pack(fill="x", padx=24, pady=(10, 0))
        tk.Label(info,
                 text=(
                     "1. Telegram'da premium emoji içeren bir mesaja sağ tıkla → Mesaj linkini kopyala\n"
                     "2. Aşağıya yapıştır → 'ID'leri Al' butonuna bas\n"
                     "3. Listeden emoji'ye çift tıkla → sözdizimi panoya kopyalanır\n"
                     "   Makro metninde kullan: [🔥](tg://emoji?id=12345678)"
                 ),
                 bg="#1e3a5f", fg="#93c5fd",
                 font=(FONT_FAMILY, 8), justify="left",
                 padx=10, pady=8).pack(anchor="w")

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=24, pady=10)

        # Mesaj linki girişi
        tk.Label(frame, text="Telegram Mesaj Linki:",
                 bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(0, 4))

        link_row = tk.Frame(frame, bg=COLORS["bg"])
        link_row.pack(fill="x")

        self._link_var = tk.StringVar()
        link_entry = tk.Entry(link_row, textvariable=self._link_var,
                              bg=COLORS["surface2"], fg=COLORS["text"],
                              insertbackground=COLORS["text"], relief="flat",
                              font=(FONT_FAMILY, 10),
                              highlightthickness=1, highlightcolor=COLORS["accent"],
                              highlightbackground=COLORS["border"])
        link_entry.pack(side="left", fill="x", expand=True, ipady=7)

        fetch_btn = tk.Button(link_row, text="🔍 ID'leri Al",
                              font=(FONT_FAMILY, 9, "bold"), padx=10,
                              command=self._fetch)
        fetch_btn.pack(side="right", padx=(6, 0))
        style_button(fetch_btn, COLORS["accent"], COLORS["accent_hover"])

        # Durum
        self._status_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=self._status_var,
                 bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 8)).pack(anchor="w", pady=(6, 2))

        # Sonuç listesi
        tk.Label(frame, text="Bulunan Emojiler  (çift tıkla → sözdizimini kopyala):",
                 bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(8, 2))

        list_frame = tk.Frame(frame, bg=COLORS["border"], bd=1)
        list_frame.pack(fill="both", expand=True)

        self._listbox = tk.Listbox(list_frame,
                                   bg=COLORS["surface2"], fg=COLORS["text"],
                                   selectbackground=COLORS["accent"],
                                   font=(FONT_FAMILY, 11),
                                   relief="flat", highlightthickness=0,
                                   activestyle="none")
        self._listbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._listbox.bind("<Double-1>", self._copy_syntax)

        # Kopyala butonu
        copy_btn = tk.Button(frame, text="📋 Seçiliyi Kopyala",
                             font=(FONT_FAMILY, 9), padx=10, pady=4,
                             command=self._copy_syntax)
        copy_btn.pack(anchor="e", pady=(6, 0))
        style_button(copy_btn, COLORS["surface2"], COLORS["border"])

        # Kapat
        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=48)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)
        close_btn = tk.Button(btn_frame, text="Kapat",
                              font=(FONT_FAMILY, 10),
                              command=self.destroy, padx=14, pady=6)
        close_btn.pack(side="right", padx=16, pady=10)
        style_button(close_btn, COLORS["surface2"], COLORS["border"])

    def _fetch(self):
        link = self._link_var.get().strip()
        if not link:
            self._status_var.set("⚠  Önce bir mesaj linki girin.")
            return

        self._status_var.set("⏳ Bağlanılıyor, lütfen bekleyin...")
        self._listbox.delete(0, "end")

        def _worker():
            try:
                import telethon_sender as tg
                results = tg.get_emoji_ids_from_message(link, timeout=30)
                self.after(0, lambda: self._on_fetch_done(results))
            except Exception as e:
                self.after(0, lambda: self._status_var.set(f"❌  Hata: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_fetch_done(self, results: list):
        if not results:
            self._status_var.set("⚠  Bu mesajda premium emoji bulunamadı.")
            return
        self._status_var.set(f"✅  {len(results)} emoji bulundu. Çift tıkla → kopyala.")
        for char, doc_id in results:
            self._listbox.insert("end", f"  {char}   →   [emoji](tg://emoji?id={doc_id})   (ID: {doc_id})")

    def _copy_syntax(self, event=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        line = self._listbox.get(sel[0])
        # Sözdizimini çıkar: [...](tg://emoji?id=...)
        import re
        match = re.search(r'\[emoji\]\(tg://emoji\?id=\d+\)', line)
        if match:
            syntax = match.group(0)
            self.clipboard_clear()
            self.clipboard_append(syntax)
            self._status_var.set(f"✅  Kopyalandı: {syntax}")


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 3 — Makro Zinciri Dialog
# ═══════════════════════════════════════════════════════════════════════════

class ChainDialog(tk.Toplevel):
    """
    Seçili makroya zincirlenecek makroları yönetir.
    Bu makro çalıştıktan sonra zincirdeki makrolar sırayla çalıştırılır.
    """

    def __init__(self, parent, macro, manager):
        super().__init__(parent)
        self.macro = macro
        self.manager = manager
        self.title(f"⛓  Zincir Yönet — {macro.name}")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        w, h = 500, 460
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()
        self.wait_window()

    def _build(self):
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")
        tk.Label(self, text=f"⛓  Zincir: {self.macro.name}",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 13, "bold")).pack(anchor="w", padx=24, pady=(14, 0))

        info = tk.Frame(self, bg="#1e3a5f")
        info.pack(fill="x", padx=24, pady=(8, 0))
        tk.Label(info,
                 text="Bu makro çalıştıktan sonra aşağıdaki makrolar sırayla tetiklenir.\n"
                      "Sırayı değiştirmek için seçip ⬆/⬇ kullan.",
                 bg="#1e3a5f", fg="#93c5fd", font=(FONT_FAMILY, 8),
                 justify="left", padx=8, pady=6).pack(anchor="w")

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=24, pady=10)

        # Mevcut zincir listesi
        tk.Label(frame, text="Zincirlenmiş Makrolar:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(anchor="w")
        chain_frame = tk.Frame(frame, bg=COLORS["border"], bd=1)
        chain_frame.pack(fill="x", pady=(4, 0))
        self._chain_lb = tk.Listbox(chain_frame, bg=COLORS["surface2"], fg=COLORS["text"],
                                    selectbackground=COLORS["accent"], font=(FONT_FAMILY, 10),
                                    relief="flat", highlightthickness=0, height=5)
        self._chain_lb.pack(fill="x", padx=4, pady=4)

        # Listeyi doldur
        self._refresh_chain()

        # Kontrol butonları
        ctrl = tk.Frame(frame, bg=COLORS["bg"])
        ctrl.pack(fill="x", pady=4)
        for txt, cmd in [("⬆", self._move_up), ("⬇", self._move_down), ("🗑 Kaldır", self._remove)]:
            b = tk.Button(ctrl, text=txt, font=(FONT_FAMILY, 9), command=cmd, padx=8)
            b.pack(side="left", padx=2)
            style_button(b, COLORS["surface2"], COLORS["border"])

        # Eklenecek makro seçimi
        tk.Label(frame, text="Ekle:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(12, 2))
        avail = [m for m in self.manager.macros if m.id != self.macro.id]
        self._avail_names = [m.name for m in avail]
        self._avail_ids = [m.id for m in avail]
        avail_frame = tk.Frame(frame, bg=COLORS["border"], bd=1)
        avail_frame.pack(fill="x")
        self._avail_lb = tk.Listbox(avail_frame, bg=COLORS["surface2"], fg=COLORS["text"],
                                    selectbackground=COLORS["accent2"], font=(FONT_FAMILY, 10),
                                    relief="flat", highlightthickness=0, height=4)
        for n in self._avail_names:
            self._avail_lb.insert("end", n)
        self._avail_lb.pack(fill="x", padx=4, pady=4)

        add_btn = tk.Button(frame, text="➕ Zincire Ekle", font=(FONT_FAMILY, 9),
                            command=self._add, padx=8, pady=4)
        add_btn.pack(anchor="w", pady=(4, 0))
        style_button(add_btn, COLORS["success"], "#15803d")

        # Kaydet / Kapat
        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=48)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)
        save_btn = tk.Button(btn_frame, text="💾 Kaydet", font=(FONT_FAMILY, 10, "bold"),
                             command=self._save, padx=14, pady=6)
        save_btn.pack(side="right", padx=8, pady=10)
        style_button(save_btn)
        close_btn = tk.Button(btn_frame, text="İptal", font=(FONT_FAMILY, 10),
                              command=self.destroy, padx=14, pady=6)
        close_btn.pack(side="right", pady=10)
        style_button(close_btn, COLORS["surface2"], COLORS["border"])

    def _refresh_chain(self):
        self._chain_lb.delete(0, "end")
        for cid in self.macro.chain_macro_ids:
            m = next((x for x in self.manager.macros if x.id == cid), None)
            self._chain_lb.insert("end", m.name if m else f"[Silinmiş: {cid}]")

    def _add(self):
        sel = self._avail_lb.curselection()
        if not sel:
            return
        mid = self._avail_ids[sel[0]]
        if mid not in self.macro.chain_macro_ids:
            self.macro.chain_macro_ids.append(mid)
            self._refresh_chain()

    def _remove(self):
        sel = self._chain_lb.curselection()
        if sel:
            del self.macro.chain_macro_ids[sel[0]]
            self._refresh_chain()

    def _move_up(self):
        sel = self._chain_lb.curselection()
        if sel and sel[0] > 0:
            i = sel[0]
            lst = self.macro.chain_macro_ids
            lst[i-1], lst[i] = lst[i], lst[i-1]
            self._refresh_chain()
            self._chain_lb.selection_set(i-1)

    def _move_down(self):
        sel = self._chain_lb.curselection()
        lst = self.macro.chain_macro_ids
        if sel and sel[0] < len(lst) - 1:
            i = sel[0]
            lst[i], lst[i+1] = lst[i+1], lst[i]
            self._refresh_chain()
            self._chain_lb.selection_set(i+1)

    def _save(self):
        self.manager.save()
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 3 — Çalıştırma Günlüğü Dialog
# ═══════════════════════════════════════════════════════════════════════════

class ExecutionLogDialog(tk.Toplevel):
    """Son tetiklenen makroların listesini gösterir."""

    def __init__(self, parent, log: list):
        super().__init__(parent)
        self.title("📝  Çalıştırma Günlüğü")
        self.configure(bg=COLORS["bg"])
        self.resizable(True, True)
        self.grab_set()

        w, h = 480, 500
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build(log)

    def _build(self, log):
        tk.Frame(self, bg=COLORS["success"], height=4).pack(fill="x")
        tk.Label(self, text="📝  Çalıştırma Günlüğü",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 13, "bold")).pack(anchor="w", padx=24, pady=(14, 4))

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        # Log listesi
        list_frame = tk.Frame(frame, bg=COLORS["border"], bd=1)
        list_frame.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical")
        lb = tk.Listbox(list_frame, bg=COLORS["surface2"], fg=COLORS["text"],
                        font=(FONT_FAMILY, 10), relief="flat",
                        highlightthickness=0, yscrollcommand=sb.set,
                        selectbackground=COLORS["accent"])
        sb.config(command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.pack(fill="both", expand=True, padx=4, pady=4)

        if not log:
            lb.insert("end", "  Henüz tetiklenen makro yok.")
        else:
            for ts, name in reversed(log):  # En yeni üstte
                lb.insert("end", f"  {ts}   {name}")

        # İstatistik
        tk.Label(frame, text=f"Toplam: {len(log)} tetikleme",
                 bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(6, 0))

        # Kapat
        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=48)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)
        tk.Button(btn_frame, text="Kapat", font=(FONT_FAMILY, 10),
                  command=self.destroy, padx=14, pady=6,
                  bg=COLORS["surface2"], fg=COLORS["text"],
                  relief="flat", cursor="hand2").pack(side="right", padx=16, pady=10)


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 3 — Quick-Send Overlay (Yüzen Mini Panel)
# ═══════════════════════════════════════════════════════════════════════════

class QuickSendOverlay(tk.Toplevel):
    """
    Ekranın sağ kenarında yüzen saydam mini panel.
    Makroları tek tıkla tetikler — Telegram penceresinden çıkmadan.
    Ctrl+Shift+Q ile aç/kapat.
    """

    def __init__(self, parent, manager, listener):
        super().__init__(parent)
        self.manager = manager
        self.listener = listener
        self.overrideredirect(True)        # Pencere çerçevesi yok
        self.attributes("-topmost", True)  # Her zaman üstte
        self.attributes("-alpha", 0.92)    # Hafif şeffaflık
        self.configure(bg=COLORS["surface"])

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 200, min(sh - 120, 600)
        self.geometry(f"{w}x{h}+{sw - w - 8}+60")

        self._build()
        self._make_draggable()

    def _build(self):
        # Başlık çubuğu
        title_bar = tk.Frame(self, bg=COLORS["accent"], height=32)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="⚡ Quick Send", bg=COLORS["accent"],
                 fg="white", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=8)
        tk.Button(title_bar, text="✕", bg=COLORS["accent"], fg="white",
                  relief="flat", font=(FONT_FAMILY, 9, "bold"),
                  command=self.destroy, cursor="hand2",
                  activebackground=COLORS["danger"],
                  activeforeground="white").pack(side="right", padx=4)

        # Makro butonları
        scroll_frame = tk.Frame(self, bg=COLORS["surface"])
        scroll_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(scroll_frame, bg=COLORS["surface"], highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=COLORS["surface"])
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        for macro in self.manager.get_all_enabled():
            short = macro.name[:22] + ("…" if len(macro.name) > 22 else "")
            btn = tk.Button(
                inner, text=short, anchor="w", padx=8,
                font=(FONT_FAMILY, 9), width=22,
                command=lambda m=macro: self._fire(m)
            )
            btn.pack(fill="x", padx=4, pady=1)
            style_button(btn, COLORS["surface2"], COLORS["accent"])

        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

    def _fire(self, macro):
        """Makroyu arka planda tetikler."""
        import threading, time
        def _run():
            time.sleep(0.1)
            self.listener._do_execute(macro)
            macro.increment_use()
        threading.Thread(target=_run, daemon=True).start()

    def _make_draggable(self):
        """Pencereyi fare ile sürüklenebilir yapar."""
        self._drag_x = 0
        self._drag_y = 0

        def on_press(e):
            self._drag_x = e.x_root - self.winfo_x()
            self._drag_y = e.y_root - self.winfo_y()

        def on_drag(e):
            self.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

        self.bind("<Button-1>", on_press)
        self.bind("<B1-Motion>", on_drag)


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 4 — Profil Yönetimi Dialog
# ═══════════════════════════════════════════════════════════════════════════

class ProfileDialog(tk.Toplevel):
    """Makro profillerini kaydet, yükle ve sil."""

    def __init__(self, parent, manager, listener, on_reload=None):
        super().__init__(parent)
        self.manager = manager
        self.listener = listener
        self.on_reload = on_reload
        self.title("🗂  Profil Yönetimi")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        w, h = 420, 440
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()

    def _build(self):
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")
        tk.Label(self, text="🗂  Profil Yönetimi",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 13, "bold")).pack(anchor="w", padx=24, pady=(14, 0))

        info = tk.Frame(self, bg="#1e3a5f")
        info.pack(fill="x", padx=24, pady=(8, 0))
        tk.Label(info,
                 text="Her profil ayrı bir makro seti. Farklı görevler için farklı profiller\n"
                      "oluşturabilirsin (ör: İş, Kişisel, Sabah, Akşam).",
                 bg="#1e3a5f", fg="#93c5fd", font=(FONT_FAMILY, 8),
                 justify="left", padx=8, pady=6).pack(anchor="w")

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=24, pady=10)

        # Mevcut profiller listesi
        tk.Label(frame, text="Kayıtlı Profiller:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(anchor="w")
        lb_frame = tk.Frame(frame, bg=COLORS["border"], bd=1)
        lb_frame.pack(fill="x")
        self._lb = tk.Listbox(lb_frame, bg=COLORS["surface2"], fg=COLORS["text"],
                              selectbackground=COLORS["accent"], font=(FONT_FAMILY, 10),
                              relief="flat", highlightthickness=0, height=6)
        self._lb.pack(fill="x", padx=4, pady=4)
        self._refresh_list()

        # Yükle / Sil butonları
        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill="x", pady=4)
        load_btn = tk.Button(btn_row, text="📂 Yükle", font=(FONT_FAMILY, 9),
                             command=self._load, padx=10)
        load_btn.pack(side="left", padx=2)
        style_button(load_btn, COLORS["success"], "#15803d")
        del_btn = tk.Button(btn_row, text="🗑 Sil", font=(FONT_FAMILY, 9),
                            command=self._delete, padx=10)
        del_btn.pack(side="left", padx=2)
        style_button(del_btn, COLORS["danger"], "#b91c1c")

        # Yeni profil kaydet
        tk.Label(frame, text="Yeni Profil Adı:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(12, 2))
        name_row = tk.Frame(frame, bg=COLORS["bg"])
        name_row.pack(fill="x")
        self._name_var = tk.StringVar(value="profil_1")
        tk.Entry(name_row, textvariable=self._name_var, bg=COLORS["surface2"],
                 fg=COLORS["text"], relief="flat", font=(FONT_FAMILY, 10)).pack(
                 side="left", fill="x", expand=True, ipady=6)
        save_btn = tk.Button(name_row, text="💾 Kaydet", font=(FONT_FAMILY, 9, "bold"),
                             command=self._save, padx=10)
        save_btn.pack(side="right", padx=(6, 0))
        style_button(save_btn)

        self._status = tk.StringVar()
        tk.Label(frame, textvariable=self._status, bg=COLORS["bg"],
                 fg=COLORS["success"], font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(8, 0))

        # Kapat
        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=48)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)
        tk.Button(btn_frame, text="Kapat", font=(FONT_FAMILY, 10),
                  command=self.destroy, padx=14, pady=6,
                  bg=COLORS["surface2"], fg=COLORS["text"],
                  relief="flat", cursor="hand2").pack(side="right", padx=16, pady=10)

    def _refresh_list(self):
        self._lb.delete(0, "end")
        for p in self.manager.list_profiles():
            self._lb.insert("end", f"  {p}")

    def _save(self):
        name = self._name_var.get().strip()
        if not name:
            self._status.set("⚠ Profil adı boş olamaz!")
            return
        if self.manager.save_as_profile(name):
            self._status.set(f"✅ '{name}' kaydedildi.")
            self._refresh_list()
        else:
            self._status.set("❌ Kayıt başarısız.")

    def _load(self):
        sel = self._lb.curselection()
        if not sel:
            self._status.set("⚠ Önce bir profil seçin.")
            return
        name = self._lb.get(sel[0]).strip()
        if messagebox.askyesno("Profil Yükle",
                               f"'{name}' profili yüklenecek.\nMevcut makrolar değiştirilecek. Devam?",
                               parent=self):
            if self.manager.load_profile(name):
                self._status.set(f"✅ '{name}' yüklendi.")
                if self.on_reload:
                    self.on_reload()
            else:
                self._status.set("❌ Yükleme başarısız.")

    def _delete(self):
        sel = self._lb.curselection()
        if not sel:
            return
        name = self._lb.get(sel[0]).strip()
        if messagebox.askyesno("Sil", f"'{name}' profili silinsin mi?", parent=self):
            self.manager.delete_profile(name)
            self._refresh_list()
            self._status.set(f"🗑 '{name}' silindi.")


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 4 — Toplu İşlemler Dialog
# ═══════════════════════════════════════════════════════════════════════════

class BulkOpsDialog(tk.Toplevel):
    """Toplu etkinleştir/devre dışı, kategoriye göre işlem, favoriler."""

    def __init__(self, parent, manager, listener, on_reload=None):
        super().__init__(parent)
        self.manager = manager
        self.listener = listener
        self.on_reload = on_reload
        self.title("⚡  Toplu İşlemler")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        w, h = 400, 480
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()

    def _build(self):
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")
        tk.Label(self, text="⚡  Toplu İşlemler",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 13, "bold")).pack(anchor="w", padx=24, pady=(14, 8))

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=24)

        def section(title):
            tk.Label(frame, text=title, bg=COLORS["bg"], fg=COLORS["accent"],
                     font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(12, 4))
            tk.Frame(frame, bg=COLORS["accent"], height=1).pack(fill="x")

        def big_btn(text, cmd, color=None):
            b = tk.Button(frame, text=text, font=(FONT_FAMILY, 10),
                          command=cmd, padx=12, pady=8, anchor="w")
            b.pack(fill="x", pady=2)
            style_button(b, color or COLORS["surface2"], color or COLORS["border"])

        # Tümü işlemleri
        section("🌐 Tümü")
        big_btn("✅  Tümünü Etkinleştir", self._enable_all, COLORS["success"])
        big_btn("⏸  Tümünü Devre Dışı Bırak", self._disable_all, COLORS["danger"])

        # Kategori işlemleri
        section("🏷 Kategoriye Göre")
        cats = self.manager.get_categories()
        cat_row = tk.Frame(frame, bg=COLORS["bg"])
        cat_row.pack(fill="x", pady=4)
        tk.Label(cat_row, text="Kategori:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="left")
        self._cat_var = tk.StringVar(value=cats[0] if cats else "")
        cat_cb = tk.OptionMenu(cat_row, self._cat_var, *cats if cats else ["—"])
        cat_cb.configure(bg=COLORS["surface2"], fg=COLORS["text"],
                         activebackground=COLORS["accent"], relief="flat",
                         font=(FONT_FAMILY, 9), highlightthickness=0)
        cat_cb.pack(side="left", padx=6)

        cat_btns = tk.Frame(frame, bg=COLORS["bg"])
        cat_btns.pack(fill="x")
        for txt, cmd in [("✅ Etkinleştir", self._enable_cat),
                         ("⏸ Devre Dışı", self._disable_cat),
                         ("🗑 Kategoriyi Sil", self._delete_cat)]:
            b = tk.Button(cat_btns, text=txt, font=(FONT_FAMILY, 9), command=cmd, padx=8)
            b.pack(side="left", padx=2)
            style_button(b, COLORS["surface2"], COLORS["border"])

        # Durum
        self._status = tk.StringVar()
        tk.Label(frame, textvariable=self._status, bg=COLORS["bg"],
                 fg=COLORS["success"], font=(FONT_FAMILY, 9),
                 wraplength=340).pack(anchor="w", pady=(12, 0))

        # Kapat
        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=48)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)
        tk.Button(btn_frame, text="Kapat", font=(FONT_FAMILY, 10),
                  command=self.destroy, padx=14, pady=6,
                  bg=COLORS["surface2"], fg=COLORS["text"],
                  relief="flat", cursor="hand2").pack(side="right", padx=16, pady=10)

    def _reload(self, msg):
        self._status.set(msg)
        if self.on_reload:
            self.on_reload()

    def _enable_all(self):
        self.manager.enable_all()
        self._reload(f"✅ {len(self.manager.macros)} makro etkinleştirildi.")

    def _disable_all(self):
        self.manager.disable_all()
        self._reload(f"⏸ {len(self.manager.macros)} makro devre dışı.")

    def _enable_cat(self):
        c = self._cat_var.get()
        self.manager.enable_by_category(c)
        self._reload(f"✅ '{c}' kategorisi etkinleştirildi.")

    def _disable_cat(self):
        c = self._cat_var.get()
        self.manager.disable_by_category(c)
        self._reload(f"⏸ '{c}' kategorisi devre dışı.")

    def _delete_cat(self):
        c = self._cat_var.get()
        if messagebox.askyesno("Sil", f"'{c}' kategorisindeki TÜM makrolar silinsin mi?",
                               parent=self):
            self.manager.delete_by_category(c)
            self._reload(f"🗑 '{c}' kategorisi silindi.")


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 5 — F1 Kısayol Özet Popup
# ═══════════════════════════════════════════════════════════════════════════

class HotkeyHelpPopup(tk.Toplevel):
    """F1 tuşuyla açılan tüm aktif makroların kısayol özetini gösterir."""

    def __init__(self, parent, manager):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.96)
        self.configure(bg=COLORS["surface"])

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 380, min(sh - 120, 560)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self._build(manager)
        # ESC veya tıklama ile kapat
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<FocusOut>", lambda e: self.after(200, self._check_focus))
        self.focus_force()

    def _check_focus(self):
        try:
            if not self.focus_displayof():
                self.destroy()
        except Exception:
            self.destroy()

    def _build(self, manager):
        # Başlık
        hdr = tk.Frame(self, bg=COLORS["accent"], height=38)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⌨  Aktif Kısayollar  (ESC ile kapat)",
                 bg=COLORS["accent"], fg="white",
                 font=(FONT_FAMILY, 10, "bold")).pack(side="left", padx=12)
        tk.Button(hdr, text="✕", bg=COLORS["accent"], fg="white",
                  relief="flat", font=(FONT_FAMILY, 10, "bold"),
                  command=self.destroy, cursor="hand2",
                  activebackground=COLORS["danger"]).pack(side="right", padx=6)

        canvas = tk.Canvas(self, bg=COLORS["surface"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=COLORS["surface"])
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Kategoriye göre grupla
        cats: dict = {}
        for m in manager.get_all_enabled():
            cat = m.category or "Genel"
            cats.setdefault(cat, []).append(m)

        for cat, macros in cats.items():
            tk.Label(inner, text=f"  {cat}", bg=COLORS["surface2"],
                     fg=COLORS["accent"], font=(FONT_FAMILY, 9, "bold"),
                     anchor="w").pack(fill="x", pady=(6, 2))
            for m in macros:
                row = tk.Frame(inner, bg=COLORS["surface"])
                row.pack(fill="x", padx=8, pady=1)
                hk = m.hotkey or (f"!{m.expansion_trigger}" if m.expansion_trigger else "—")
                tk.Label(row, text=hk, bg=COLORS["accent"], fg="white",
                         font=(FONT_FAMILY, 9, "bold"), width=14,
                         anchor="w", padx=6).pack(side="left")
                name = m.name[:26] + ("…" if len(m.name) > 26 else "")
                fav = "⭐ " if m.favorite else ""
                tk.Label(row, text=fav + name, bg=COLORS["surface"],
                         fg=COLORS["text"], font=(FONT_FAMILY, 9),
                         anchor="w").pack(side="left", padx=6)

        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 5 — Son Mesajı Sil Dialog
# ═══════════════════════════════════════════════════════════════════════════

class DeleteLastMessageDialog(tk.Toplevel):
    """Son gönderilen makro mesajını Telethon ile siler."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("🗑  Son Mesajı Sil")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        w, h = 380, 260
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build()

    def _build(self):
        tk.Frame(self, bg=COLORS["danger"], height=4).pack(fill="x")
        tk.Label(self, text="🗑  Son Mesajı Sil",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 13, "bold")).pack(anchor="w", padx=24, pady=(14, 0))

        warn = tk.Frame(self, bg="#3b1f1f")
        warn.pack(fill="x", padx=24, pady=(10, 0))
        tk.Label(warn,
                 text="⚠  Bu işlem aktif Telegram sohbetindeki son mesajı kalıcı siler!\n"
                      "API modu açık ve bağlı olmalı.",
                 bg="#3b1f1f", fg="#fca5a5", font=(FONT_FAMILY, 8),
                 justify="left", padx=8, pady=6).pack(anchor="w")

        self._status = tk.StringVar(value="")
        tk.Label(self, textvariable=self._status, bg=COLORS["bg"],
                 fg=COLORS["danger"], font=(FONT_FAMILY, 9),
                 wraplength=330).pack(anchor="w", padx=24, pady=(12, 0))

        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=52)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)

        tk.Button(btn_frame, text="Kapat", font=(FONT_FAMILY, 10),
                  command=self.destroy, padx=14, pady=6,
                  bg=COLORS["surface2"], fg=COLORS["text"],
                  relief="flat").pack(side="right", padx=8, pady=10)

        del_btn = tk.Button(btn_frame, text="🗑  Sil",
                            font=(FONT_FAMILY, 10, "bold"),
                            command=self._delete, padx=14, pady=6)
        del_btn.pack(side="right", pady=10)
        style_button(del_btn, COLORS["danger"], "#b91c1c")

    def _delete(self):
        self._status.set("⏳ Siliniyor...")
        import threading

        def _worker():
            try:
                import telethon_sender as tg
                tg.delete_last_message()
                self.after(0, lambda: self._status.set("✅ Son mesaj silindi."))
            except Exception as e:
                self.after(0, lambda: self._status.set(f"❌ {e}"))

        threading.Thread(target=_worker, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 6 — AI Metin İyileştirici Dialog
# ═══════════════════════════════════════════════════════════════════════════

class AITextDialog(tk.Toplevel):
    """Gemini API ile makro metnini iyileştirir."""

    def __init__(self, parent, initial_text: str = ""):
        super().__init__(parent)
        self.title("✨  AI Metin İyileştirici")
        self.configure(bg=COLORS["bg"])
        self.resizable(True, True)
        self.grab_set()
        self.result_text = ""

        w, h = 560, 560
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self._build(initial_text)

    def _build(self, initial_text):
        tk.Frame(self, bg="#7c3aed", height=4).pack(fill="x")
        tk.Label(self, text="✨  AI Metin İyileştirici  (Gemini)",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 13, "bold")).pack(anchor="w", padx=24, pady=(14, 0))

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=24, pady=10)

        # API Key
        key_row = tk.Frame(frame, bg=COLORS["bg"])
        key_row.pack(fill="x", pady=(0, 8))
        tk.Label(key_row, text="Gemini API Key:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(side="left")

        import ai_helper
        self._key_var = tk.StringVar(value=ai_helper.load_api_key())
        key_entry = tk.Entry(key_row, textvariable=self._key_var, show="*",
                             bg=COLORS["surface2"], fg=COLORS["text"], relief="flat",
                             font=(FONT_FAMILY, 9), width=32)
        key_entry.pack(side="left", padx=6, ipady=4)
        tk.Button(key_row, text="Kaydet", font=(FONT_FAMILY, 8),
                  command=lambda: ai_helper.save_api_key(self._key_var.get().strip()),
                  padx=6, pady=3, bg=COLORS["surface2"], fg=COLORS["text"],
                  relief="flat").pack(side="left")

        # Talimat
        tk.Label(frame, text="Talimat:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(anchor="w")
        instructions = [
            "Daha profesyonel ve resmi yaz",
            "Daha samimi ve sıcak yaz",
            "Kısalt, öz ve net hale getir",
            "Türkçe yazım kurallarına göre düzelt",
            "Emoji ekle, daha enerjik yap",
        ]
        self._instr_var = tk.StringVar(value=instructions[0])
        instr_menu = tk.OptionMenu(frame, self._instr_var, *instructions)
        instr_menu.configure(bg=COLORS["surface2"], fg=COLORS["text"],
                             activebackground=COLORS["accent"], relief="flat",
                             font=(FONT_FAMILY, 9), highlightthickness=0)
        instr_menu.pack(fill="x", pady=(2, 8))

        # Orijinal metin
        tk.Label(frame, text="Orijinal Metin:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(anchor="w")
        self._orig = tk.Text(frame, bg=COLORS["surface2"], fg=COLORS["text"],
                             font=(FONT_FAMILY, 10), height=5, relief="flat",
                             insertbackground=COLORS["text"], wrap="word")
        self._orig.insert("1.0", initial_text)
        self._orig.pack(fill="x", pady=(2, 8))

        # İyileştirilmiş metin
        tk.Label(frame, text="AI Çıktısı:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).pack(anchor="w")
        self._out = tk.Text(frame, bg="#0f2027", fg="#34d399",
                            font=(FONT_FAMILY, 10), height=6, relief="flat",
                            insertbackground="#34d399", wrap="word", state="disabled")
        self._out.pack(fill="both", expand=True, pady=(2, 0))

        # Durum
        self._status = tk.StringVar()
        tk.Label(frame, textvariable=self._status, bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 8)).pack(anchor="w")

        # Butonlar
        btn_row = tk.Frame(self, bg=COLORS["surface"], height=52)
        btn_row.pack(fill="x", side="bottom")
        btn_row.pack_propagate(False)

        close_btn = tk.Button(btn_row, text="Kapat", font=(FONT_FAMILY, 10),
                              command=self.destroy, padx=14, pady=6,
                              bg=COLORS["surface2"], fg=COLORS["text"], relief="flat")
        close_btn.pack(side="right", padx=8, pady=10)

        use_btn = tk.Button(btn_row, text="✅ Kullan (Kopyala)",
                            font=(FONT_FAMILY, 10), command=self._use,
                            padx=14, pady=6)
        use_btn.pack(side="right", pady=10)
        style_button(use_btn, COLORS["success"], "#15803d")

        ai_btn = tk.Button(btn_row, text="✨ İyileştir",
                           font=(FONT_FAMILY, 10, "bold"), command=self._run_ai,
                           padx=14, pady=6)
        ai_btn.pack(side="right", pady=10, padx=4)
        style_button(ai_btn, "#7c3aed", "#6d28d9")

    def _run_ai(self):
        text = self._orig.get("1.0", "end").strip()
        if not text:
            self._status.set("⚠ Metin boş!")
            return
        self._status.set("⏳ AI işliyor...")
        import threading

        def _worker():
            try:
                import ai_helper
                result = ai_helper.improve_text(
                    text,
                    instruction=self._instr_var.get(),
                    api_key=self._key_var.get().strip()
                )
                def _update():
                    self._out.configure(state="normal")
                    self._out.delete("1.0", "end")
                    self._out.insert("1.0", result)
                    self._out.configure(state="disabled")
                    self.result_text = result
                    self._status.set("✅ Tamamlandı.")
                self.after(0, _update)
            except Exception as e:
                self.after(0, lambda: self._status.set(f"❌ {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _use(self):
        text = self._out.get("1.0", "end").strip() if self._out.cget("state") == "disabled" else ""
        if not text:
            self._status.set("⚠ Önce 'İyileştir' butonuna bas.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.result_text = text
        self._status.set("✅ Panoya kopyalandı.")


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 6 — PIN Kilidi Dialog
# ═══════════════════════════════════════════════════════════════════════════

class PinLockDialog(tk.Toplevel):
    """Uygulama başlarken PIN kilidi gösterir."""

    def __init__(self, parent, correct_pin: str, on_success=None, on_fail=None):
        super().__init__(parent)
        self.correct_pin = correct_pin
        self.on_success = on_success
        self.on_fail = on_fail
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLORS["bg"])

        w, h = 320, 300
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self._attempts = 0
        self._build()
        self.grab_set()

    def _build(self):
        tk.Frame(self, bg=COLORS["accent"], height=6).pack(fill="x")
        tk.Label(self, text="🔒  KlavyeMacro", bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 16, "bold")).pack(pady=(30, 4))
        tk.Label(self, text="PIN kodunuzu girin", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 10)).pack()

        self._pin_var = tk.StringVar()
        pin_entry = tk.Entry(self, textvariable=self._pin_var, show="●",
                             bg=COLORS["surface2"], fg=COLORS["text"],
                             font=(FONT_FAMILY, 18, "bold"), relief="flat",
                             insertbackground=COLORS["text"], justify="center",
                             width=12)
        pin_entry.pack(pady=20, ipady=10)
        pin_entry.bind("<Return>", lambda e: self._verify())
        pin_entry.focus()

        self._status = tk.StringVar()
        tk.Label(self, textvariable=self._status, bg=COLORS["bg"],
                 fg=COLORS["danger"], font=(FONT_FAMILY, 9)).pack()

        unlock_btn = tk.Button(self, text="Kilidi Aç", font=(FONT_FAMILY, 11, "bold"),
                               command=self._verify, padx=20, pady=8)
        unlock_btn.pack(pady=12)
        style_button(unlock_btn)

    def _verify(self):
        pin = self._pin_var.get().strip()
        if pin == self.correct_pin:
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            self._attempts += 1
            self._pin_var.set("")
            if self._attempts >= 5:
                self._status.set("❌ 5 yanlış deneme. Uygulama kapanıyor.")
                self.after(2000, lambda: self.on_fail() if self.on_fail else None)
            else:
                self._status.set(f"❌ Yanlış PIN! ({self._attempts}/5)")


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 6 — Güncelleme Kontrolü Dialog
# ═══════════════════════════════════════════════════════════════════════════

class UpdateCheckDialog(tk.Toplevel):
    """
    Discord/Chrome tarzı In-App Otomatik Güncelleyici.

    Aşamalar:
      1. Kontrol  — GitHub releases API sorgulanır
      2. Bilgi    — Yeni sürüm + release notları gösterilir
      3. İndirme  — Progress bar ile EXE indirilir
      4. Kurulum  — Bat script çalıştırılır, uygulama yeniden başlar
    """

    VERSION = "1.1.0"

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Guncelleyici - KlavyeMacro")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        w, h = 460, 400
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")

        self._download_url = ""
        self._new_exe_path = ""
        self._result = {}
        self._build()
        self._start_check()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build(self):
        # Üst accent bar
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")

        # İkon + başlık
        hdr = tk.Frame(self, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=24, pady=(18, 0))
        tk.Label(hdr, text="KlavyeMacro", bg=COLORS["bg"], fg=COLORS["text"],
                 font=(FONT_FAMILY, 15, "bold")).pack(side="left")
        tk.Label(hdr, text=f"  v{self.VERSION}", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 10)).pack(side="left", pady=2)

        # Durum etiketi
        self._phase_var = tk.StringVar(value="Guncelleme kontrol ediliyor...")
        self._phase_lbl = tk.Label(self, textvariable=self._phase_var,
                                   bg=COLORS["bg"], fg=COLORS["accent"],
                                   font=(FONT_FAMILY, 10, "bold"))
        self._phase_lbl.pack(anchor="w", padx=24, pady=(14, 0))

        # Release notları kutusu
        notes_frame = tk.Frame(self, bg=COLORS["surface2"])
        notes_frame.pack(fill="both", expand=True, padx=24, pady=(8, 0))
        self._notes = tk.Text(notes_frame, bg=COLORS["surface2"], fg=COLORS["text"],
                              font=(FONT_FAMILY, 9), relief="flat", wrap="word",
                              state="disabled", height=8, padx=10, pady=8)
        sb = ttk.Scrollbar(notes_frame, command=self._notes.yview)
        self._notes.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._notes.pack(fill="both", expand=True)

        # Progress bar (gizli başlar)
        self._prog_frame = tk.Frame(self, bg=COLORS["bg"])
        self._prog_frame.pack(fill="x", padx=24, pady=(10, 0))
        self._prog_label = tk.Label(self._prog_frame, text="",
                                    bg=COLORS["bg"], fg=COLORS["text_dim"],
                                    font=(FONT_FAMILY, 8))
        self._prog_label.pack(anchor="w")
        self._progress = ttk.Progressbar(self._prog_frame, mode="determinate",
                                         length=400, maximum=100)
        self._progress.pack(fill="x")
        self._prog_frame.pack_forget()  # gizle

        # Buton satırı
        btn_frame = tk.Frame(self, bg=COLORS["surface"], height=56)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)

        self._close_btn = tk.Button(btn_frame, text="Kapat",
                                    font=(FONT_FAMILY, 10), command=self.destroy,
                                    padx=16, pady=8, bg=COLORS["surface2"],
                                    fg=COLORS["text"], relief="flat", cursor="hand2")
        self._close_btn.pack(side="right", padx=12, pady=10)

        self._action_btn = tk.Button(btn_frame, text="Kontrol ediliyor...",
                                     font=(FONT_FAMILY, 10, "bold"),
                                     command=self._on_action, padx=16, pady=8,
                                     state="disabled")
        self._action_btn.pack(side="right", pady=10)
        style_button(self._action_btn)

    def _set_notes(self, text: str):
        self._notes.configure(state="normal")
        self._notes.delete("1.0", "end")
        self._notes.insert("1.0", text)
        self._notes.configure(state="disabled")

    # ── Aşama 1: Kontrol ────────────────────────────────────────────────────

    def _start_check(self):
        self._set_notes("GitHub sunucusuna baglaniyor...")
        import threading
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        import ai_helper
        result = ai_helper.check_update(self.VERSION)
        self.after(0, lambda: self._on_check_done(result))

    def _on_check_done(self, result: dict):
        self._result = result

        if result.get("error"):
            self._phase_var.set("Baglanti hatasi")
            self._phase_lbl.configure(fg=COLORS["danger"])
            self._set_notes(
                f"Guncelleme kontrolu basarisiz oldu.\n\n"
                f"Hata: {result['error']}\n\n"
                f"Internet baglantinizi kontrol edin."
            )
            self._action_btn.configure(text="Tekrar Dene", state="normal",
                                       command=self._start_check)
            style_button(self._action_btn, COLORS["surface2"], COLORS["border"])
            return

        if not result["update_available"]:
            self._phase_var.set("En guncel surumdesiniz!")
            self._phase_lbl.configure(fg=COLORS["success"])
            self._set_notes(
                f"KlavyeMacro v{self.VERSION} - En guncel surum\n\n"
                f"Herhangi yeni bir guncelleme bulunmadi.\n"
                f"Daha sonra tekrar kontrol edebilirsiniz."
            )
            self._action_btn.configure(text="Tamam", state="normal",
                                       command=self.destroy)
            style_button(self._action_btn, COLORS["surface2"], COLORS["border"])
            return

        # Yeni surum var!
        latest = result["latest"]
        size_mb = round(result.get("asset_size", 0) / 1_048_576, 1)
        notes_raw = result.get("release_notes", "") or "Bos birakilmis."
        self._download_url = result.get("download_url", "")

        self._phase_var.set(f"Yeni surum: v{latest}")
        self._phase_lbl.configure(fg="#f59e0b")

        size_str = f"{size_mb} MB" if size_mb > 0 else "bilinmiyor"
        notes_text = (
            f"KlavyeMacro v{latest} hazir!\n"
            f"Boyut: {size_str}\n"
            f"{'=' * 42}\n"
            f"Degisiklikler:\n\n"
            f"{notes_raw}"
        )
        self._set_notes(notes_text)

        if self._download_url:
            self._action_btn.configure(
                text=f"Indir ve Yukle  ({size_str})",
                state="normal",
                command=self._on_action
            )
            style_button(self._action_btn, COLORS["success"], "#15803d")
        else:
            # Asset yok, tarayiciya yonlendir
            self._action_btn.configure(
                text="GitHub'da Gor",
                state="normal",
                command=lambda: __import__("webbrowser").open(result.get("url", ""))
            )
            style_button(self._action_btn, COLORS["accent"], COLORS["accent_hover"])

    # ── Aşama 2: İndirme ────────────────────────────────────────────────────

    def _on_action(self):
        if not self._download_url:
            return
        self._start_download()

    def _start_download(self):
        latest = self._result.get("latest", "?")
        self._phase_var.set(f"v{latest} indiriliyor...")
        self._phase_lbl.configure(fg=COLORS["accent"])
        self._action_btn.configure(state="disabled", text="Indiriliyor...")
        self._close_btn.configure(state="disabled")

        # Progress bar'i goster
        self._prog_frame.pack(fill="x", padx=24, pady=(8, 0))

        import threading
        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        import ai_helper

        def progress(downloaded, total):
            if total > 0:
                pct = min(100, int(downloaded * 100 / total))
                dl_mb = round(downloaded / 1_048_576, 1)
                tot_mb = round(total / 1_048_576, 1)
                self.after(0, lambda p=pct, d=dl_mb, t=tot_mb: self._update_progress(p, d, t))

        try:
            path = ai_helper.download_update(self._download_url, progress_cb=progress)
            self.after(0, lambda: self._on_download_done(path))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self._on_download_error(err))

    def _update_progress(self, pct: int, dl_mb: float, tot_mb: float):
        self._progress["value"] = pct
        self._prog_label.configure(text=f"{dl_mb} MB / {tot_mb} MB  ({pct}%)")

    # ── Aşama 3: Kurulum ────────────────────────────────────────────────────

    def _on_download_done(self, path: str):
        self._new_exe_path = path
        self._progress["value"] = 100
        self._prog_label.configure(text="Indirme tamamlandi!")

        latest = self._result.get("latest", "?")
        self._phase_var.set(f"v{latest} hazir - Kurulmak icin bekliyor")
        self._phase_lbl.configure(fg=COLORS["success"])
        self._set_notes(
            f"KlavyeMacro v{latest} indirildi!\n\n"
            f"'Yeniden Baslat ve Yukle' butonuna tikladiginda:\n"
            f"  1. Uygulama kapanir\n"
            f"  2. Yeni surum eski surumun yerine gecilir\n"
            f"  3. KlavyeMacro otomatik yeniden baslar\n\n"
            f"Tum makrolarin ve ayarlarin korunur."
        )

        self._action_btn.configure(
            text="Yeniden Baslat ve Yukle",
            state="normal",
            command=self._install_update
        )
        style_button(self._action_btn, "#f59e0b", "#d97706")
        self._close_btn.configure(state="normal")

    def _on_download_error(self, err: str):
        self._phase_var.set("Indirme basarisiz!")
        self._phase_lbl.configure(fg=COLORS["danger"])
        self._set_notes(
            f"Indirme sirasinda hata olustu:\n\n{err}\n\n"
            f"Baglantinizi kontrol edip tekrar deneyin.\n"
            f"Veya GitHub'dan manuel indirin."
        )
        self._action_btn.configure(text="Tekrar Dene", state="normal",
                                   command=self._start_download)
        style_button(self._action_btn, COLORS["danger"], "#b91c1c")
        self._close_btn.configure(state="normal")

    def _install_update(self):
        """Updater bat'i calistir, uygulamayi kapat."""
        import ai_helper
        try:
            ai_helper.launch_updater_and_quit(self._new_exe_path)
        except RuntimeError as e:
            # EXE modu degil (Python scripti) — GitHub'a yon
            messagebox.showinfo(
                "Kurulum",
                f"Not: {e}\n\n"
                f"Indirilen dosya:\n{self._new_exe_path}",
                parent=self
            )

