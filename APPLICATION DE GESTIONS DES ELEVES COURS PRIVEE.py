#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# COURS PRIVÉ - Desktop manager (Tkinter + SQLite3)
# Owner: DR.ALMOUSTAPHA MANOMI
# Requires Python 3.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3, os, csv, datetime, webbrowser, shutil
from pathlib import Path

THIS_DIR = Path(__file__).parent
DB = THIS_DIR / "data.db"
PHOTOS = THIS_DIR / "photos"
PHOTOS.mkdir(exist_ok=True)

# Theme colors (chosen)
PRIMARY = "#0b6e6e"   # dark teal
ACCENT  = "#ff6b6b"   # coral

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            last_name TEXT,
            first_name TEXT,
            classe TEXT,
            cycle TEXT,
            year TEXT,
            photo TEXT,
            notes TEXT,
            phone TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            topic TEXT,
            duration INTEGER,
            note TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            amount REAL,
            method TEXT,
            note TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            sender TEXT,
            content TEXT,
            read_flag INTEGER DEFAULT 0
        )
    """)
    conn.commit(); conn.close()

class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        master.title("COURS PRIVÉ - DR.ALMOUSTAPHA MANOMI")
        master.geometry("1000x650")
        self.pack(fill="both", expand=True)
        self.create_style(master)
        self.create_widgets()
        init_db()
        self.load_students()

    def create_style(self, master):
        style = ttk.Style(master)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TFrame', background=PRIMARY)
        style.configure('TLabel', background=PRIMARY, foreground='white')
        style.configure('Heading.TLabel', font=('Helvetica', 12, 'bold'), background=PRIMARY, foreground='white')
        style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'))
        master.configure(bg=PRIMARY)

    def create_widgets(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(paned, width=320)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=4)

        ttk.Label(left, text="Liste des élèves", style='Heading.TLabel').pack(anchor="w", padx=6, pady=(6,0))
        self.lst = tk.Listbox(left, width=40)
        self.lst.pack(fill="both", expand=True, padx=6)
        self.lst.bind("<<ListboxSelect>>", self.on_select)

        btnf = ttk.Frame(left)
        btnf.pack(fill="x", padx=6, pady=6)
        ttk.Button(btnf, text="Ajouter élève", command=self.add_student).pack(side="left", padx=2)
        ttk.Button(btnf, text="Modifier", command=self.edit_student).pack(side="left", padx=2)
        ttk.Button(btnf, text="Supprimer", command=self.delete_student).pack(side="left", padx=2)
        ttk.Button(btnf, text="Rafraîchir", command=self.load_students).pack(side="left", padx=2)

        sf = ttk.Frame(left)
        sf.pack(fill="x", padx=6, pady=(0,6))
        ttk.Label(sf, text="Recherche:").pack(side="left")
        self.search_var = tk.StringVar()
        ent = ttk.Entry(sf, textvariable=self.search_var)
        ent.pack(side="left", fill="x", expand=True, padx=4)
        ent.bind("<Return>", lambda e: self.load_students())
        ttk.Button(sf, text="Go", command=self.load_students).pack(side="left", padx=4)

        # Right: tabs
        tabs = ttk.Notebook(right)
        tabs.pack(fill="both", expand=True)
        self.tab_info = ttk.Frame(tabs)
        self.tab_notes = ttk.Frame(tabs)
        self.tab_messages = ttk.Frame(tabs)
        self.tab_inscription = ttk.Frame(tabs)
        self.tab_reports = ttk.Frame(tabs)
        self.tab_planning = ttk.Frame(tabs)
        tabs.add(self.tab_info, text="Gestion des élèves")
        tabs.add(self.tab_notes, text="Notes / Bulletins")
        tabs.add(self.tab_messages, text="Messagerie")
        tabs.add(self.tab_inscription, text="Inscription")
        tabs.add(self.tab_reports, text="Rapports / Paiements")
        tabs.add(self.tab_planning, text="Planning")

        # Info area
        self.info_text = tk.Text(self.tab_info, state="disabled")
        self.info_text.pack(fill="both", expand=True, padx=6, pady=6)

        # Notes tab layout
        nf = ttk.Frame(self.tab_notes)
        nf.pack(fill="both", expand=True)
        lf = ttk.Frame(nf)
        lf.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(lf, text="Historique des cours").pack(anchor="w")
        self.lst_lessons = tk.Listbox(lf, width=40)
        self.lst_lessons.pack(fill="y", expand=True)
        btnl = ttk.Frame(lf)
        btnl.pack(fill="x", pady=6)
        ttk.Button(btnl, text="Ajouter leçon", command=self.add_lesson).pack(side="left", padx=2)
        ttk.Button(btnl, text="Supprimer leçon", command=self.delete_lesson).pack(side="left", padx=2)
        # Right: summary / average
        rf = ttk.Frame(nf)
        rf.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(rf, text="Calculs & Bulletins").pack(anchor="w")
        self.avg_label = ttk.Label(rf, text="Sélectionnez un élève...")
        self.avg_label.pack(anchor="w", pady=6)
        ttk.Button(rf, text="Ajouter contrôle / note", command=self.add_grade).pack(anchor="w", pady=4)

        # Messages tab
        mf = ttk.Frame(self.tab_messages)
        mf.pack(fill="both", expand=True, padx=6, pady=6)
        leftm = ttk.Frame(mf)
        leftm.pack(side="left", fill="y")
        ttk.Label(leftm, text="Messages").pack(anchor="w")
        self.lst_msgs = tk.Listbox(leftm, width=30)
        self.lst_msgs.pack(fill="y", expand=True)
        rightm = ttk.Frame(mf)
        rightm.pack(side="left", fill="both", expand=True, padx=6)
        self.msg_text = tk.Text(rightm, height=15)
        self.msg_text.pack(fill="both", expand=True)
        sendf = ttk.Frame(rightm)
        sendf.pack(fill="x", pady=6)
        ttk.Label(sendf, text="De:").pack(side="left")
        self.sender_var = tk.StringVar(value="Prof")
        ttk.Entry(sendf, textvariable=self.sender_var, width=12).pack(side="left", padx=4)
        ttk.Button(sendf, text="Envoyer", command=self.send_message).pack(side="left", padx=6)
        ttk.Button(sendf, text="Marquer lu", command=self.mark_msg_read).pack(side="left", padx=4)

        # Inscription tab: form
        f = ttk.Frame(self.tab_inscription, padding=6)
        f.pack(fill="both", expand=True)
        lefti = ttk.Frame(f)
        lefti.pack(side="left", fill="y")
        ttk.Label(lefti, text="Formulaire inscription").pack(anchor="w")
        self.form = {}
        for field in ["Code","Prénom","Nom","Classe","Cycle","Année","Téléphone parent"]:
            ttk.Label(lefti, text=field+":").pack(anchor="w", pady=(6,0))
            v = tk.StringVar()
            ttk.Entry(lefti, textvariable=v).pack(fill="x")
            key = field.lower().replace(" ", "_")
            self.form[key] = v
        ttk.Button(lefti, text="Choisir photo (PNG recommandé)", command=self.choose_photo).pack(pady=6)
        self.photo_label = ttk.Label(lefti, text="Aucune photo")
        self.photo_label.pack()
        ttk.Button(lefti, text="Enregistrer", command=self.save_inscription).pack(pady=6)

        # Reports & payments tab
        rptf = ttk.Frame(self.tab_reports, padding=6)
        rptf.pack(fill="both", expand=True)
        ttk.Label(rptf, text="Exports & paiements").pack(anchor="w")
        btns = ttk.Frame(rptf); btns.pack(anchor="w", pady=6)
        ttk.Button(btns, text="Exporter élèves CSV", command=self.export_students_csv).pack(side="left", padx=4)
        ttk.Button(btns, text="Exporter paiements CSV", command=self.export_payments_csv).pack(side="left", padx=4)
        ttk.Button(btns, text="Générer bulletin (HTML)", command=self.generate_report_html).pack(side="left", padx=4)
        ttk.Button(btns, text="Ajouter paiement", command=self.add_payment).pack(side="left", padx=4)
        ttk.Button(btns, text="Voir paiements", command=self.view_payments_window).pack(side="left", padx=4)
        ttk.Button(rptf, text="Ouvrir dossier photos", command=lambda: os.startfile(str(PHOTOS))).pack(anchor="w", pady=6)

        # Planning
        pf = ttk.Frame(self.tab_planning, padding=6)
        pf.pack(fill="both", expand=True)
        ttk.Label(pf, text="Planning simple").pack(anchor="w")
        self.plan_text = tk.Text(pf, height=20)
        self.plan_text.pack(fill="both", expand=True)

        # Status bar
        self.status = ttk.Label(self, text="Prêt", relief=tk.SUNKEN, anchor="w")
        self.status.pack(fill="x", side="bottom")

    # DB helpers
    def conn(self):
        return sqlite3.connect(DB)

    def load_students(self):
        q = self.search_var.get().strip()
        conn = self.conn(); c = conn.cursor()
        if q:
            c.execute("SELECT id, code, last_name, first_name, classe FROM students WHERE code LIKE ? OR last_name LIKE ? OR first_name LIKE ? ORDER BY id", (f"%{q}%",f"%{q}%",f"%{q}%"))
        else:
            c.execute("SELECT id, code, last_name, first_name, classe FROM students ORDER BY id")
        rows = c.fetchall(); conn.close()
        self.lst.delete(0, tk.END)
        for r in rows:
            display = f"{r[1]} - {r[2]} {r[3]} ({r[4]})"
            self.lst.insert(tk.END, f"{r[0]}|{display}")

    def on_select(self, event=None):
        sel = self.lst.curselection()
        if not sel: return
        raw = self.lst.get(sel[0])
        sid = int(raw.split("|",1)[0])
        conn = self.conn(); c = conn.cursor()
        c.execute("SELECT code,last_name,first_name,classe,cycle,year,photo,notes,phone FROM students WHERE id=?", (sid,))
        s = c.fetchone(); conn.close()
        txt = f"Code: {s[0]}\nNom: {s[2]} {s[1]}\nClasse: {s[3]} | Cycle: {s[4]} | Année: {s[5]}\nTéléphone: {s[8] or ''}\n\nNotes:\n{s[7] or ''}"
        self.info_text.configure(state="normal"); self.info_text.delete("1.0","end"); self.info_text.insert("1.0", txt); self.info_text.configure(state="disabled")
        # load lessons and messages
        self.load_lessons(sid); self.load_messages(sid); self.compute_average(sid)

    def add_student(self):
        # open inscription tab and clear form
        for k in self.form: self.form[k].set("")
        self.photo_label.config(text="Aucune photo"); self.chosen_photo = None
        messagebox.showinfo("Ajouter", "Remplissez le formulaire dans l'onglet Inscription, puis cliquez Enregistrer.")

    def edit_student(self):
        sel = self.lst.curselection()
        if not sel:
            messagebox.showinfo("Info","Sélectionnez un élève à modifier"); return
        raw = self.lst.get(sel[0]); sid = int(raw.split("|",1)[0])
        conn = self.conn(); c = conn.cursor()
        c.execute("SELECT code,last_name,first_name,classe,cycle,year,photo,notes,phone FROM students WHERE id=?", (sid,))
        r = c.fetchone(); conn.close()
        if r:
            self.form["code"].set(r[0]); self.form["prénom"].set(r[2]); self.form["nom"].set(r[1])
            self.form["classe"].set(r[3]); self.form["cycle"].set(r[4]); self.form["année"].set(r[5])
            self.form["téléphone_parent"].set(r[8] or "")
            self.photo_label.config(text=r[6] or "Aucune photo")
            self.chosen_photo = r[6]; self.editing_id = sid
            messagebox.showinfo("Modifier", "Faites les changements dans l'onglet Inscription, puis Enregistrer.")

    def delete_student(self):
        sel = self.lst.curselection()
        if not sel:
            messagebox.showinfo("Info","Sélectionnez un élève à supprimer"); return
        if not messagebox.askyesno("Confirm","Supprimer cet élève ?"): return
        raw = self.lst.get(sel[0]); sid = int(raw.split("|",1)[0])
        conn = self.conn(); c = conn.cursor()
        c.execute("DELETE FROM students WHERE id=?", (sid,))
        c.execute("DELETE FROM lessons WHERE student_id=?", (sid,))
        c.execute("DELETE FROM payments WHERE student_id=?", (sid,))
        c.execute("DELETE FROM messages WHERE student_id=?", (sid,))
        conn.commit(); conn.close(); self.load_students()

    def choose_photo(self):
        p = filedialog.askopenfilename(title="Choisir photo", filetypes=[("Images","*.png;*.gif;*.jpg;*.jpeg"),("All","*.*")])
        if p:
            dest = PHOTOS / Path(p).name
            try: shutil.copy(p, dest)
            except Exception: pass
            self.photo_label.config(text=str(dest)); self.chosen_photo = str(dest)

    def save_inscription(self):
        code = self.form["code"].get().strip()
        prenom = self.form["prénom"].get().strip()
        nom = self.form["nom"].get().strip()
        classe = self.form["classe"].get().strip()
        cycle = self.form["cycle"].get().strip()
        year = self.form["année"].get().strip()
        phone = self.form["téléphone_parent"].get().strip() if "téléphone_parent" in self.form else ""
        photo = getattr(self, "chosen_photo", None)
        if not code or not prenom:
            messagebox.showwarning("Champs manquants","Code et prénom requis"); return
        conn = self.conn(); c = conn.cursor()
        if getattr(self, "editing_id", None):
            c.execute("UPDATE students SET code=?, last_name=?, first_name=?, classe=?, cycle=?, year=?, photo=?, phone=? WHERE id=?",
                      (code, nom, prenom, classe, cycle, year, photo, phone, self.editing_id))
            self.editing_id = None
        else:
            try:
                c.execute("INSERT INTO students (code,last_name,first_name,classe,cycle,year,photo,phone) VALUES (?,?,?,?,?,?,?,?)",
                          (code, nom, prenom, classe, cycle, year, photo, phone))
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
        conn.commit(); conn.close(); self.load_students(); messagebox.showinfo("OK","Élève enregistré")

    def open_inscription_window(self, edit=False):
        # helper kept for backward compatibility
        messagebox.showinfo("Inscription", "Utilisez l'onglet Inscription pour remplir le formulaire.")

    # Lessons / notes
    def load_lessons(self, student_id):
        conn = self.conn(); c = conn.cursor()
        c.execute("SELECT id,date,topic,duration,note FROM lessons WHERE student_id=? ORDER BY date DESC", (student_id,))
        rows = c.fetchall(); conn.close()
        self.lst_lessons.delete(0, tk.END)
        for r in rows:
            self.lst_lessons.insert(tk.END, f"{r[0]}|{r[1]} - {r[2]} ({r[3]}min) Note:{r[4] or ''}")

    def add_lesson(self):
        sel = self.lst.curselection(); 
        if not sel: messagebox.showinfo("Info","Sélectionnez un élève"); return
        sid = int(self.lst.get(sel[0]).split("|",1)[0])
        w = tk.Toplevel(self); w.title("Ajouter leçon")
        ttk.Label(w, text="Date (YYYY-MM-DD)").pack(); dvar = tk.StringVar(value=str(datetime.date.today())); ttk.Entry(w, textvariable=dvar).pack()
        ttk.Label(w, text="Sujet").pack(); tvar = tk.StringVar(); ttk.Entry(w, textvariable=tvar).pack()
        ttk.Label(w, text="Durée (min)").pack(); dur = tk.IntVar(value=60); ttk.Entry(w, textvariable=dur).pack()
        ttk.Label(w, text="Note/Commentaire").pack(); nvar = tk.StringVar(); ttk.Entry(w, textvariable=nvar).pack()
        def save():
            conn = self.conn(); c = conn.cursor()
            c.execute("INSERT INTO lessons (student_id,date,topic,duration,note) VALUES (?,?,?,?,?)", (sid, dvar.get(), tvar.get(), dur.get(), nvar.get()))
            conn.commit(); conn.close(); w.destroy(); self.load_lessons(sid)
        ttk.Button(w, text="Enregistrer", command=save).pack(pady=6)

    def delete_lesson(self):
        sel = self.lst_lessons.curselection()
        if not sel: messagebox.showinfo("Info","Sélectionnez une leçon"); return
        rid = int(self.lst_lessons.get(sel[0]).split("|",1)[0])
        if not messagebox.askyesno("Confirm","Supprimer cette leçon ?"): return
        conn = self.conn(); c = conn.cursor(); c.execute("DELETE FROM lessons WHERE id=?", (rid,)); conn.commit(); conn.close(); self.load_students()

    def add_grade(self):
        sel = self.lst.curselection()
        if not sel: messagebox.showinfo("Info","Sélectionnez un élève"); return
        sid = int(self.lst.get(sel[0]).split("|",1)[0])
        w = tk.Toplevel(self); w.title("Ajouter note/contrôle")
        ttk.Label(w, text="Titre").pack(); title = tk.StringVar(); ttk.Entry(w, textvariable=title).pack()
        ttk.Label(w, text="Valeur (0-20)").pack(); val = tk.DoubleVar(value=10); ttk.Entry(w, textvariable=val).pack()
        ttk.Label(w, text="Commentaire").pack(); cvar = tk.StringVar(); ttk.Entry(w, textvariable=cvar).pack()
        def save():
            conn = self.conn(); c = conn.cursor()
            c.execute("INSERT INTO lessons (student_id,date,topic,duration,note) VALUES (?,?,?,?,?)", (sid, str(datetime.date.today()), title.get(), 0, str(val.get()) + " | " + cvar.get()))
            conn.commit(); conn.close(); w.destroy(); self.load_lessons(sid); self.compute_average(sid)
        ttk.Button(w, text="Enregistrer", command=save).pack(pady=6)

    def compute_average(self, student_id):
        conn = self.conn(); c = conn.cursor()
        c.execute("SELECT note FROM lessons WHERE student_id=? AND note IS NOT NULL", (student_id,))
        rows = c.fetchall(); conn.close()
        grades = []
        for r in rows:
            try:
                g = float(str(r[0]).split("|")[0].strip()); grades.append(g)
            except Exception:
                pass
        if grades:
            avg = sum(grades)/len(grades)
            self.avg_label.config(text=f"Moyenne: {avg:.2f} ({len(grades)} notes)")
        else:
            self.avg_label.config(text="Aucune note disponible")

    # Messages
    def load_messages(self, student_id):
        conn = self.conn(); c = conn.cursor()
        c.execute("SELECT id,date,sender,content,read_flag FROM messages WHERE student_id=? ORDER BY date DESC", (student_id,))
        rows = c.fetchall(); conn.close()
        self.lst_msgs.delete(0, tk.END)
        for r in rows:
            flag = "" if r[4] else "*NEW* "
            self.lst_msgs.insert(tk.END, f"{r[0]}|{flag}{r[1]} - {r[2]}: {r[3][:30]}")

    def send_message(self):
        sel = self.lst.curselection(); 
        if not sel: messagebox.showinfo("Info","Sélectionnez un élève pour envoyer"); return
        sid = int(self.lst.get(sel[0]).split("|",1)[0]); content = self.msg_text.get("1.0","end").strip()
        if not content: messagebox.showwarning("Vide","Écrivez un message"); return
        conn = self.conn(); c = conn.cursor()
        c.execute("INSERT INTO messages (student_id,date,sender,content,read_flag) VALUES (?,?,?,?,0)", (sid, str(datetime.datetime.now()), self.sender_var.get(), content))
        conn.commit(); conn.close(); self.msg_text.delete("1.0","end"); self.load_messages(sid); messagebox.showinfo("OK","Message envoyé"); messagebox.showinfo("Notification","Message envoyé aux parents/élève")

    def mark_msg_read(self):
        sel = self.lst_msgs.curselection()
        if not sel: messagebox.showinfo("Info","Sélectionnez un message"); return
        rid = int(self.lst_msgs.get(sel[0]).split("|",1)[0])
        conn = self.conn(); c = conn.cursor(); c.execute("UPDATE messages SET read_flag=1 WHERE id=?", (rid,)); conn.commit(); conn.close()
        self.load_students()

    # Payments
    def add_payment(self):
        sel = self.lst.curselection()
        if not sel:
            messagebox.showinfo("Info","Sélectionnez un élève avant d'ajouter un paiement"); return
        sid = int(self.lst.get(sel[0]).split("|",1)[0])
        w = tk.Toplevel(self); w.title("Ajouter paiement")
        ttk.Label(w, text="Date (YYYY-MM-DD)").pack(); d = tk.StringVar(value=str(datetime.date.today())); ttk.Entry(w, textvariable=d).pack()
        ttk.Label(w, text="Montant").pack(); amt = tk.DoubleVar(value=0.0); ttk.Entry(w, textvariable=amt).pack()
        ttk.Label(w, text="Méthode (espèces/carte)").pack(); method = tk.StringVar(); ttk.Entry(w, textvariable=method).pack()
        ttk.Label(w, text="Note").pack(); note = tk.StringVar(); ttk.Entry(w, textvariable=note).pack()
        def save():
            conn = self.conn(); c = conn.cursor()
            c.execute("INSERT INTO payments (student_id,date,amount,method,note) VALUES (?,?,?,?,?)", (sid, d.get(), float(amt.get()), method.get(), note.get()))
            conn.commit(); conn.close(); w.destroy(); messagebox.showinfo("OK","Paiement enregistré")
        ttk.Button(w, text="Enregistrer", command=save).pack(pady=6)

    def view_payments_window(self):
        sel = self.lst.curselection()
        if not sel:
            messagebox.showinfo("Info","Sélectionnez un élève pour voir ses paiements"); return
        sid = int(self.lst.get(sel[0]).split("|",1)[0])
        conn = self.conn(); c = conn.cursor(); c.execute("SELECT id,date,amount,method,note FROM payments WHERE student_id=? ORDER BY date DESC", (sid,))
        rows = c.fetchall(); conn.close()
        w = tk.Toplevel(self); w.title("Paiements")
        lb = tk.Listbox(w, width=80)
        lb.pack(fill="both", expand=True)
        for r in rows:
            lb.insert(tk.END, f"{r[1]} | {r[2]} | {r[3]} | {r[4] or ''}")

    # Reports / exports
    def export_students_csv(self):
        conn = self.conn(); c = conn.cursor()
        c.execute("SELECT code,last_name,first_name,classe,cycle,year,photo,phone FROM students")
        rows = c.fetchall(); conn.close()
        p = Path(__file__).parent / "students_export.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["code","last_name","first_name","classe","cycle","year","photo","phone"])
            w.writerows(rows)
        messagebox.showinfo("Export", f"CSV créé: {p}")

    def export_payments_csv(self):
        conn = self.conn(); c = conn.cursor()
        c.execute("SELECT student_id,date,amount,method,note FROM payments")
        rows = c.fetchall(); conn.close()
        p = Path(__file__).parent / "payments_export.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["student_id","date","amount","method","note"])
            w.writerows(rows)
        messagebox.showinfo("Export", f"CSV créé: {p}")

    def generate_report_html(self):
        sel = self.lst.curselection()
        if not sel: messagebox.showinfo("Info","Sélectionnez un élève"); return
        sid = int(self.lst.get(sel[0]).split("|",1)[0])
        conn = self.conn(); c = conn.cursor()
        c.execute("SELECT code,last_name,first_name,classe,cycle,year,photo,phone FROM students WHERE id=?", (sid,)); s = c.fetchone()
        c.execute("SELECT date,topic,duration,note FROM lessons WHERE student_id=? ORDER BY date DESC", (sid,)); lessons = c.fetchall()
        conn.close()
        html = f"<html><head><meta charset='utf-8'><title>Bulletin {s[2]} {s[1]}</title></head><body><h1>Bulletin - COURS PRIVÉ</h1><h2>{s[2]} {s[1]} ({s[0]})</h2><p>Classe: {s[3]} | Cycle: {s[4]} | Année: {s[5]}</p><p>Téléphone: {s[7] or ''}</p><h3>Leçons / Contrôles</h3><ul>"
        for L in lessons:
            html += f"<li>{L[0]} - {L[1]} - Durée {L[2]} - Note: {L[3] or ''}</li>"
        html += "</ul></body></html>"
        p = Path(__file__).parent / f"bulletin_{s[0]}.html"
        with open(p, "w", encoding="utf-8") as f: f.write(html)
        messagebox.showinfo("Généré", f"Bulletin HTML: {p}")
        webbrowser.open(p.as_uri())

if __name__ == '__main__':
    init_db()
    root = tk.Tk()
    app = App(root)
    root.mainloop()
