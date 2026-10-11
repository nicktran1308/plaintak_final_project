#!/usr/bin/env python3
"""
Generate the synthetic discharge instruction sheet as a PDF with a real text
layer, so intake.py can extract from it.

Same content as the JPG version. Entirely synthetic: invented patient,
invented MRN, invented physicians, fictitious hospital.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

W, H = letter
M = 0.9 * inch
OUT = "discharge_instructions.pdf"

c = canvas.Canvas(OUT, pagesize=letter)
c.setTitle("Patient Discharge Instructions")
y = H - M


def line(txt, font="Helvetica", size=10.5, gap=15, dx=0):
    global y
    c.setFont(font, size)
    c.drawString(M + dx, y, txt)
    y -= gap


def rule(gap=10):
    global y
    c.setStrokeColorRGB(0.72, 0.72, 0.72)
    c.setLineWidth(0.7)
    c.line(M, y, W - M, y)
    y -= gap


def section(title):
    global y
    y -= 8
    line(title, "Helvetica-Bold", 12, 15)
    rule(12)


def wrap(txt, font="Helvetica", size=10.5, dx=0, width=None, gap=14):
    """Wrap to the page width, drawing each line separately."""
    global y
    from reportlab.pdfbase.pdfmetrics import stringWidth
    limit = width or (W - 2 * M - dx)
    words, cur = txt.split(), ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if stringWidth(trial, font, size) > limit:
            line(cur, font, size, gap, dx)
            cur = w
        else:
            cur = trial
    if cur:
        line(cur, font, size, gap, dx)


# ---------------- letterhead ----------------
line("VALLEY GENERAL MEDICAL CENTER", "Helvetica-Bold", 17, 20)
line("Department of Internal Medicine  |  1420 Harbor Blvd, Fullerton, CA 92831  |  (714) 555-0180",
     "Helvetica", 8, 16)
c.setStrokeColorRGB(0.1, 0.1, 0.1)
c.setLineWidth(1.6)
c.line(M, y, W - M, y)
y -= 22

line("PATIENT DISCHARGE INSTRUCTIONS", "Helvetica-Bold", 13, 22)

# ---------------- patient block ----------------
for a, b, cc, d in [
    ("Patient:", "NGUYEN, HUONG T.", "MRN:", "004-88-2317"),
    ("DOB:", "03/14/1955  (Age 71)", "Attending:", "R. Kaplan, MD"),
    ("Admitted:", "11/05/2026", "Discharged:", "11/08/2026 14:20"),
]:
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(M, y, a)
    c.drawString(M + 3.3 * inch, y, cc)
    c.setFont("Helvetica", 9.5)
    c.drawString(M + 0.85 * inch, y, b)
    c.drawString(M + 4.25 * inch, y, d)
    y -= 14
y -= 8

# ---------------- content ----------------
section("DISCHARGE DIAGNOSIS")
wrap("Primary: Acute kidney injury (AKI), Stage 2, secondary to volume depletion, "
     "superimposed on Stage 3a chronic kidney disease. Secondary: Type 2 diabetes "
     "mellitus with diabetic nephropathy; essential hypertension.")

section("MEDICATION INSTRUCTIONS")
for item in [
    "1. HOLD metformin 500 mg PO BID until you follow up with nephrology on 11/14. Do not resume unless instructed by the nephrology service.",
    "2. HOLD lisinopril 20 mg PO daily pending repeat basic metabolic panel. Resumption is contingent upon creatinine normalization.",
    "3. CONTINUE atorvastatin 40 mg PO QHS without interruption.",
    "4. CONTINUE insulin glargine 18 units subcutaneously QHS. Monitor capillary blood glucose TID and prior to bedtime.",
    "5. Avoid all NSAIDs, including ibuprofen and naproxen, as these agents are nephrotoxic and may precipitate recurrent renal injury.",
]:
    wrap(item, dx=12, width=W - 2 * M - 12)
    y -= 4

section("ACTIVITY AND DIET")
wrap("Ambulate as tolerated. Avoid strenuous exertion for 7 days. Adhere to a "
     "sodium-restricted diet (less than 2 g/day) and maintain adequate oral "
     "hydration, approximately 1.5 to 2 L daily unless otherwise directed. "
     "Restrict dietary potassium pending repeat electrolyte assessment.")

section("FOLLOW-UP APPOINTMENTS")
wrap("Nephrology, Dr. S. Almeida, 11/14/2026 at 9:30 AM, Suite 240. Obtain basic "
     "metabolic panel 48 hours prior to this appointment.")
y -= 4
wrap("Primary Care, Dr. R. Kaplan, 11/21/2026 at 2:00 PM.")

section("RETURN TO THE EMERGENCY DEPARTMENT IF YOU EXPERIENCE")
wrap("Decreased urine output or anuria; new or worsening lower-extremity edema; "
     "dyspnea or orthopnea; persistent nausea and emesis precluding oral intake; "
     "confusion or altered mental status; or capillary blood glucose readings "
     "persistently below 70 mg/dL or above 300 mg/dL.")

y -= 14
rule(16)
line("I have received and understand these instructions.", "Helvetica", 9.5, 30)
c.setStrokeColorRGB(0.1, 0.1, 0.1)
c.setLineWidth(1)
c.line(M, y, M + 2.6 * inch, y)
c.line(M + 3.3 * inch, y, M + 5.4 * inch, y)
y -= 11
line("Patient / Representative signature", "Helvetica", 7.5, 0)
c.setFont("Helvetica", 7.5)
c.drawString(M + 3.3 * inch, y, "Date")

c.setFont("Helvetica", 7.5)
c.setFillColorRGB(0.6, 0.6, 0.6)
c.drawString(M, 0.55 * inch, "Synthetic example document. Not a real patient record.")
c.drawRightString(W - M, 0.55 * inch, "Page 1 of 1")

c.save()
print("wrote", OUT)
