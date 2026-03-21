import os
import numpy as np
from flask import Flask, render_template, request, send_from_directory
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# ---------------- Flask App ----------------
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ---------------- Load Model ----------------
model = load_model('hypervision_OPG_model.h5', compile=False)

# ---------------- Model Settings ----------------
img_size = (299, 299)

class_dict = {
    0: 'Caries',
    1: 'Decayed Tooth',
    2: 'Ectopic',
    3: 'Healthy Teeth'
}

classes = list(class_dict.values())

# ---------------- Serve Uploaded Images ----------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------- Main Route ----------------
@app.route('/', methods=['GET', 'POST'])
def index():
    prediction_label = None
    class_prob_pairs = None
    image_path = None

    if request.method == 'POST':
        file = request.files.get('image')

        if file and file.filename != '':
            filename = file.filename
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # ----- Image Preprocessing -----
            img = image.load_img(save_path, target_size=img_size)
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = img_array / 255.0

            # ----- Prediction -----
            preds = model.predict(img_array)
            class_index = np.argmax(preds, axis=1)[0]
            prediction_label = classes[class_index]

            class_prob_pairs = list(zip(classes, preds[0]))

            # IMPORTANT: browser-accessible URL
            image_path = f"/uploads/{filename}"

    return render_template(
        'index.html',
        prediction=prediction_label,
        class_prob_pairs=class_prob_pairs,
        image_path=image_path
    )

# ---------------- Run App ----------------
if __name__ == '__main__':
    app.run(debug=True)
