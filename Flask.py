import os
from flask import Flask, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename

from lib.relaylib import Relay, find_device

relay = Relay(find_device("VID:PID=0d28:0204"), 115200)

UPLOAD_FOLDER = '/home/pi/Flask/uploads'
ALLOWED_EXTENSIONS = set(['wav'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if request.form['submit'] == 'Upload file':
            # check if the post request has the file part
            if 'file' not in request.files:
                flash('No file part')
                return redirect(request.url)
            file = request.files['file']
            volume = int (request.form['volume'])
            # if user does not select file, browser also
            # submit a empty part without filename
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                print(volume)
                if relay.is_busy():
                    flash("Wait for previous upload to finish")
                    return redirect("")

                relay.set_volume(volume)
                relay.join()
                relay.send_file(filepath)
                return redirect("")
        if request.form['submit'] == 'Repeat last uploaded file':
            volume = int (request.form['volume'])
            if relay.is_busy():
                flash("Wait for upload to finish")
                return redirect("")
            else:
                relay.set_volume(volume)
                relay.join()
                relay.play_last()

    return render_template("upload.html")

if __name__ == '__main__':
    app.run(debug=True)