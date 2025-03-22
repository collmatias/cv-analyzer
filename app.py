#Python 3.10
# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, send_from_directory, jsonify, request, redirect, url_for, session, flash
import os
import pandas as pd
import json
from datetime import datetime

from utils import extract_text_from_pdf, analyze_cv, analyze_compared_cv, load_candidates_ranking, generate_pdf, generate_global_report, get_user_folders
from utils import MAX_CVS, MAX_CVS_COMPARE, USERS_FILE, USERS_FOLDER
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import Schema, fields, ValidationError

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","")

####################################################

def save_users(users):
    """Guarda los usuarios en el archivo JSON con contraseñas hasheadas."""
    for user, data in users.items():
        if "password" in data and not data["password"].startswith("pbkdf2:sha256"):
            #data["password"] = generate_password_hash(data["password"])
            data["password"] = data["password"]
    
    with open(os.path.join(USERS_FOLDER, USERS_FILE), "w") as file:
        json.dump(users, file, indent=4)

def verify_password(stored_password, provided_password):
    """Verifica la contraseña del usuario."""
    return check_password_hash(stored_password, provided_password)

def load_users():
    """Carga los usuarios desde el archivo JSON y maneja errores."""
    users_path = os.path.join(USERS_FOLDER, USERS_FILE)
    
    if not os.path.exists(users_path):
        os.makedirs(USERS_FOLDER, exist_ok=True)
        #save_users({"admin": {"username": "admin", "nombre": "admin", "apellido": "admin", "password": generate_password_hash("admin")}})
        save_users({"admin": {"username": "admin", "nombre": "admin", "apellido": "admin", "password": "admin"}})
    
    with open(users_path, "r") as file:
        return json.load(file)
    
def get_user_data(session):
    
    user=session["user"]
    user_data = load_users().get(user, {})

    return user_data
####################################################

@app.route("/")
def upload_page():
    if "user" not in session:
        return redirect(url_for("login_page"))
    
    return render_template("index.html",user_data=get_user_data(session))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()

        if username in users and users[username]["password"] == password:
        #if username in users and verify_password(users[username]["password"], password):
            session["user"] = username
            flash("Inicio de sesión exitoso.", "success")
            return redirect(url_for("upload_page"))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))

@app.route("/admin", methods=["GET", "POST"])
def manage_users():
    if "user" not in session or session["user"] != "admin":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("login_page"))

    users = load_users()

    # Asegurar que todos los usuarios tengan el campo "username"
    for user_key, user_data in users.items():
        if "username" not in user_data:
            user_data["username"] = user_key

    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username")

        if action == "add":
            nombre = request.form.get("nombre")
            apellido = request.form.get("apellido")
            password = request.form.get("password")

            if username in users:
                flash("El usuario ya existe.", "warning")
            else:
                users[username] = {
                    "username": username,  # Se agrega el campo username
                    "nombre": nombre,
                    "apellido": apellido,
                    "password": password
                }
                save_users(users)
                flash(f"Usuario {username} agregado.", "success")

        elif action == "edit":
            if username in users:
                users[username].update({
                    "username": username,  # Asegurar que el username no se pierda
                    "nombre": request.form.get("nombre"),
                    "apellido": request.form.get("apellido"),
                    "password": request.form.get("password")
                })
                save_users(users)
                flash(f"Usuario {username} actualizado.", "success")
            else:
                flash("El usuario no existe.", "warning")

        elif action == "delete" and username:
            if username in users and username != "admin":
                del users[username]
                save_users(users)
                flash(f"Usuario {username} eliminado.", "success")
            else:
                flash("No puedes eliminar este usuario.", "warning")

    return render_template("admin.html", users=users, user_data=get_user_data(session))

####################################################
@app.route("/analyze", methods=["POST"])
def analyze():

    if "user" not in session:  # Si el usuario no está en sesión, redirige al login
        return redirect(url_for("login_page"))

    user_folders = get_user_folders(session)  # Obtener rutas de usuario
    if not user_folders:
        return redirect(url_for("login_page"))
    
    analysis_type = request.form.get("analysis_type")
    files = request.files.getlist("pdf_files")
    job_position = "No especificado"
    rankings = []
    all_cv_texts = []  # Lista para almacenar los textos de todos los CVs si estamos en modo comparación
    fecha = datetime.now().strftime("%Y%m%d%H%M")
    fecha_title = pd.to_datetime(fecha).strftime("%d/%m/%Y %H:%M")

    if str(files) == "[<FileStorage: '' ('application/octet-stream')>]": # Si no se han subido archivos
        return render_template("error.html", error_message="No se han subido archivos.",user_data=get_user_data(session)), 400
    elif analysis_type == "comparison" and len(files) > MAX_CVS_COMPARE:
        error_message = "No se pueden analizar más de {MAX_CVS_COMPARE} CVs a la vez."
        return render_template("error.html", error_message=error_message,user_data=get_user_data(session)), 400
    elif len(files) > MAX_CVS:
        error_message = "No se pueden analizar más de {MAX_CVS} CVs a la vez."
        return render_template("error.html", error_message=error_message,user_data=get_user_data(session)), 400

    files_names  = []
    for file in files:
        filename = os.path.join(user_folders.upload, file.filename)
        files_names.append(file.filename)
        
        file.save(filename)
        text = extract_text_from_pdf(filename)

        # En modo de comparación, guardamos todos los textos de los CVs
        if analysis_type == "comparison":
            if text:
                all_cv_texts.append("CV: {filename}\n{text}".format(filename=file.filename, text=text))
        else:
            # En modo individual, analizamos el CV por separado
            return render_template("error.html", error_message="Funcion no implementada.",user_data=get_user_data(session)), 400
            # if text:
            #     analysis, error = analyze_cv(text)
            #     if error:
            #         return render_template("error.html", error_message=error,user_data=get_user_data(session)), 400
            #     rankings.append({"Nombre": file.filename, "Puntaje": analysis.get("evaluacion", {}).get("puntaje", "N/A")})
            # else:
            #     analysis, error = None, "No se pudo extraer texto del CV."
            #     rankings.append({"Nombre": file.filename, "Puntaje": "N/A"})

    # Si estamos en modo de comparación, analizamos todos los CVs juntos
    if analysis_type == "comparison":
        # Unir todos los textos de los CVs en un solo string
        combined_text = "\n".join(all_cv_texts)

        data = request.form.get("job_position")
        if data:
            job_position = data
        else:
            job_position = "No especificado"

        # Enviar el texto combinado a OpenAI para análisis de comparación
        analysis, error = analyze_compared_cv(combined_text,job_position)

        if error:
            return render_template("error.html", error_message=error, user_data=get_user_data(session)), 400

        pdf_paths = generate_pdf(analysis, user_folders, fecha)  # Guardamos el JSON en el PDF
        # Verificar si analysis contiene candidatos
        rankings = load_candidates_ranking(analysis, rankings, pdf_paths)

        # Ordenar por puntaje (si es necesario)
        rankings.sort(key=lambda x: x['puntaje'], reverse=True)
    
    # Si estamos en modo individual, ya hemos asignado los puntajes durante el loop anterior
    if analysis_type == "comparison" and rankings:
        # Guardar el ranking en un archivo CSV
        rankings_df = pd.DataFrame(rankings).sort_values(by="puntaje", ascending=False)
        rankings_df.to_csv(os.path.join(user_folders.rankings, f"cv_ranking_{fecha}.csv"), index=False)
    
    report_filename = generate_global_report(files_names, job_position, analysis, user_folders, fecha)  # Generar el reporte global

    filters = {
        "min_score": 0,
        "max_score": 100,
        "industry": "",
        "skills": ""
    }
    # Devolvemos la plantilla de ranking sin filtrado
    return render_template("filtered_ranking.html",
                           rankings=rankings_df.to_dict(orient="records"),
                           fecha_title=fecha_title,
                           fecha=fecha,
                           filters=filters,
                           report_filename=report_filename,
                           user_data=get_user_data(session))
    
    
@app.route("/download/<filename>")
def download(filename):
    if "user" not in session:  # Si el usuario no está en sesión, redirige al login
        return redirect(url_for("login_page"))

    user_folders = get_user_folders(session)
    if not user_folders:
        return redirect(url_for("login_page"))

    # Determinar la carpeta del archivo
    if "_report_" in filename.lower():
        folder = user_folders.reports
    elif "_analysis_" in filename.lower():
        folder = user_folders.results
    else:
        folder = user_folders.upload

        folder = os.path.join(os.getcwd(), folder)        
    try:
        # Envía el archivo solicitado desde la carpeta de resultados
        return send_from_directory(folder, filename, as_attachment=True)
    except FileNotFoundError:
        return render_template("error.html", error_message="Archivo no encontrado.", user_data=get_user_data(session)), 404

@app.route("/reports")
def reports_page():
    if "user" not in session:  # Si el usuario no está en sesión, redirige al login
        return redirect(url_for("login_page"))
    
    user_folders = get_user_folders(session)
    if not user_folders:
        return redirect(url_for("login_page"))

    # Obtener la lista de archivos en la carpeta de reportes
    report_files = [
        {
            "filename": f,
            "date": f.split("_")[-1].replace(".pdf", "")  # Extrae la fecha del nombre
        }
        for f in os.listdir(user_folders.reports) if f.startswith("global_report_") and f.endswith(".pdf")
    ]
    # Ordenar por fecha descendente
    report_files.sort(key=lambda x: x["date"], reverse=True)

    return render_template("reports.html", report_files=report_files, user_data=get_user_data(session))

@app.route("/rankings")
def rankings_page():
    if "user" not in session:  # Si el usuario no está en sesión, redirige al login
        return redirect(url_for("login_page"))
    
    user_folders = get_user_folders(session)
    if not user_folders:
        return redirect(url_for("login_page"))

    # Obtener la lista de archivos en la carpeta de reportes
    ranking_files = [
        {
            "filename": f,
            "date": f.split("_")[-1].replace(".csv", "")  # Extrae la fecha del nombre
        }
        for f in os.listdir(user_folders.rankings  ) if f.startswith("cv_ranking") and f.endswith(".csv")
    ]
    # Ordenar por fecha descendente
    ranking_files.sort(key=lambda x: x["date"], reverse=True)

    return render_template("rankings.html", ranking_files=ranking_files, user_data=get_user_data(session))

# Agregar filtrado en la interfaz web
@app.route("/filtered_ranking/<fecha>")
def filtered_ranking(fecha):
    if "user" not in session:  # Si el usuario no está en sesión, redirige al login
        return redirect(url_for("login_page"))

    user_folders = get_user_folders(session)
    if not user_folders:
        return redirect(url_for("login_page"))

    rankings_df = pd.read_csv(os.path.join(user_folders.rankings, f"cv_ranking_{fecha}.csv"))

    min_score = request.args.get("min_score", default=0, type=int)
    max_score = request.args.get("max_score", default=100, type=int)
    industry_filter = request.args.get("industry", default="", type=str)
    skills_filter = request.args.get("skills", default="", type=str)
    
    filtered_rankings = rankings_df[(rankings_df["puntaje"] >= min_score) & (rankings_df["puntaje"] <= max_score)]
    
    if industry_filter:
        filtered_rankings = filtered_rankings[filtered_rankings["industria"].str.contains(industry_filter, case=False, na=False)]
                                              
    
    if skills_filter:
        filtered_rankings = filtered_rankings[filtered_rankings["habilidades"].str.contains(skills_filter, case=False, na=False)]
    
    filters = {
        "min_score": min_score,
        "max_score": max_score,
        "industry": industry_filter,
        "skills": skills_filter
    }
    report_filename = f"global_report_{fecha}.pdf"
    fecha_title = pd.to_datetime(fecha).strftime("%d/%m/%Y %H:%M")

    # Devolvemos la plantilla de ranking con filtrado
    return render_template("filtered_ranking.html",
                           rankings=filtered_rankings.to_dict(orient="records"),
                           fecha_title=fecha_title,
                           fecha=fecha,
                           filters=filters,
                           report_filename=report_filename,
                           user_data=get_user_data(session))

###### API ######
@app.route("/api/rankings/<fecha>")
def api_rankings(fecha):
    if "user" not in session:  # Si el usuario no está en sesión, redirige al login
        return redirect(url_for("login_page"))
    
    user_folders = get_user_folders(session)
    if not user_folders:
        return redirect(url_for("login_page"))

    rankings_path = os.path.join(user_folders.rankings, f"cv_ranking_{fecha}.csv")

    if os.path.exists(rankings_path):
        #rankings_df = pd.read_csv(rankings_path)
        rankings_df = pd.read_csv(rankings_path, encoding="utf-8")
        return rankings_df.to_json(orient="records", force_ascii=False) 
    return jsonify([]), 404

if __name__ == "__main__":
    app.run(debug=True)
