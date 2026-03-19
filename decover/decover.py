import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import fitz  # PyMuPDF
import threading
import os
import certifi
import ssl
import re

# PDF Layout Engine
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors

# --- Universal Import Logic ---
try:
    from mistralai import Mistral
except ImportError:
    try:
        from mistralai.client import Mistral
    except ImportError:
        Mistral = None

# MAC SSL FIX
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
ssl._create_default_https_context = ssl._create_unverified_context

class CoverLetterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cover Letter Architect Pro")
        self.root.geometry("900x980")
        self.root.configure(bg="#f4f7f9")
        
        self.cv_text = ""
        self.api_key = None
        self.ask_for_key()

    def ask_for_key(self):
        self.key_win = tk.Toplevel(self.root)
        self.key_win.title("API Key")
        self.key_win.geometry("400x180")
        self.key_win.grab_set()
        tk.Label(self.key_win, text="Enter Mistral API Key:", font=("Arial", 10, "bold")).pack(pady=15)
        self.key_entry = ttk.Entry(self.key_win, show="*", width=40)
        self.key_entry.pack(pady=5)
        ttk.Button(self.key_win, text="Verify & Launch", command=self.verify_key).pack(pady=20)

    def verify_key(self):
        key = self.key_entry.get().strip()
        if key:
            self.api_key = key
            self.key_win.destroy()
            self.setup_main_ui()

    def setup_main_ui(self):
        main = tk.Frame(self.root, bg="#f4f7f9", padx=30, pady=20)
        main.pack(expand=True, fill="both")
        
        # --- HEADER ---
        header_f = tk.Frame(main, bg="#f4f7f9")
        header_f.pack(fill="x")
        tk.Label(header_f, text="AI Cover Letter Designer", font=("Helvetica", 20, "bold"), bg="#f4f7f9").pack(side="left")
        
        # RESET BUTTON (Persistent salary/name)
        tk.Button(header_f, text="🔄 RESET PROCESS", command=self.reset_ui, bg="#e74c3c", fg="white", font=("Arial", 9, "bold"), relief="flat", padx=10).pack(side="right")

        # --- STEP 1: UPLOAD ---
        self.upload_btn = tk.Button(main, text="1. Upload Profile (PDF)", command=self.upload_cv, bg="#bdc3c7", relief="flat", font=("Arial", 10, "bold"))
        self.upload_btn.pack(fill="x", pady=(15, 5))
        self.cv_label = tk.Label(main, text="No profile loaded", fg="gray", bg="#f4f7f9")
        self.cv_label.pack()

        # --- STEP 2: JD ---
        tk.Label(main, text="2. Paste Job Description:", bg="#f4f7f9", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
        self.jd_text = tk.Text(main, height=7, font=("Arial", 10), padx=10, pady=10, relief="flat")
        self.jd_text.pack(fill="x", pady=5)

        # --- STEP 3: PERSISTENT SETTINGS ---
        settings_frame = tk.LabelFrame(main, text=" Settings (Persisted) ", bg="#f4f7f9", font=("Arial", 9, "bold"), padx=10, pady=10)
        settings_frame.pack(fill="x", pady=10)
        
        tk.Label(settings_frame, text="Salary:", bg="#f4f7f9").grid(row=0, column=0, sticky="w")
        self.salary_entry = ttk.Entry(settings_frame, width=15)
        self.salary_entry.grid(row=0, column=1, padx=10, sticky="w")

        tk.Label(settings_frame, text="Language:", bg="#f4f7f9").grid(row=0, column=2, sticky="w")
        self.lang_var = tk.StringVar(value="English")
        self.lang_combo = ttk.Combobox(settings_frame, textvariable=self.lang_var, values=["English", "German"], state="readonly", width=10)
        self.lang_combo.grid(row=0, column=3, padx=10, sticky="w")

        self.use_template_var = tk.BooleanVar(value=True)
        self.template_cb = tk.Checkbutton(settings_frame, text="Use Naming Template", variable=self.use_template_var, bg="#f4f7f9")
        self.template_cb.grid(row=1, column=0, columnspan=2, pady=(10,0), sticky="w")
        
        tk.Label(settings_frame, text="Last Name:", bg="#f4f7f9").grid(row=1, column=2, pady=(10,0), sticky="w")
        self.last_name_entry = ttk.Entry(settings_frame, width=15)
        self.last_name_entry.grid(row=1, column=3, padx=10, pady=(10,0), sticky="w")

        # --- STEP 4: GENERATE ---
        self.gen_btn = tk.Button(main, text="GENERATE PREVIEW", command=self.generate_letter, bg="#27ae60", fg="white", font=("Arial", 12, "bold"), pady=8, relief="flat")
        self.gen_btn.pack(fill="x", pady=15)

        # --- STEP 5: PREVIEW ---
        tk.Label(main, text="Review & Final Edits:", bg="#f4f7f9", font=("Arial", 10, "bold")).pack(anchor="w")
        self.output_text = tk.Text(main, height=15, font=("Times New Roman", 12), padx=40, pady=40, wrap="word", relief="flat")
        self.output_text.pack(fill="both", expand=True, pady=5)

        # --- STEP 6: EXPORT ---
        self.export_btn = tk.Button(main, text="💾 EXPORT ONE-PAGE PDF", command=self.export_to_pdf, bg="#2980b9", fg="white", font=("Arial", 12, "bold"), pady=10, relief="flat")
        self.export_btn.pack(fill="x", pady=10)

    def reset_ui(self):
        """Resets inputs but preserves salary and name settings."""
        self.cv_text = ""
        self.cv_label.config(text="No profile loaded", fg="gray")
        self.jd_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        messagebox.showinfo("Reset", "Profile and Job Description cleared. Settings preserved.")

    def upload_cv(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            doc = fitz.open(path)
            self.cv_text = "".join([page.get_text() for page in doc])
            self.cv_label.config(text=f"✅ Loaded: {os.path.basename(path)}", fg="green")

    def generate_letter(self):
        jd = self.jd_text.get("1.0", tk.END).strip()
        if not self.cv_text or not jd:
            messagebox.showwarning("Incomplete", "Please upload profile and paste JD.")
            return
        self.gen_btn.config(state="disabled", text="Drafting...")
        threading.Thread(target=self.call_mistral, args=(jd, self.salary_entry.get(), self.lang_var.get()), daemon=True).start()

    def call_mistral(self, jd, salary, lang):
        try:
            client = Mistral(api_key=self.api_key)
            sal_p = f"Mention salary expectation of {salary}." if salary else "No salary mention."
            prompt = f"""Write a professional cover letter in {lang}. 
            Data: {self.cv_text}
            Job: {jd}
            {sal_p}
            RULES: No bolding, no placeholders, no (m/w/d), no 'Notes' section. Body ~1600 chars. 
            Strict Format: Full Name, Address, Phone, Email on separate lines. Then 'Hiring Manager'. Then Subject. Then Salutation."""
            
            response = client.chat.complete(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
            text = response.choices[0].message.content
            
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            text = re.sub(r'\[.*?\]', '', text)
            lines = text.split('\n')
            final_lines = []
            for l in lines:
                if any(p in l.lower() for p in ['notes:', 'note:', 'character count:', '---']): break
                final_lines.append(l)
            
            self.root.after(0, lambda: self.show_preview("\n".join(final_lines).strip()))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("AI Error", str(e)))
        finally:
            self.root.after(0, lambda: self.gen_btn.config(state="normal", text="GENERATE PREVIEW"))

    def show_preview(self, text):
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, text)

    def export_to_pdf(self):
        text_content = self.output_text.get("1.0", tk.END).strip()
        if not text_content: return

        # Dynamic Filename logic
        initial_file = ""
        if self.use_template_var.get():
            last_name = self.last_name_entry.get().strip()
            if last_name:
                prefix = "Anschreiben_" if self.lang_var.get() == "German" else "Cover_Letter_"
                initial_file = f"{prefix}{last_name}"

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=initial_file, filetypes=[("PDF", "*.pdf")])
        if not file_path: return

        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
            styles = getSampleStyleSheet()
            
            content_len = len(text_content)
            base_size = 11 if content_len < 2200 else 10
            
            # FIXED: Added leading (vertical space) to styles to prevent overlap
            name_style = ParagraphStyle('Name', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=22, alignment=TA_CENTER, spaceAfter=4)
            contact_style = ParagraphStyle('Contact', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.grey)
            body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Times-Roman', fontSize=base_size, leading=base_size+4, alignment=TA_JUSTIFY, spaceAfter=10)
            subject_style = ParagraphStyle('Subject', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=base_size+1, leading=base_size+6, spaceBefore=15, spaceAfter=15)
            hiring_style = ParagraphStyle('Hiring', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=base_size, leading=base_size+4, spaceBefore=12)

            story = []
            lines = text_content.split('\n')
            
            # Header
            story.append(Paragraph(lines[0], name_style))
            contact_info = " | ".join([l.strip() for l in lines[1:5] if l.strip()])
            story.append(Paragraph(contact_info, contact_style))
            story.append(Spacer(1, 12)) # Gap before the line
            story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=12))

            for i, para in enumerate(lines[5:]):
                para = para.strip()
                if not para: continue
                
                if "Hiring Manager" in para:
                    story.append(Paragraph(para, hiring_style))
                elif any(s in para for s in ["Subject:", "Betreff:", "Application for"]):
                    story.append(Paragraph(para, subject_style))
                else:
                    story.append(Paragraph(para, body_style))

            doc.build(story)
            messagebox.showinfo("Success", f"PDF Saved: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = CoverLetterApp(root)
    root.mainloop()
