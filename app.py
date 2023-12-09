from flask import Flask, abort, request, send_file, jsonify, make_response
from flask_cors import CORS
from tempfile import NamedTemporaryFile
from gtts import gTTS
import whisper
import torch
import requests
import random
import base64
from openai import AzureOpenAI

# Check if NVIDIA GPU is available
torch.cuda.is_available()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Load the Whisper model:
model = whisper.load_model("base", device=DEVICE)

app = Flask(__name__)
CORS(app)

# set up Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),  
    api_version="2023-05-15",#os.getenv('OPEN_API_VERSION'),
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
)

chatgpt_model = "gpt-model-01"

history = [{"role": "system", "content": 'You are a nurse triaging me for mental health risk assessment. Please ask me questions and provide me with a score.'}]

@app.route('/')
def root():
    return app.send_static_file('index.html')


@app.route('/whisper', methods=['POST'])
def handler():
    if not request.files:
        # If the user didn't submit any files, return a 400 (Bad Request) error.
        abort(400)

    # For each file, let's store the results in a list of dictionaries.
    results = []

    # Loop over every file that the user submitted.
    for filename, handle in request.files.items():
        # Create a temporary file.
        # The location of the temporary file is available in `temp.name`.
        temp = NamedTemporaryFile()
        # Write the user's uploaded file to the temporary file.
        # The file will get deleted when it drops out of scope.
        handle.save(temp)
        # Let's get the transcript of the temporary file.
        result = model.transcribe(temp.name)
        # Now we can store the result object for this file.
        results.append({
            'filename': filename,
            'transcript': result['text'],
        })

        print(result['text'], flush=True)

        history.append({"role": "user", "content": result['text']})

        messages = history

        response = client.chat.completions.create(
            model=chatgpt_model,
            messages=messages,
        )

        print(response.choices[0].message.content, flush=True)

        history.append({"role": "system", "content": response.choices[0].message.content})

        result_audio_file = gtts_call(response.choices[0].message.content)
        if result_audio_file:
            return result_audio_file

    # This will be automatically converted to JSON.
    return {'results': results}#result_audio_file#

def gtts_call(text):
    path_to_file = 'file' + str(random.random()) + '.mp3'
    with open(path_to_file, 'wb') as ff:
        gTTS(text=text, lang='en', slow=False).write_to_fp(ff)

    with open(path_to_file, 'rb') as f:
        audio_binary = f.read()
        audio = base64.b64encode(audio_binary).decode("utf-8")
        return jsonify({'status': True, 'audio': audio})
    # return send_file(path_to_file, mimetype="audio/mp3", as_attachment=True, attachment_filename="test.mp3")

def qcri_tts_call(text, model_id='c3cea013-3e43-4ca9-8676-c457ad120ac3'):
    url = 'https://tts.qcri.org/api/submit_job'
    params = {'model_id': model_id, 'is_public':False, 'text': text} # Amina model from TTS
    response = requests.post(url, json = params)

    response = response.json()
    if response['success'] == True:
        job_id = response['job_id']

        status_url = 'https://tts.qcri.org/api/get_status'
        final_status = 'done'

        status_response = requests.post(status_url)
        while (status_response['status'] != final_status):
            status_response = requests.post(status_url)

        final_audio_url = 'https://tts.qcri.org/api/' + job_id + '.wav'
        final_audio_response = requests.get(final+final_audio_url)
        path_to_file = '/audio_files/' + job_id + '.mp3'
        with open(path_to_file, 'wb') as f:
            f.write(doc.content)

        return send_file(path_to_file, mimetype="audio/mp3", as_attachment=True, attachment_filename="test.mp3")
    else:
        return None
    #     qcri_tts_call(text, model_id='bd72a5ac-cfc1-4188-b745-c209ce790338') # Hamza model from TTS


