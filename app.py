from flask import Flask, render_template, request, redirect
import pandas as pd
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "investment_data.xlsx")

if not os.path.exists(FILE_PATH):
    df = pd.DataFrame(columns=["Asset Class", "Asset Name", "Amount Invested", "Current Value"])
    df.to_excel(FILE_PATH, index=False)
else:
    try:
        test_df = pd.read_excel(FILE_PATH, engine='openpyxl')
        if list(test_df.columns) != ["Asset Class", "Asset Name", "Amount Invested", "Current Value"]:
            raise ValueError("Column headers mismatch.")
    except:
        df = pd.DataFrame(columns=["Asset Class", "Asset Name", "Amount Invested", "Current Value"])
        df.to_excel(FILE_PATH, index=False)

@app.route('/')
def index():
    df = pd.read_excel(FILE_PATH, engine='openpyxl')
    total_invested = df['Amount Invested'].sum()
    current_value = df['Current Value'].sum()
    returns = current_value - total_invested
    roi = (returns / total_invested) * 100 if total_invested else 0
    return render_template("index.html", table=df.to_dict(orient="records"),
                           total=total_invested, current=current_value,
                           returns=returns, roi=round(roi, 2))

@app.route('/add', methods=["GET", "POST"])
def add():
    if request.method == "POST":
        new_entry = {
            "Asset Class": request.form["class"],
            "Asset Name": request.form["name"],
            "Amount Invested": float(request.form["amount"]),
            "Current Value": float(request.form["current"])
        }
        df = pd.read_excel(FILE_PATH, engine='openpyxl')
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel(FILE_PATH, index=False)
        return redirect('/')
    return render_template("add.html")

@app.route('/edit/<int:idx>', methods=["GET", "POST"])
def edit(idx):
    df = pd.read_excel(FILE_PATH, engine='openpyxl')
    if request.method == "POST":
        df.at[idx, "Asset Class"] = request.form["class"]
        df.at[idx, "Asset Name"] = request.form["name"]
        df.at[idx, "Amount Invested"] = float(request.form["amount"])
        df.at[idx, "Current Value"] = float(request.form["current"])
        df.to_excel(FILE_PATH, index=False)
        return redirect('/')
    row = df.iloc[idx]
    return render_template("edit.html", idx=idx, row=row)

@app.route('/delete/<int:idx>')
def delete(idx):
    df = pd.read_excel(FILE_PATH, engine='openpyxl')
    df.drop(index=idx, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.to_excel(FILE_PATH, index=False)
    return redirect('/')

@app.route('/import', methods=["GET", "POST"])
def import_excel():
    if request.method == "POST":
        file = request.files["file"]
        if file and file.filename.endswith(".csv"):
            try:
                # Read CSV
                df_raw = pd.read_csv(file)

                # Normalize column names
                df_raw.columns = df_raw.columns.str.strip().str.replace(".", "", regex=False)

                # Ensure required columns
                if not {"Invested", "Cur val"}.issubset(df_raw.columns):
                    return "❌ CSV must have columns: 'Invested' and 'Cur val'", 400

                total_invested = df_raw["Invested"].sum()
                total_current = df_raw["Cur val"].sum()

                df_existing = pd.read_excel(FILE_PATH, engine='openpyxl')

                # Generate unique name like Zerodha, Zerodha1, etc.
                base_name = "Zerodha"
                asset_names = df_existing["Asset Name"].tolist()
                if base_name not in asset_names:
                    final_name = base_name
                else:
                    i = 1
                    while f"{base_name}{i}" in asset_names:
                        i += 1
                    final_name = f"{base_name}{i}"

                # Append new row
                new_entry = {
                    "Asset Class": "Equity",
                    "Asset Name": final_name,
                    "Amount Invested": total_invested,
                    "Current Value": total_current
                }

                df_existing = pd.concat([df_existing, pd.DataFrame([new_entry])], ignore_index=True)
                df_existing.to_excel(FILE_PATH, index=False)

                detail_file = os.path.join(BASE_DIR, f"{final_name}.csv")
                df_raw.to_csv(detail_file, index=False)

                return redirect('/')
            except Exception as e:
                return f"❌ Error processing file: {e}", 500
        else:
            return "❌ Only CSV files are allowed", 400

    return render_template("import.html")


@app.route("/zerodha/<name>")
def view_zerodha_details(name):
    try:
        # Look for a CSV matching the Zerodha asset name (e.g., Zerodha.csv, Zerodha1.csv, etc.)
        detail_file = os.path.join(BASE_DIR, f"{name}.csv")
        if not os.path.exists(detail_file):
            return f"❌ Details not found for {name}", 404

        df = pd.read_csv(detail_file)
        columns = df.columns.tolist()
        table = df.to_dict(orient="records")
        return render_template("zerodha_details.html", name=name, table=table, columns=columns)

    except Exception as e:
        return f"❌ Error loading details for {name}: {str(e)}", 500


if __name__ == "__main__":

