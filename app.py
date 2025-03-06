from flask import Flask, request, render_template, send_file, jsonify
import openai
import pdfplumber
import os
import pandas as pd
from fpdf import FPDF

# Configurar la API de OpenAI
if not os.path.exists("chatgpt-api-key.txt"):
    openai.api_key = "sk-..."
    print("API key is missing! Please add your OpenAI API key to a file"
else:
    file = open("chatgpt-api-key.txt", "r")
    openai.api_key = file.read()
    file.close()

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
RESULTS_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Función para extraer texto de un PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text.strip()

# Función para analizar el CV con ChatGPT
def analyze_cv(text):
    prompt = f"""
    Analiza el siguiente CV y proporciona un resumen con:
    - Perfil profesional
    - Career path recomendado
    - Habilidades clave a potenciar
    - Indicador MBTI aproximado
    - Puestos recomendados y habilidades clave
    - Evaluación general y puntaje del CV del 1 al 100
    - Industria recomendada basada en la experiencia
    - Lista de habilidades clave extraídas del CV
    
    CV:
    {text}
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "Eres un experto en análisis de CV."},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

# Función para generar PDF con el análisis
def generate_pdf(cv_name, analysis):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, f"Análisis de CV - {cv_name}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, analysis)
    pdf_filename = os.path.join(RESULTS_FOLDER, f"{cv_name}_analysis.pdf")
    pdf.output(pdf_filename)
    return pdf_filename

# Página principal para cargar CVs
@app.route("/")
def upload_page():
    return render_template("index.html")

# Ruta para procesar los CVs
@app.route("/analyze", methods=["POST"])
def analyze():
    files = request.files.getlist("cv_files")
    rankings = []
    
    for file in files:
        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)
        text = extract_text_from_pdf(filename)
        analysis = analyze_cv(text)
        pdf_path = generate_pdf(file.filename, analysis)
        score = int(analysis.split("Puntaje del CV:")[1].split("/100")[0])  # Extraer puntaje
        industry = analysis.split("Industria recomendada:")[1].split("\n")[0] if "Industria recomendada:" in analysis else "No especificado"
        skills = analysis.split("Lista de habilidades clave:")[1].split("\n")[0] if "Lista de habilidades clave:" in analysis else "No especificado"
        rankings.append({"Nombre": file.filename, "Puntaje": score, "Industria": industry, "Habilidades": skills, "PDF": pdf_path})
    
    rankings_df = pd.DataFrame(rankings).sort_values(by="Puntaje", ascending=False)
    rankings_df.to_csv(os.path.join(RESULTS_FOLDER, "cv_ranking.csv"), index=False)
    
    return render_template("results.html", rankings=rankings)

# Ruta para descargar los PDF
@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(RESULTS_FOLDER, filename), as_attachment=True)

# Agregar Bootstrap y gráficos con Chart.js en la interfaz
@app.route("/ranking")
def ranking_page():
    rankings_df = pd.read_csv(os.path.join(RESULTS_FOLDER, "cv_ranking.csv"))
    return render_template("ranking.html", rankings=rankings_df.to_dict(orient="records"))

# API para obtener datos en JSON
@app.route("/api/rankings")
def api_rankings():
    rankings_df = pd.read_csv(os.path.join(RESULTS_FOLDER, "cv_ranking.csv"))
    return jsonify(rankings_df.to_dict(orient="records"))

# Agregar filtrado en la interfaz web
@app.route("/filtered_ranking")
def filtered_ranking():
    rankings_df = pd.read_csv(os.path.join(RESULTS_FOLDER, "cv_ranking.csv"))
    min_score = request.args.get("min_score", default=0, type=int)
    max_score = request.args.get("max_score", default=100, type=int)
    industry_filter = request.args.get("industry", default=None, type=str)
    skills_filter = request.args.get("skills", default=None, type=str)
    
    filtered_rankings = rankings_df[(rankings_df["Puntaje"] >= min_score) & (rankings_df["Puntaje"] <= max_score)]
    
    if industry_filter:
        filtered_rankings = filtered_rankings[filtered_rankings["Industria"] == industry_filter]
    
    if skills_filter:
        filtered_rankings = filtered_rankings[filtered_rankings["Habilidades"].str.contains(skills_filter, case=False, na=False)]
    
    return render_template("filtered_ranking.html", rankings=filtered_rankings.to_dict(orient="records"))

if __name__ == "__main__":
    app.run(debug=True)