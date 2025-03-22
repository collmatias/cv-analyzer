# cv-analyzer

# Proyecto Flask

Este proyecto es una aplicación desarrollada con Flask y requiere **Python 3.10** para su correcta ejecución. A continuación, se detallan los pasos para configurar el entorno y ejecutar la aplicación.

## 📌 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:
- **Python 3.10** ([Descargar aquí](https://www.python.org/downloads/))
- **pip** (gestor de paquetes de Python, incluido con Python 3.10)
- **Virtualenv** (opcional pero recomendado para aislar el entorno)

## 🔧 Configuración del Entorno Virtual

Se recomienda instalar las dependencias dentro de un **entorno virtual** para evitar conflictos con otras instalaciones de Python en tu sistema.

1. **Crear un entorno virtual:**
   ```bash
   python3.10 -m venv venv
   ```
   Esto creará una carpeta llamada `venv` en el directorio del proyecto.

2. **Activar el entorno virtual:**
   - En **Linux/macOS**:
     ```bash
     source venv/bin/activate
     ```
   - En **Windows**:
     ```powershell
     venv\Scripts\activate
     ```
   Al activarse correctamente, deberías ver `(venv)` al inicio de la línea de comandos.

3. **Instalar las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Ejecución de la Aplicación Flask

Una vez instaladas las dependencias, puedes ejecutar la aplicación Flask con los siguientes pasos:

1. **Asegúrate de que el entorno virtual está activado** (`source venv/bin/activate` o `venv\Scripts\activate`).
2. **Ejecutar la aplicación:**
   ```bash
   python app.py
   ```
3. **Acceder a la aplicación** en tu navegador:
   - Por defecto, Flask corre en: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 🛠️ Notas Adicionales
- Si deseas cambiar el puerto de ejecución, puedes hacerlo ejecutando:
  ```bash
  python app.py --port=8080
  ```
- Para desactivar el entorno virtual en cualquier momento:
  ```bash
  deactivate
  ```

## 📄 IMPORTANTE
Para poder ejecutar consultas a ChatGPT debes agregar una API Key valida en el archivo chatgpt-api-key.txt

O tambien exportarla como variable de entorno:

  ```bash
  export OPENAI_API_KEY=sk-proj...
  ```

Tambien de debe exportar como variable de entorno una SECRET_KEY para el manejo de sesiones.

  ```bash
  export SECRET_KEY=random_secret_key
  ```


---
¡Listo! Ahora puedes trabajar con la aplicación Flask. 🚀

