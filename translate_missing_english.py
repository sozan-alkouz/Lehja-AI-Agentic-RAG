import os
import time
import pandas as pd
from deep_translator import GoogleTranslator

# إذا كان الملف المترجم موجودًا، أكمل عليه
if os.path.exists("done_translated.xlsx"):
    INPUT_FILE = "done_translated.xlsx"
    print("Resuming from done_translated.xlsx")
else:
    INPUT_FILE = "done.xlsx"
    print("Starting from done.xlsx")

OUTPUT_FILE = "done_translated.xlsx"

# قراءة الملف
df = pd.read_excel(INPUT_FILE)

# التأكد من وجود الأعمدة
required_columns = ["Modern Standard Arabic", "English"]

for col in required_columns:
    if col not in df.columns:
        raise Exception(f"Column '{col}' not found.")

translator = GoogleTranslator(source="ar", target="en")

translated = 0

for i in df.index:

    english = str(df.loc[i, "English"]).strip()

    # إذا كانت الترجمة موجودة، انتقل للصف التالي
    if english != "" and english.lower() != "nan":
        continue

    arabic = str(df.loc[i, "Modern Standard Arabic"]).strip()

    if arabic == "" or arabic.lower() == "nan":
        continue

    while True:
        try:
            translation = translator.translate(arabic)

            df.loc[i, "English"] = translation

            translated += 1

            print(f"[{translated}] Row {i+2} translated")

            # احفظ بعد كل ترجمة
            df.to_excel(OUTPUT_FILE, index=False)

            time.sleep(0.5)

            break

        except Exception as e:
            print(f"Error at row {i+2}: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

print("=" * 50)
print("Finished Successfully!")
print(f"Translated {translated} new rows.")
print("=" * 50)