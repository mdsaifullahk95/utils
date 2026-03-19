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
        self.root.geometry("850x950")
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
        
        tk.Label(main, text="Professional Cover Letter Designer", font=("Helvetica", 20, "bold"), bg="#f4f7f9").pack(pady=10)

        # 1. Profile Upload
        self.upload_btn = tk.Button(main, text="1. Upload Profile (PDF)", command=self.upload_cv, bg="#bdc3c7", relief="flat", font=("Arial", 10, "bold"))
        self.upload_btn.pack(fill="x", pady=5)
        self.cv_label = tk.Label(main, text="No profile loaded", fg="gray", bg="#f4f7f9")
        self.cv_label.pack()

        # 2. JD Input
        tk.Label(main, text="2. Paste Job Description:", bg="#f4f7f9", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
        self.jd_text = tk.Text(main, height=8, font=("Arial", 10), padx=10, pady=10, relief="flat")
        self.jd_text.pack(fill="x", pady=5)

        # 3. Settings
        ctrls = tk.Frame(main, bg="#f4f7f9")
        ctrls.pack(fill="x", pady=10)
        tk.Label(ctrls, text="Salary:", bg="#f4f7f9").pack(side="left")
        self.salary_entry = ttk.Entry(ctrls, width=15)
        self.salary_entry.pack(side="left", padx=10)
        tk.Label(ctrls, text="Language:", bg="#f4f7f9").pack(side="left", padx=(10,0))
        self.lang_var = tk.StringVar(value="English")
        self.lang_combo = ttk.Combobox(ctrls, textvariable=self.lang_var, values=["English", "German"], state="readonly", width=10)
        self.lang_combo.pack(side="left", padx=10)

        # 4. Generate
        self.gen_btn = tk.Button(main, text="GENERATE PREVIEW", command=self.generate_letter, bg="#27ae60", fg="white", font=("Arial", 12, "bold"), pady=8, relief="flat")
        self.gen_btn.pack(fill="x", pady=10)

        # 5. Result/Preview
        tk.Label(main, text="Review & Final Edits:", bg="#f4f7f9", font=("Arial", 10, "bold")).pack(anchor="w")
        self.output_text = tk.Text(main, height=18, font=("Times New Roman", 12), padx=40, pady=40, wrap="word", relief="flat")
        self.output_text.pack(fill="both", expand=True, pady=5)

        # 6. Export
        self.export_btn = tk.Button(main, text="💾 EXPORT ONE-PAGE PDF", command=self.export_to_pdf, bg="#2980b9", fg="white", font=("Arial", 12, "bold"), pady=10, relief="flat")
        self.export_btn.pack(fill="x", pady=10)

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
            RULES: No bolding, no placeholders, no (m/w/d), no 'Notes' section. Body ~1600 characters. 
            Format: Start with My Name, Address, Phone, Email. Then 'Hiring Manager'. Then Subject. Then Salutation."""
            
            response = client.chat.complete(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
            text = response.choices[0].message.content
            
            # Cleaning logic
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
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not file_path: return

        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
            styles = getSampleStyleSheet()
            
            # Dynamic Font Size logic
            content_len = len(text_content)
            base_size = 11 if content_len < 2200 else 10
            
            # Styles
            name_style = ParagraphStyle('Name', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=2)
            contact_style = ParagraphStyle('Contact', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11, alignment=TA_CENTER, textColor=colors.grey)
            body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Times-Roman', fontSize=base_size, leading=base_size+3, alignment=TA_JUSTIFY, spaceAfter=10)
            subject_style = ParagraphStyle('Subject', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=base_size+1, leading=base_size+5, spaceBefore=15, spaceAfter=15)
            hiring_style = ParagraphStyle('Hiring', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=base_size, leading=base_size+3, spaceBefore=10)

            story = []
            lines = text_content.split('\n')
            
            # Modern Header
            story.append(Paragraph(lines[0], name_style)) # Your Name
            contact_info = " | ".join([l.strip() for l in lines[1:5] if l.strip()])
            story.append(Paragraph(contact_info, contact_style))
            story.append(Spacer(1, 10))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=2, spaceAfter=10))

            # Remaining Content
            for i, para in enumerate(lines[5:]):
                para = para.strip()
                if not para: continue
                
                if "Hiring Manager" in para:
                    story.append(Paragraph(para, hiring_style))
                elif any(s in para for s in ["Subject:", "Betreff:", "Application for"]):
                    story.append(Paragraph(para, subject_style))
                elif any(s in para for s in ["Dear", "Sehr geehrte", "Yours", "Best regards", "Sincerely"]):
                    story.append(Paragraph(para, body_style))
                else:
                    story.append(Paragraph(para, body_style))

            doc.build(story)
            messagebox.showinfo("Success", f"Professional One-Page PDF Created! (Font: {base_size}pt)")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = CoverLetterApp(root)
    root.mainloop()
