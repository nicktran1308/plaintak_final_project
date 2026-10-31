#!/usr/bin/env python3
"""
Generate synthetic discharge sheets as PDFs with a real text layer.

Sheet 00 is the original evaluation document. Eighteen further sheets vary
drugs, doses, dates, ranges, and negations. Every name, MRN, and hospital
is invented. Nothing here is a real patient record.

The original file path stays eval/synthetic_docs/discharge_instructions.pdf
so the existing eval harnesses keep working. The full set is written to
eval/synthetic_docs/sheets/ with a manifest of the facts each sheet contains.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
SHEET_DIR = HERE / "sheets"
W, H = letter
M = 0.9 * inch

# The sheet the published evaluations used. Do not edit its sentences.
ORIGINAL = {
    "id": "sheet_00_aki",
    "file": "discharge_instructions.pdf",
    "hospital": "VALLEY GENERAL MEDICAL CENTER",
    "dept_line": "Department of Internal Medicine  |  1420 Harbor Blvd, Fullerton, CA 92831  |  (714) 555-0180",
    "patient": "NGUYEN, HUONG T.",
    "mrn": "004-88-2317",
    "dob": "03/14/1955  (Age 71)",
    "attending": "R. Kaplan, MD",
    "admitted": "11/05/2026",
    "discharged": "11/08/2026 14:20",
    "diagnosis": (
        "Primary: Acute kidney injury (AKI), Stage 2, secondary to volume depletion, "
        "superimposed on Stage 3a chronic kidney disease. Secondary: Type 2 diabetes "
        "mellitus with diabetic nephropathy; essential hypertension."
    ),
    "meds": [
        "1. HOLD metformin 500 mg PO BID until you follow up with nephrology on 11/14. Do not resume unless instructed by the nephrology service.",
        "2. HOLD lisinopril 20 mg PO daily pending repeat basic metabolic panel. Resumption is contingent upon creatinine normalization.",
        "3. CONTINUE atorvastatin 40 mg PO QHS without interruption.",
        "4. CONTINUE insulin glargine 18 units subcutaneously QHS. Monitor capillary blood glucose TID and prior to bedtime.",
        "5. Avoid all NSAIDs, including ibuprofen and naproxen, as these agents are nephrotoxic and may precipitate recurrent renal injury.",
    ],
    "activity": (
        "Ambulate as tolerated. Avoid strenuous exertion for 7 days. Adhere to a "
        "sodium-restricted diet (less than 2 g/day) and maintain adequate oral "
        "hydration, approximately 1.5 to 2 L daily unless otherwise directed. "
        "Restrict dietary potassium pending repeat electrolyte assessment."
    ),
    "followups": [
        "Nephrology, Dr. S. Almeida, 11/14/2026 at 9:30 AM, Suite 240. Obtain basic metabolic panel 48 hours prior to this appointment.",
        "Primary Care, Dr. R. Kaplan, 11/21/2026 at 2:00 PM.",
    ],
    "emergency": (
        "Decreased urine output or anuria; new or worsening lower-extremity edema; "
        "dyspnea or orthopnea; persistent nausea and emesis precluding oral intake; "
        "confusion or altered mental status; or capillary blood glucose readings "
        "persistently below 70 mg/dL or above 300 mg/dL."
    ),
}


def _sheet(**kwargs):
    """Fill the shared letterhead fields for one invented hospital stay."""
    kwargs.setdefault("dept_line", kwargs.pop("dept"))
    return kwargs


SHEETS = [
    ORIGINAL,
    _sheet(
        id="sheet_01_warfarin",
        file="sheets/sheet_01_warfarin.pdf",
        hospital="HARBOR VIEW COMMUNITY HOSPITAL",
        dept="Cardiology  |  800 Ocean Ave, Long Beach, CA 90802  |  (562) 555-0142",
        patient="TRAN, MINH D.", mrn="100-22-4401",
        dob="06/02/1948  (Age 78)", attending="L. Ortega, MD",
        admitted="03/02/2026", discharged="03/06/2026 09:10",
        diagnosis="Primary: Atrial fibrillation with rapid ventricular response, now rate controlled. Secondary: Heart failure with preserved ejection fraction.",
        meds=[
            "1. HOLD warfarin 5 mg PO daily until your INR is checked on 03/12. Do not resume unless the anticoagulation clinic instructs you.",
            "2. CONTINUE metoprolol tartrate 25 mg PO BID without interruption.",
            "3. CONTINUE furosemide 40 mg PO daily. Do not double the dose if you miss one.",
            "4. Avoid ibuprofen and naproxen while warfarin is held.",
        ],
        activity="Walk as tolerated. Do not lift more than 10 pounds for 14 days. Limit fluids to 1 to 1.5 L daily unless the heart clinic directs otherwise.",
        followups=[
            "Anticoagulation clinic, 03/12/2026 at 8:15 AM. Have the INR drawn that morning.",
            "Cardiology, Dr. L. Ortega, 03/20/2026 at 1:30 PM.",
        ],
        emergency="Bleeding that does not stop, black stools, chest pain, or new shortness of breath. Call if your weight rises by more than 2 pounds in one day.",
    ),
    _sheet(
        id="sheet_02_amoxicillin",
        file="sheets/sheet_02_amoxicillin.pdf",
        hospital="CEDAR STREET MEDICAL CENTER",
        dept="Infectious Diseases  |  15 Cedar St, Santa Ana, CA 92701  |  (714) 555-0166",
        patient="PHAM, LAN K.", mrn="220-18-9033",
        dob="09/19/1962  (Age 63)", attending="A. Brooks, MD",
        admitted="04/01/2026", discharged="04/03/2026 16:40",
        diagnosis="Primary: Community-acquired pneumonia, clinical improvement on antibiotics. Secondary: Type 2 diabetes mellitus.",
        meds=[
            "1. CONTINUE amoxicillin 875 mg PO BID for 7 days. Do not stop early even if you feel better.",
            "2. HOLD metformin 1000 mg PO BID until you follow up on 04/10. Do not resume unless your primary doctor instructs you.",
            "3. CONTINUE lisinopril 10 mg PO daily.",
            "4. Avoid alcohol until the antibiotic course is finished.",
        ],
        activity="Rest for 3 days, then walk as tolerated. Drink 2 to 3 L of water daily unless you are told to limit fluids. Do not return to work until 04/10.",
        followups=[
            "Primary care, Dr. A. Brooks, 04/10/2026 at 10:00 AM.",
            "Chest x-ray, 04/24/2026 at 9:00 AM.",
        ],
        emergency="Fever above 101 degrees, oxygen trouble, chest pain, or blood sugar below 70 mg/dL or above 300 mg/dL.",
    ),
    _sheet(
        id="sheet_03_levothyroxine",
        file="sheets/sheet_03_levothyroxine.pdf",
        hospital="NORTH PARK CLINIC HOSPITAL",
        dept="Endocrinology  |  410 Park Ave, Pasadena, CA 91101  |  (626) 555-0190",
        patient="CHO, HELEN S.", mrn="331-44-1180",
        dob="01/28/1970  (Age 56)", attending="P. Shah, MD",
        admitted="05/11/2026", discharged="05/12/2026 11:05",
        diagnosis="Primary: Hypothyroidism with medication adjustment after a low free T4. Secondary: Gastroesophageal reflux.",
        meds=[
            "1. CONTINUE levothyroxine 88 mcg PO once daily on an empty stomach. Do not take it with calcium or iron.",
            "2. HOLD calcium carbonate 500 mg PO BID until 05/18.",
            "3. CONTINUE pantoprazole 40 mg PO daily before breakfast.",
            "4. Do not double a missed levothyroxine dose.",
        ],
        activity="Usual activity. Wait 30 to 60 minutes after levothyroxine before eating. Drink 1 to 1.5 L of water daily. Avoid taking the calcium tablets until the clinic restarts them.",
        followups=[
            "Endocrinology, Dr. P. Shah, 05/18/2026 at 3:45 PM. Thyroid labs are due that morning.",
            "Primary care, 06/15/2026 at 8:30 AM.",
        ],
        emergency="Severe palpitations, chest pain, or confusion. A pulse persistently above 120 beats per minute should be seen the same day.",
    ),
    _sheet(
        id="sheet_04_heart_failure",
        file="sheets/sheet_04_heart_failure.pdf",
        hospital="RIVERBEND GENERAL HOSPITAL",
        dept="Heart Failure  |  90 River Rd, Riverside, CA 92501  |  (951) 555-0177",
        patient="DIAZ, CARLOS M.", mrn="448-02-7761",
        dob="12/04/1951  (Age 74)", attending="N. Okonkwo, MD",
        admitted="06/01/2026", discharged="06/05/2026 13:25",
        diagnosis="Primary: Acute decompensated heart failure, improved with diuresis. Secondary: Chronic kidney disease, stage 3.",
        meds=[
            "1. HOLD carvedilol 6.25 mg PO BID until you are seen on 06/09. Do not resume unless cardiology instructs you.",
            "2. CONTINUE furosemide 40 mg PO daily. Do not skip a dose.",
            "3. CONTINUE spironolactone 25 mg PO daily.",
            "4. Avoid salt and do not add salt at the table.",
        ],
        activity="Weigh yourself every morning. Call if you gain more than 3 pounds in 2 days. Limit fluids to 1.2 to 1.8 L daily. Do not do strenuous exertion for 10 days.",
        followups=[
            "Heart failure clinic, Dr. N. Okonkwo, 06/09/2026 at 11:20 AM.",
            "Basic metabolic panel, 06/08/2026 at 7:40 AM.",
        ],
        emergency="Sudden shortness of breath, chest pain, fainting, or swelling that returns in one day.",
    ),
    _sheet(
        id="sheet_05_insulin",
        file="sheets/sheet_05_insulin.pdf",
        hospital="WESTSIDE COMMUNITY HOSPITAL",
        dept="Diabetes  |  2200 West Blvd, Anaheim, CA 92801  |  (714) 555-0133",
        patient="NGUYEN, THAO P.", mrn="512-77-3008",
        dob="04/14/1959  (Age 67)", attending="R. Kaplan, MD",
        admitted="07/02/2026", discharged="07/04/2026 15:00",
        diagnosis="Primary: Hyperglycemia without ketoacidosis, now improved. Secondary: Type 2 diabetes mellitus and hypertension.",
        meds=[
            "1. HOLD insulin glargine 24 units subcutaneously QHS until 07/11. Do not resume unless the diabetes clinic instructs you.",
            "2. CONTINUE metformin 1000 mg PO BID with food.",
            "3. CONTINUE lisinopril 20 mg PO daily.",
            "4. Do not double a missed insulin dose. If you miss a dose, skip it.",
        ],
        activity="Check blood sugar before meals and at bedtime. Usual walking is allowed. Drink 1.5 to 2 L daily unless your doctor limits fluids. Do not drive if a reading is below 70 mg/dL.",
        followups=[
            "Diabetes clinic, 07/11/2026 at 9:50 AM.",
            "Primary care, Dr. R. Kaplan, 07/18/2026 at 2:10 PM.",
        ],
        emergency="Blood sugar below 70 mg/dL that does not rise with juice, or blood sugar above 300 mg/dL, or vomiting that prevents you from drinking.",
    ),
    _sheet(
        id="sheet_06_pain",
        file="sheets/sheet_06_pain.pdf",
        hospital="FOOTHILL MEMORIAL HOSPITAL",
        dept="Orthopedics  |  75 Hill St, Pomona, CA 91766  |  (909) 555-0188",
        patient="SINGH, RAJIV K.", mrn="623-15-8842",
        dob="08/30/1980  (Age 45)", attending="M. Adler, MD",
        admitted="08/08/2026", discharged="08/09/2026 18:30",
        diagnosis="Primary: Right ankle fracture, closed, splinted. Secondary: No chronic medications on admission.",
        meds=[
            "1. CONTINUE acetaminophen 650 mg PO every 6 hours as needed for pain. Do not exceed 3000 mg in one day.",
            "2. Avoid ibuprofen 200 mg and naproxen. Do not take any NSAID.",
            "3. HOLD oxycodone 5 mg PO every 6 hours after 08/12. Do not resume it.",
            "4. CONTINUE a stool softener if you are still taking oxycodone.",
        ],
        activity="Keep the splint on. Do not bear weight on the right leg for 14 days. Elevate the leg. Drink 2 to 2.5 L of water daily.",
        followups=[
            "Orthopedics, Dr. M. Adler, 08/16/2026 at 8:00 AM.",
            "Wound check, 08/12/2026 at 4:20 PM.",
        ],
        emergency="Toes that turn blue or numb, pain not relieved by the prescribed dose, or a fever above 101 degrees.",
    ),
    _sheet(
        id="sheet_07_asthma",
        file="sheets/sheet_07_asthma.pdf",
        hospital="BAYSIDE GENERAL HOSPITAL",
        dept="Pulmonary  |  500 Bay St, Huntington Beach, CA 92648  |  (714) 555-0119",
        patient="LE, MAI T.", mrn="734-90-2217",
        dob="02/11/1992  (Age 34)", attending="S. Rahman, MD",
        admitted="08/28/2026", discharged="08/30/2026 12:15",
        diagnosis="Primary: Asthma exacerbation, improved after steroids and bronchodilators. Secondary: Seasonal allergies.",
        meds=[
            "1. CONTINUE albuterol 2 puffs every 6 hours for 5 days, then as needed. Do not exceed 12 puffs in one day.",
            "2. CONTINUE prednisone 40 mg PO daily for 5 days. Do not stop early.",
            "3. HOLD propranolol 10 mg PO BID. Do not resume unless cardiology instructs you.",
            "4. CONTINUE fluticasone 2 puffs inhaled BID.",
        ],
        activity="Avoid smoke and heavy exercise for 7 days. Walk indoors as tolerated. Drink 2 to 3 L daily if you are not fluid restricted.",
        followups=[
            "Pulmonary, Dr. S. Rahman, 09/04/2026 at 10:40 AM.",
            "Primary care, 09/18/2026 at 3:00 PM.",
        ],
        emergency="Trouble breathing that does not improve after 2 puffs, blue lips, or chest pain.",
    ),
    _sheet(
        id="sheet_08_apixaban",
        file="sheets/sheet_08_apixaban.pdf",
        hospital="SUMMIT VALLEY HOSPITAL",
        dept="Neurology  |  12 Summit Dr, Irvine, CA 92612  |  (949) 555-0155",
        patient="KIM, SOO J.", mrn="845-33-6704",
        dob="11/07/1944  (Age 81)", attending="H. Feldman, MD",
        admitted="09/14/2026", discharged="09/18/2026 10:55",
        diagnosis="Primary: Ischemic stroke, small vessel, no thrombolysis. Secondary: Atrial fibrillation.",
        meds=[
            "1. CONTINUE apixaban 5 mg PO BID. Do not skip a dose. Do not double the next dose if one is missed.",
            "2. HOLD aspirin 81 mg PO daily. Do not resume unless neurology instructs you.",
            "3. CONTINUE atorvastatin 40 mg PO QHS.",
            "4. Avoid ibuprofen and naproxen.",
        ],
        activity="Speech and walking therapy as scheduled. Do not drive until 10/02. Limit added salt. Drink 1 to 1.5 L daily unless told otherwise.",
        followups=[
            "Neurology, Dr. H. Feldman, 09/28/2026 at 2:45 PM.",
            "Cardiology, 10/06/2026 at 9:15 AM.",
        ],
        emergency="Sudden weakness, facial droop, trouble speaking, severe headache, or bleeding that will not stop.",
    ),
    _sheet(
        id="sheet_09_digoxin",
        file="sheets/sheet_09_digoxin.pdf",
        hospital="LAKEVIEW MEDICAL CENTER",
        dept="Internal Medicine  |  300 Lake Ave, Lakewood, CA 90712  |  (562) 555-0108",
        patient="BROWN, ELLEN R.", mrn="956-21-4488",
        dob="05/23/1939  (Age 87)", attending="J. Petrova, MD",
        admitted="09/27/2026", discharged="10/01/2026 14:05",
        diagnosis="Primary: Digoxin toxicity, resolved after the drug was held. Secondary: Heart failure with reduced ejection fraction.",
        meds=[
            "1. HOLD digoxin 125 mcg PO daily until the level is checked on 10/03. Do not resume unless cardiology instructs you.",
            "2. CONTINUE furosemide 20 mg PO daily. Do not skip a dose.",
            "3. CONTINUE carvedilol 3.125 mg PO BID.",
            "4. Avoid antacids within 2 hours of your other morning pills.",
        ],
        activity="Rest at home for 5 days. Weigh daily. Do not drink more than 1.2 to 1.8 L of fluid a day. Call for a gain of 3 pounds in 2 days.",
        followups=[
            "Digoxin level and basic metabolic panel, 10/03/2026 at 7:30 AM.",
            "Cardiology, Dr. J. Petrova, 10/10/2026 at 11:00 AM.",
        ],
        emergency="Yellow vision, severe nausea, a very slow pulse, fainting, or chest pain.",
    ),
    _sheet(
        id="sheet_10_seizure",
        file="sheets/sheet_10_seizure.pdf",
        hospital="PACIFIC GROVE HOSPITAL",
        dept="Neurology  |  88 Grove Ln, Costa Mesa, CA 92626  |  (714) 555-0194",
        patient="GARCIA, LUIS A.", mrn="167-58-9022",
        dob="07/16/1988  (Age 38)", attending="C. Nguyen, MD",
        admitted="01/08/2027", discharged="01/09/2027 17:20",
        diagnosis="Primary: Breakthrough seizure in a patient with known epilepsy, back to baseline. Secondary: Insomnia.",
        meds=[
            "1. CONTINUE levetiracetam 500 mg PO BID. Do not stop taking this medicine.",
            "2. HOLD lorazepam 0.5 mg PO QHS after 01/12. Do not resume it.",
            "3. Do not skip a levetiracetam dose. If you miss one, do not double the next dose.",
            "4. Avoid alcohol.",
        ],
        activity="Do not drive until 04/09. Do not swim alone. Sleep regular hours. Drink 2 to 3 L of water daily.",
        followups=[
            "Neurology, Dr. C. Nguyen, 01/22/2027 at 1:15 PM.",
            "Primary care, 02/05/2027 at 9:40 AM.",
        ],
        emergency="Another seizure, a seizure lasting more than 2 minutes, or trouble breathing.",
    ),
    _sheet(
        id="sheet_11_gout",
        file="sheets/sheet_11_gout.pdf",
        hospital="ORANGE GROVE HOSPITAL",
        dept="Rheumatology  |  640 Grove St, Orange, CA 92868  |  (714) 555-0127",
        patient="WU, PETER L.", mrn="278-64-1155",
        dob="03/03/1955  (Age 71)", attending="E. Marsh, MD",
        admitted="01/20/2027", discharged="01/21/2027 13:10",
        diagnosis="Primary: Acute gout flare of the left great toe, improving. Secondary: Chronic kidney disease, stage 3a.",
        meds=[
            "1. HOLD allopurinol 100 mg PO daily until 02/02. Do not resume unless rheumatology instructs you.",
            "2. CONTINUE colchicine 0.6 mg PO daily for 7 days. Do not take an extra tablet for pain.",
            "3. Avoid naproxen and ibuprofen.",
            "4. CONTINUE acetaminophen 500 mg PO every 6 hours as needed. Do not exceed 3000 mg in one day.",
        ],
        activity="Rest the foot for 3 days. Drink 2 to 3 L of water daily unless nephrology has limited your fluids. Do not drink beer.",
        followups=[
            "Rheumatology, Dr. E. Marsh, 02/02/2027 at 8:50 AM.",
            "Nephrology labs, 01/30/2027 at 7:15 AM.",
        ],
        emergency="A red hot joint with fever, vomiting, or no urine for 12 hours.",
    ),
    _sheet(
        id="sheet_12_copd",
        file="sheets/sheet_12_copd.pdf",
        hospital="MESA RIDGE HOSPITAL",
        dept="Pulmonary  |  19 Mesa Rd, Santa Ana, CA 92705  |  (714) 555-0171",
        patient="JOHNSON, RUTH E.", mrn="389-41-6620",
        dob="10/29/1946  (Age 79)", attending="D. Alvarez, MD",
        admitted="02/10/2027", discharged="02/14/2027 11:45",
        diagnosis="Primary: COPD exacerbation, improved on steroids and nebulizers. Secondary: Former tobacco use, quit.",
        meds=[
            "1. CONTINUE prednisone 20 mg PO daily for 5 days. Do not stop early.",
            "2. CONTINUE tiotropium 1 capsule inhaled once daily. Do not swallow the capsule.",
            "3. CONTINUE albuterol 2 puffs every 6 hours as needed. Do not exceed 8 puffs in one day.",
            "4. HOLD metoprolol succinate 50 mg PO daily until 02/18. Do not resume unless cardiology instructs you.",
        ],
        activity="Avoid smoke and dust. Walk short distances. Do not do strenuous exertion for 7 days. Drink 1.5 to 2 L daily if you are not fluid restricted.",
        followups=[
            "Pulmonary, Dr. D. Alvarez, 02/18/2027 at 2:30 PM.",
            "Primary care, 03/04/2027 at 10:10 AM.",
        ],
        emergency="Breathing that is worse after 2 puffs, chest pain, or confusion.",
    ),
    _sheet(
        id="sheet_13_cephalexin",
        file="sheets/sheet_13_cephalexin.pdf",
        hospital="EASTSIDE COMMUNITY HOSPITAL",
        dept="General Surgery  |  1500 East First St, Santa Ana, CA 92701  |  (714) 555-0148",
        patient="PATEL, ANITA R.", mrn="490-12-3386",
        dob="06/21/1975  (Age 51)", attending="K. Ito, MD",
        admitted="02/24/2027", discharged="02/26/2027 09:35",
        diagnosis="Primary: Cellulitis of the left lower leg, improving on antibiotics. Secondary: Type 2 diabetes mellitus.",
        meds=[
            "1. CONTINUE cephalexin 500 mg PO every 6 hours for 10 days. Do not skip a dose. Do not stop early.",
            "2. HOLD metformin 500 mg PO BID until 03/01. Do not resume unless your doctor instructs you.",
            "3. CONTINUE atorvastatin 20 mg PO QHS.",
            "4. Avoid soaking the leg. Keep the dressing dry.",
        ],
        activity="Elevate the leg. Walk short distances. Do not stand for long periods for 7 days. Drink 2 to 3 L of water daily.",
        followups=[
            "Surgery clinic, Dr. K. Ito, 03/01/2027 at 8:20 AM.",
            "Primary care, 03/08/2027 at 4:00 PM.",
        ],
        emergency="Redness that spreads, fever above 101 degrees, or blood sugar below 70 mg/dL or above 250 mg/dL.",
    ),
    _sheet(
        id="sheet_14_amlodipine",
        file="sheets/sheet_14_amlodipine.pdf",
        hospital="CENTRAL VALLEY HOSPITAL",
        dept="Internal Medicine  |  42 Center St, Garden Grove, CA 92840  |  (714) 555-0160",
        patient="NGUYEN, DUC H.", mrn="501-83-2294",
        dob="09/09/1958  (Age 67)", attending="B. Cohen, MD",
        admitted="03/28/2027", discharged="03/31/2027 16:10",
        diagnosis="Primary: Hypertensive urgency, now controlled. Secondary: Gout, quiescent.",
        meds=[
            "1. CONTINUE amlodipine 5 mg PO daily. Do not skip a dose.",
            "2. HOLD hydrochlorothiazide 25 mg PO daily until 04/08. Do not resume unless instructed.",
            "3. CONTINUE allopurinol 300 mg PO daily.",
            "4. Avoid ibuprofen.",
        ],
        activity="Check your blood pressure each morning. Usual activity. Limit salt. Drink 0.8 to 1.2 L daily unless you feel dizzy, in which case sit down and call.",
        followups=[
            "Primary care, Dr. B. Cohen, 04/08/2027 at 9:05 AM.",
            "Basic metabolic panel, 04/07/2027 at 7:50 AM.",
        ],
        emergency="Chest pain, shortness of breath, fainting, or a blood pressure reading above 180 systolic.",
    ),
    _sheet(
        id="sheet_15_pantoprazole",
        file="sheets/sheet_15_pantoprazole.pdf",
        hospital="HILLCREST GENERAL HOSPITAL",
        dept="Gastroenterology  |  9 Hillcrest Dr, Fullerton, CA 92832  |  (714) 555-0184",
        patient="MARTINEZ, ROSA L.", mrn="612-47-5501",
        dob="12/12/1966  (Age 59)", attending="F. Haddad, MD",
        admitted="04/19/2027", discharged="04/21/2027 12:40",
        diagnosis="Primary: Upper gastrointestinal bleed, resolved, no further bleeding. Secondary: Osteoarthritis.",
        meds=[
            "1. CONTINUE pantoprazole 40 mg PO daily before breakfast for 8 weeks. Do not stop early.",
            "2. HOLD ibuprofen 400 mg. Do not resume any NSAID.",
            "3. HOLD aspirin 81 mg PO daily. Do not resume unless cardiology instructs you.",
            "4. CONTINUE acetaminophen 650 mg PO every 8 hours as needed. Do not exceed 3000 mg in one day.",
        ],
        activity="Eat small meals. Avoid alcohol for 14 days. Do not lift more than 15 pounds for 7 days. Drink 1.5 to 2 L daily.",
        followups=[
            "Gastroenterology, Dr. F. Haddad, 05/06/2027 at 1:40 PM.",
            "Primary care, 05/12/2027 at 11:30 AM.",
        ],
        emergency="Black stools, vomiting blood, dizziness when standing, or chest pain.",
    ),
    _sheet(
        id="sheet_16_glipizide",
        file="sheets/sheet_16_glipizide.pdf",
        hospital="SOUTH COUNTY HOSPITAL",
        dept="Endocrinology  |  700 South St, Mission Viejo, CA 92691  |  (949) 555-0138",
        patient="CHEN, WEI M.", mrn="723-09-4416",
        dob="08/08/1952  (Age 74)", attending="P. Shah, MD",
        admitted="06/06/2027", discharged="06/08/2027 10:20",
        diagnosis="Primary: Hypoglycemia in a patient taking glipizide, resolved. Secondary: Hyperlipidemia.",
        meds=[
            "1. HOLD glipizide 5 mg PO BID until 06/12. Do not resume unless the diabetes clinic instructs you.",
            "2. CONTINUE metformin 500 mg PO BID with meals.",
            "3. CONTINUE atorvastatin 80 mg PO QHS. Do not skip a dose.",
            "4. Do not double a missed dose of any of these medicines.",
        ],
        activity="Check blood sugar before breakfast and at bedtime. Eat on a regular schedule. Do not drive if a reading is below 80 mg/dL. Drink 2 to 2.5 L daily.",
        followups=[
            "Diabetes clinic, Dr. P. Shah, 06/12/2027 at 8:10 AM.",
            "Primary care, 06/26/2027 at 3:20 PM.",
        ],
        emergency="Blood sugar below 70 mg/dL with sweating or confusion, or blood sugar above 300 mg/dL.",
    ),
    _sheet(
        id="sheet_17_calcium",
        file="sheets/sheet_17_calcium.pdf",
        hospital="MIDTOWN COMMUNITY HOSPITAL",
        dept="Endocrinology  |  18 Midtown Ave, Whittier, CA 90602  |  (562) 555-0199",
        patient="ALI, FATIMA N.", mrn="834-70-1288",
        dob="04/02/1979  (Age 48)", attending="G. Bernstein, MD",
        admitted="07/13/2027", discharged="07/14/2027 15:55",
        diagnosis="Primary: Hypocalcemia after thyroid surgery, improving on supplements. Secondary: Hypothyroidism on replacement.",
        meds=[
            "1. CONTINUE levothyroxine 112 mcg PO once daily. Do not take it with the calcium tablets.",
            "2. CONTINUE calcium carbonate 1000 mg PO TID with meals.",
            "3. CONTINUE calcitriol 0.25 mcg PO daily.",
            "4. Wait at least 4 hours after levothyroxine before a calcium dose. Do not skip the calcium.",
        ],
        activity="Usual activity. The neck incision should stay dry for 2 days. Avoid heavy lifting for 7 days. Drink 2 to 3 L daily.",
        followups=[
            "Calcium and thyroid labs, 07/16/2027 at 7:20 AM.",
            "Endocrinology, Dr. G. Bernstein, 07/20/2027 at 2:00 PM.",
        ],
        emergency="Face or hand tingling that is severe, muscle cramps you cannot stop, trouble breathing, or neck swelling.",
    ),
    _sheet(
        id="sheet_18_enoxaparin",
        file="sheets/sheet_18_enoxaparin.pdf",
        hospital="WEST COUNTY HOSPITAL",
        dept="Hematology  |  260 County Rd, Buena Park, CA 90621  |  (714) 555-0122",
        patient="SMITH, JAMES P.", mrn="945-36-8077",
        dob="01/15/1960  (Age 67)", attending="L. Ortega, MD",
        admitted="08/01/2027", discharged="08/06/2027 13:30",
        diagnosis="Primary: Acute deep vein thrombosis of the left leg. Secondary: Obesity. No surgery was performed.",
        meds=[
            "1. CONTINUE enoxaparin 40 mg subcutaneously once daily. Do not skip a dose. Do not inject into a bruise.",
            "2. HOLD warfarin 2.5 mg PO daily until 08/14. Do not resume unless the anticoagulation clinic instructs you.",
            "3. Do not take warfarin and enoxaparin on the same day unless the clinic tells you to overlap them.",
            "4. Avoid aspirin, ibuprofen, and naproxen.",
        ],
        activity="Walk several times a day. Do not sit still for more than 1 hour. Wear the compression stocking. Drink 1.8 to 2.2 L of water daily unless you are told to limit fluids.",
        followups=[
            "Anticoagulation clinic, 08/14/2027 at 8:40 AM. INR that morning.",
            "Hematology, Dr. L. Ortega, 08/21/2027 at 1:05 PM.",
        ],
        emergency="Sudden chest pain, coughing blood, a leg that is suddenly more swollen, or bleeding that will not stop.",
    ),
]


class SheetCanvas:
    def __init__(self, path: Path, title: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.c = canvas.Canvas(str(path), pagesize=letter)
        self.c.setTitle(title)
        self.y = H - M

    def line(self, txt, font="Helvetica", size=10.5, gap=15, dx=0):
        self.c.setFont(font, size)
        self.c.drawString(M + dx, self.y, txt)
        self.y -= gap

    def rule(self, gap=10, weight=0.7, gray=0.72):
        self.c.setStrokeColorRGB(gray, gray, gray)
        self.c.setLineWidth(weight)
        self.c.line(M, self.y, W - M, self.y)
        self.y -= gap

    def section(self, title):
        self.y -= 8
        self.line(title, "Helvetica-Bold", 12, 15)
        self.rule(12)

    def wrap(self, txt, font="Helvetica", size=10.5, dx=0, width=None, gap=14):
        limit = width or (W - 2 * M - dx)
        words, cur = txt.split(), ""
        for word in words:
            trial = f"{cur} {word}".strip()
            if stringWidth(trial, font, size) > limit:
                self.line(cur, font, size, gap, dx)
                cur = word
            else:
                cur = trial
        if cur:
            self.line(cur, font, size, gap, dx)


def render(spec: dict, path: Path) -> None:
    s = SheetCanvas(path, "Patient Discharge Instructions")
    s.line(spec["hospital"], "Helvetica-Bold", 17, 20)
    s.line(spec["dept_line"], "Helvetica", 8, 16)
    s.c.setStrokeColorRGB(0.1, 0.1, 0.1)
    s.c.setLineWidth(1.6)
    s.c.line(M, s.y, W - M, s.y)
    s.y -= 22
    s.line("PATIENT DISCHARGE INSTRUCTIONS", "Helvetica-Bold", 13, 22)

    rows = [
        ("Patient:", spec["patient"], "MRN:", spec["mrn"]),
        ("DOB:", spec["dob"], "Attending:", spec["attending"]),
        ("Admitted:", spec["admitted"], "Discharged:", spec["discharged"]),
    ]
    for a, b, cc, d in rows:
        s.c.setFont("Helvetica-Bold", 9.5)
        s.c.drawString(M, s.y, a)
        s.c.drawString(M + 3.3 * inch, s.y, cc)
        s.c.setFont("Helvetica", 9.5)
        s.c.drawString(M + 0.85 * inch, s.y, b)
        s.c.drawString(M + 4.25 * inch, s.y, d)
        s.y -= 14
    s.y -= 8

    s.section("DISCHARGE DIAGNOSIS")
    s.wrap(spec["diagnosis"])
    s.section("MEDICATION INSTRUCTIONS")
    for item in spec["meds"]:
        s.wrap(item, dx=12, width=W - 2 * M - 12)
        s.y -= 4
    s.section("ACTIVITY AND DIET")
    s.wrap(spec["activity"])
    s.section("FOLLOW-UP APPOINTMENTS")
    for i, item in enumerate(spec["followups"]):
        if i:
            s.y -= 4
        s.wrap(item)
    s.section("RETURN TO THE EMERGENCY DEPARTMENT IF YOU EXPERIENCE")
    s.wrap(spec["emergency"])
    if s.y < 1.35 * inch:
        raise SystemExit(f"{spec['id']} overflowed the page (y={s.y:.0f})")

    s.y -= 14
    s.rule(16, weight=0.7, gray=0.72)
    s.line("I have received and understand these instructions.", "Helvetica", 9.5, 30)
    s.c.setStrokeColorRGB(0.1, 0.1, 0.1)
    s.c.setLineWidth(1)
    s.c.line(M, s.y, M + 2.6 * inch, s.y)
    s.c.line(M + 3.3 * inch, s.y, M + 5.4 * inch, s.y)
    s.y -= 11
    s.line("Patient / Representative signature", "Helvetica", 7.5, 0)
    s.c.setFont("Helvetica", 7.5)
    s.c.drawString(M + 3.3 * inch, s.y, "Date")
    s.c.setFillColorRGB(0.6, 0.6, 0.6)
    s.c.drawString(M, 0.55 * inch, "Synthetic example document. Not a real patient record.")
    s.c.drawRightString(W - M, 0.55 * inch, "Page 1 of 1")
    s.c.save()


_DOSE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|l|units?|puffs?|capsule)\b", re.I)
_DATE = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
_RANGE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:to|-)\s*\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|l|units?|puffs?|pounds|minutes|hours|days)\b", re.I)
_NEG = re.compile(r"\b(?:do not|avoid|hold)\b", re.I)


def facts(spec: dict) -> dict:
    blob = "\n".join(spec["meds"] + [spec["activity"], spec["emergency"], *spec["followups"]])
    return {
        "id": spec["id"],
        "pdf": spec["file"],
        "patient": spec["patient"],
        "diagnosis": spec["diagnosis"],
        "meds": spec["meds"],
        "activity": spec["activity"],
        "followups": spec["followups"],
        "emergency": spec["emergency"],
        "doses": sorted(set(m.group(0) for m in _DOSE.finditer(blob))),
        "dates": sorted(set(m.group(0) for m in _DATE.finditer(blob))),
        "ranges": sorted(set(m.group(0) for m in _RANGE.finditer(blob))),
        "negations": sorted(set(m.group(0).lower() for m in _NEG.finditer(blob))),
    }


def check_intake(path: Path) -> int:
    root = HERE.parents[1]
    sys.path.insert(0, str(root))
    from backend.pipeline.intake import load_document
    doc = load_document(path)
    meds = [p for p in doc.content() if p.text[:3].rstrip(".").isdigit() or p.text.startswith(tuple(f"{i}." for i in range(1, 8)))]
    if len(doc.content()) < 6 or len(meds) < 3:
        raise SystemExit(f"{path.name}: intake found {len(doc.content())} content paragraphs, {len(meds)} medication lines")
    return len(doc.content())


def main() -> None:
    manifest = []
    for spec in SHEETS:
        path = HERE / spec["file"]
        render(spec, path)
        row = facts(spec)
        missing = [k for k in ("doses", "dates", "ranges", "negations") if not row[k]]
        if missing:
            raise SystemExit(f"{spec['id']} is missing {missing}")
        n = check_intake(path)
        row["content_paragraphs"] = n
        manifest.append(row)
        print(f"wrote {path.relative_to(HERE)}  content={n}  doses={len(row['doses'])}  ranges={row['ranges']}")

    out = SHEET_DIR / "manifest.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in manifest), encoding="utf-8")
    print(f"wrote {out.relative_to(HERE)}  sheets={len(manifest)}")


if __name__ == "__main__":
    main()
