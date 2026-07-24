import os
import pandas as pd
import langdetect

def is_english(text):
    try:
        return langdetect.detect(text) == 'en'
    except:
        return False

def clean_csv_files(data_dir):

    for filename in os.listdir(data_dir):
        if not filename.endswith('.csv'):
            continue
        file_path = os.path.join(data_dir, filename)
        print(f"Processing {file_path}")
        try:
            df = pd.read_csv(file_path)
        except pd.errors.EmptyDataError:
            print(f"  Skipped (empty file): {file_path}")
            continue
        except Exception as e:
            print(f"  Skipped (read error): {file_path} ({e})")
            continue

        if df.empty or len(df.columns) == 0:
            print(f"  Skipped (no data): {file_path}")
            continue

        # Brand filtering is no longer done here — scraper/product_page.py now
        # confirms brand from the product page itself before a row is ever
        # written, so a post-hoc substring filter would only mask a source-side
        # bug rather than fix one.

        # Remove non-English reviews. Match only the review body column itself
        # (ReviewRecord.text) — a loose substring match on 'review'/'text' also
        # catches numeric columns like review_count on the products CSVs, and
        # langdetect flags every row of those as non-English.
        review_cols = [col for col in df.columns if col.lower() == "text"]
        for col in review_cols:
            before = len(df)
            df = df[df[col].apply(lambda x: is_english(str(x)))]
            after = len(df)
            if after < before:
                print(f"  Removed {before - after} non-English reviews from column '{col}' in {file_path}.")

        if df.empty:
            print(f"  Warning: Cleaning would result in empty file for {file_path}. Skipping save to prevent data loss.")
            continue

        df.to_csv(file_path, index=False)
        print(f"  Cleaned {file_path}")

if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), 'raw')
    clean_csv_files(data_dir)
    print("All CSVs cleaned.")
