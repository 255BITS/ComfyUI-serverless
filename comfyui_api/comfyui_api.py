
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
from websocket import WebSocket # note: websocket-client (https://github.com/websocket-client/websocket-client)
import io
import requests
import time
import os
import subprocess
from typing import List
import sys

APP_NAME = os.getenv('APP_NAME') if os.getenv('APP_NAME') is not None else 'COMFY_SERVERLESS' # Name of the application
API_COMMAND_LINE = os.getenv('API_COMMAND_LINE') if os.getenv('API_COMMAND_LINE') is not None else 'python3 ComfyUI/main.py' # Command line to start the API server, e.g. "python3 ComfyUI/main.py"; warning: do not add parameter --port as it will be passed later
TEST_PAYLOAD = json.load(open(os.getenv('TEST_PAYLOAD'))) if os.getenv('TEST_PAYLOAD') is not None else json.load(open('test_payload.json')) # The TEST_PAYLOAD is a JSON object that contains a prompt that will be used to test if the API server is running
MAX_COMFY_START_ATTEMPTS = int(os.getenv('MAX_COMFY_START_ATTEMPTS')) if os.getenv('MAX_COMFY_START_ATTEMPTS') is not None else 10  # Set this to the maximum number of connection attempts to ComfyUI you want
COMFY_START_ATTEMPTS_SLEEP = float(os.getenv('COMFY_START_ATTEMPTS_SLEEP')) if os.getenv('COMFY_START_ATTEMPTS_SLEEP') is not None else 1 # The waiting time for each reattempt to connect to ComfyUI

INSTANCE_IDENTIFIER = APP_NAME+'-'+str(uuid.uuid4()) # Unique identifier for this instance of the worker; used in the WebSocket connection

class ComfyAPI:
    _instance = None
    _process = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ComfyAPI, cls).__new__(cls)
        return cls._instance

    def __init__(self, url="localhost:7777"):
        self.server_address = "https://"+url
        self.client_id = INSTANCE_IDENTIFIER
        self.ws_address = f"ws://{url}/ws?clientId={self.client_id}"
        self.ws = WebSocket()

    def is_api_running(self): # This method is used to check if the API server is running
        test_payload = TEST_PAYLOAD
        try:
            print(f"Checking web server is running in {self.server_address}...")
            response = requests.get(self.server_address)
            if response.status_code == 200: # Check if the API server tells us it's running by returning a 200 status code
                self.ws.connect(self.ws_address)
                print(f"Web server is running (status code 200). Now trying test image...")
                test_image = self.generate_images(test_payload)
                print(f"Type of test_image: {type(test_image)}")
                print(f"Test image: {test_image}")
                if test_image is not None:  # this ensures that the API server is actually running and not just the web server
                    return True
                return False
        except Exception as e:
            print("API not running:", e)
            return False

    def get_history(self, prompt_id): # This method is used to retrieve the history of a prompt from the API server
        with urllib.request.urlopen(f"{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def get_image(self, filename, subfolder, folder_type): # This method is used to retrieve an image from the API server
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"{self.server_address}/view?{url_values}") as response:
            return response.read()

    def queue_prompt(self, prompt): # This method is used to queue a prompt for execution
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        headers = {'Content-Type': 'application/json'}  # Set Content-Type header
        req = urllib.request.Request(f"{self.server_address}/prompt", data=data, headers=headers)
        return json.loads(urllib.request.urlopen(req).read())

    def generate_images(self, payload, delete=True): # This method is used to generate images from a prompt and is the main method of this class
        try:
            if not self.ws.connected: # Check if the WebSocket is connected to the API server and reconnect if necessary
                print("WebSocket is not connected. Reconnecting...")
                self.ws.connect(self.ws_address)
            prompt_id = self.queue_prompt(payload)['prompt_id']
            while True:
                out = self.ws.recv() # Wait for a message from the API server
                if isinstance(out, str): # Check if the message is a string
                    message = json.loads(out) # Parse the message as JSON
                    if message['type'] == 'executing': # Check if the message is an 'executing' message
                        data = message['data'] # Extract the data from the message
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            break
            address = self.find_output_node(payload) # Find the SaveImage node; workflow MUST contain only one SaveImage node
            history = self.get_history(prompt_id)[prompt_id]
            filenames = eval(f"history['outputs']{address}")['images']  # Extract all images
            images = []
            for img_info in filenames:
                filename = img_info['filename']
                subfolder = img_info['subfolder']
                folder_type = img_info['type']
                image_data = self.get_image(filename, subfolder, folder_type)
                image_file = io.BytesIO(image_data)
                image = Image.open(image_file)
                if delete:
                    os.remove(image_file)
                images.append(image)
            return images
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_no = exc_traceback.tb_lineno
            error_message = f'Unhandled error at line {line_no}: {str(e)}'
            print("generate_images - ", error_message)

    def upload_image(self, filepath, subfolder=None, folder_type=None, overwrite=False):  # This method is used to upload an image to the API server for use in img2img or controlnet
        try: 
            url = f"{self.server_address}/upload/image"
            with open(filepath, 'rb') as file:
                files = {'image': file}
                data = {'overwrite': str(overwrite).lower()}
                if subfolder:
                    data['subfolder'] = subfolder
                if folder_type:
                    data['type'] = folder_type
                response = requests.post(url, files=files, data=data)
            return response.json()
        except Exception as e:
            raise

    @staticmethod
    def find_output_node(json_object): # This method is used to find the node containing the SaveImage class in a prompt
        for key, value in json_object.items():
            if isinstance(value, dict):
                if value.get("class_type") == "SaveImage":
                    return f"['{key}']"  # Return the key containing the SaveImage class
                result = ComfyConnector.find_output_node(value)
                if result:
                    return result
        return None
    
    @staticmethod
    def load_payload(path):
        with open(path, 'r') as file:
            return json.load(file)

    @staticmethod
    def replace_key_value(json_object, target_key, new_value, class_type_list=None, exclude=True): # This method is used to edit the payload of a prompt
        for key, value in json_object.items():
            # Check if the current value is a dictionary and apply the logic recursively
            if isinstance(value, dict):
                class_type = value.get('class_type')                
                # Determine whether to apply the logic based on exclude and class_type_list
                should_apply_logic = (
                    (exclude and (class_type_list is None or class_type not in class_type_list)) or
                    (not exclude and (class_type_list is not None and class_type in class_type_list))
                )
                # Apply the logic to replace the target key with the new value if conditions are met
                if should_apply_logic and target_key in value:
                    value[target_key] = new_value
                # Recurse vertically (into nested dictionaries)
                ComfyConnector.replace_key_value(value, target_key, new_value, class_type_list, exclude)
            # Recurse sideways (into lists)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        ComfyConnector.replace_key_value(item, target_key, new_value, class_type_list, exclude)
