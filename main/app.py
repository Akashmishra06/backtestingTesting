from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# Define the upload folder path
UPLOAD_FOLDER = './uploads'  # You can change this to any path
ALLOWED_EXTENSIONS = {'csv'}

# Create the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check if the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'index.html')  # Serve the HTML frontend

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'csvFiles' not in request.files:
        return jsonify({"success": False, "message": "No file part"})

    files = request.files.getlist('csvFiles')
    if not files:
        return jsonify({"success": False, "message": "No files selected"})

    uploaded_files = []
    errors = []

    for file in files:
        if file.filename == '':
            errors.append("Empty file name detected.")
            continue

        if file and allowed_file(file.filename):
            # Secure the file name
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            uploaded_files.append(filename)
        else:
            errors.append(f"Invalid file format for {file.filename}")

    if uploaded_files:
        return jsonify({
            "success": True,
            "message": f"Files uploaded successfully: {', '.join(uploaded_files)}",
            "errors": errors if errors else None
        })
    else:
        return jsonify({"success": False, "message": "No valid CSV files were uploaded.", "errors": errors})

if __name__ == '__main__':
    app.run(debug=True)
