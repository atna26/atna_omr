from flask import Flask, render_template, request
import os
import flask
import werkzeug
import numpy
import scipy.misc
import os.path
import json
import base64
from omr import omr2
from PIL import Image

app = Flask(__name__)
class ResponseData(object):
    code = ""
    message = ""
    data = ""

    def __init__(self, code, message, data):
        self.code = code
        self.data = data
        self.message = message
def Base64Encoder(string):
    with open(string, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string
    
@app.route('/', methods = ['GET', 'POST'])
def handle_request():
    try:
        if request.method == 'POST':
            imagefile = flask.request.files['image']
            filename = werkzeug.utils.secure_filename(imagefile.filename)
            print("\nReceived image File name : " + imagefile.filename)
            imagefile.save(filename)
            im = Image.open(filename)
            imagename = os.path.splitext(filename)[0]
            rgba_im = im.convert('RGBA')
            newname = imagename + ".png"
            rgba_im.save(newname)
            imageresult = omr2("./" + newname)

            hasilGambar = Base64Encoder("detected.png")
            hasilFileTxt = Base64Encoder("detected.txt")
            imageBase64 = hasilGambar.decode('ascii')
            txtBase64 = hasilFileTxt.decode('ascii')
            data = {}
            data["gambar"] = imageBase64
            data["file"] = txtBase64
            response = ResponseData(200, "Gambar Berhasil Diproses", [data])
            return json.dumps(response.__dict__)
    except Exception as e:
        if hasattr(e, 'message'):
            data = [e]
            data_len = ""
            response = ResponseData("500","Terjadi Kesalahan Pada Server",data)
            response = json.dumps(response.__dict__)
            return str(response)
        else:
            data = []
            data_lesn = ""
            response = ResponseData("500","Terjadi Kesalahan Pada Server",data)
            response = json.dumps(response.__dict__)
            return str(response)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)