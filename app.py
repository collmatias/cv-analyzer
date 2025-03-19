#Python 3.10
# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, send_from_directory, jsonify
import os
import pandas as pd
import json

from utils import extract_text_from_pdf, analyze_cv, analyze_compared_cv, load_candidates_ranking, generate_pdf
from utils import UPLOAD_FOLDER, RESULTS_FOLDER, PROCESSED_FOLDER, MAX_CVS, MAX_CVS_COMPARE

app = Flask(__name__)

@app.route("/")
def upload_page():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    analysis_type = request.form.get("analysis_type")
    files = request.files.getlist("cv_files")
    job_position = ""
    rankings = []
    all_cv_texts = []  # Lista para almacenar los textos de todos los CVs si estamos en modo comparación

    if len(files) == 0:
        return render_template("error.html", error_message="No se han subido archivos."), 400
    elif analysis_type == "comparison" and len(files) > MAX_CVS_COMPARE:
        error_message = "No se pueden analizar más de {MAX_CVS_COMPARE} CVs a la vez."
        return render_template("error.html", error_message=error_message), 400
    elif len(files) > MAX_CVS:
        error_message = "No se pueden analizar más de {MAX_CVS} CVs a la vez."
        return render_template("error.html", error_message=error_message), 400

    for file in files:
        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)
        text = extract_text_from_pdf(filename)

        # En modo de comparación, guardamos todos los textos de los CVs
        if analysis_type == "comparison":
            if text:
                all_cv_texts.append("CV: {filename}\n{text}".format(filename=file.filename, text=text))
        else:
            # En modo individual, analizamos el CV por separado
            if text:
                analysis, error = analyze_cv(text)
                if error:
                    return render_template("error.html", error_message=error), 400
                rankings.append({"Nombre": file.filename, "Puntaje": analysis.get("evaluacion", {}).get("puntaje", "N/A")})
            else:
                analysis, error = None, "No se pudo extraer texto del CV."
                rankings.append({"Nombre": file.filename, "Puntaje": "N/A"})

    # Si estamos en modo de comparación, analizamos todos los CVs juntos
    if analysis_type == "comparison":
        # Unir todos los textos de los CVs en un solo string
        combined_text = "\n".join(all_cv_texts)

        data = request.form.get("job_position")
        if data:
            job_position = "Puesto Objetivo: {job_position}".format(job_position=data)

        # Enviar el texto combinado a OpenAI para análisis de comparación
        analysis, error = analyze_compared_cv(combined_text,job_position)

        if error:
            return render_template("error.html", error_message=error), 400

        pdf_path = generate_pdf(file.filename, json.dumps(analysis, indent=4))  # Guardamos el JSON en el PDF

        # Verificar si analysis contiene candidatos
        rankings = load_candidates_ranking(analysis, rankings, pdf_path)

        # Ordenar por puntaje (si es necesario)
        rankings.sort(key=lambda x: x['Puntaje'], reverse=True)
    
    # Si estamos en modo individual, ya hemos asignado los puntajes durante el loop anterior
    if analysis_type == "comparison" and rankings:
        # Guardar el ranking en un archivo CSV
        rankings_df = pd.DataFrame(rankings).sort_values(by="Puntaje", ascending=False)
        rankings_df.to_csv(os.path.join(RESULTS_FOLDER, "cv_ranking.csv"), index=False)
    
    return render_template("results.html", rankings=rankings)

@app.route("/download/results/<filename>")
def download_file(filename):
    # La carpeta "results" debe ser accesible desde el servidor
    results_folder = os.path.join(os.getcwd(), RESULTS_FOLDER)
    try:
        # Envía el archivo solicitado desde la carpeta de resultados
        return send_from_directory(results_folder, filename, as_attachment=True)
    except FileNotFoundError:
        return render_template("error.html", error_message="Archivo no encontrado."), 404

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