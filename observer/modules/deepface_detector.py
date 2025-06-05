
import cv2

import os
import threading
import time
import requests 
import base64   
from io import BytesIO  
from PIL import Image   

from .observer_pattern import Observer
from .pidog_state      import PiDogState
from config            import DEEPFACE_CUDA_VISIBLE_DEVICES, DEEPFACE_FRAME_SKIP

_try_vilib = False


os.environ["CUDA_VISIBLE_DEVICES"] = DEEPFACE_CUDA_VISIBLE_DEVICES

def np_to_base64(img_np):
    """
    Convert numpy image (RGB) to base64 string
    """
    img = Image.fromarray(img_np.astype('uint8'), 'RGB')
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("ascii")

class DeepFaceDetector(Observer):
    """
    Gère la détection de genre via un service externe (API) dans un thread séparé,
    **uniquement** sur la webcam PC (cv2.VideoCapture).
    Observe PiDogState pour savoir quand démarrer ou arrêter.
    """
    API_URL = "http://52.210.72.244/api/dogguard/genre/detection"

    def __init__(self, on_man_detected_callback):
        self._on_man_detected_callback = on_man_detected_callback
        self._detection_thread = None
        self._running = False
        self._stop_event = threading.Event()
        self._is_active_for_detection = False
        self._man_detection_streak = 0
        print("DeepFaceDetector: Initialisé.")

    def update(self, mode):
        """
        Quand le mode change :
         - Si mode == MODE_PATROL → on active la détection,
         - Si mode == MODE_ALERT  → on stoppe la détection.
        """
        if mode == PiDogState.MODE_PATROL:
            print("DeepFaceDetector: Réactivation de la détection (mode PATROL).")
            self._is_active_for_detection = True
            self.start_detection()
        elif mode == PiDogState.MODE_ALERT:
            print("DeepFaceDetector: Désactivation de la détection (mode ALERT).")
            self._is_active_for_detection = False
            self.stop_detection()
            self._man_detection_streak = 0
        else:
            print(f"DeepFaceDetector: Mode '{mode}' non géré par le détecteur, détection arrêtée.")
            self._is_active_for_detection = False
            self.stop_detection()

    def start_detection(self):
        """Démarre la thread de détection si pas déjà en cours."""
        if not self._running:
            print("DeepFaceDetector: Démarrage du thread de détection...")
            self._running = True
            self._stop_event.clear()
            self._man_detection_streak = 0
            self._detection_thread = threading.Thread(
                target=self._detection_loop, name="DeepFaceThread"
            )
            self._detection_thread.start()
        else:
            print("DeepFaceDetector: La détection est déjà en cours.")


    def stop_detection(self):
        """Arrête la thread de détection en cours (si active)."""
        if self._running:
            print("DeepFaceDetector: Signal d'arrêt envoyé au thread de détection...")
            self._running = False
            self._stop_event.set()
            self._man_detection_streak = 0
            if self._detection_thread and self._detection_thread.is_alive():
                self._detection_thread.join(timeout=5) # Attendre que le thread se termine
                if self._detection_thread.is_alive():
                    print("DeepFaceDetector: Thread de détection n'a pas pu s'arrêter proprement.")
                else:
                    print("DeepFaceDetector: Thread de détection arrêté avec succès.")
            else:
                print("DeepFaceDetector: Le thread de détection n'était pas actif ou n'existait pas.")
        else:
            print("DeepFaceDetector: La détection n'est pas en cours, rien à arrêter.")


    def _detection_loop(self):
        """
        Boucle permanente qui lit la frame depuis la webcam PC,
        puis envoie à l'API de détection toutes les DEEPFACE_FRAME_SKIP images.
        """
        print(f"DeepFaceDetector: (_try_vilib = {_try_vilib}) → tentative d'ouverture de VideoCapture(0)…")
        cap = cv2.VideoCapture(0) 
        if not cap.isOpened():
            print("DeepFaceDetector: IMPOSSIBLE d'ouvrir la webcam locale. Arrêt du thread de détection.")
            self._running = False 
            return
        print("DeepFaceDetector: Webcam locale ouverte avec succès, début du loop.")

        frame_count = 0

        while self._running and not self._stop_event.is_set():
            ret, frame = cap.read() 
            if not ret:
                print("DeepFaceDetector: Erreur lecture webcam. Tentative de reconnexion ou arrêt.")
                break 
            
            frame = cv2.flip(frame, 1)
            frame_count += 1

            if self._is_active_for_detection and (frame_count % DEEPFACE_FRAME_SKIP == 0):
               
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                base64_image_data = np_to_base64(frame_rgb)

                payload = {"data":{ "frame":base64_image_data}}
                headers = {"Content-Type": "application/json"}
                faces_detected_in_frame = []

                try:
                   
                    response = requests.post(self.API_URL, json=payload, headers=headers, timeout=10) 
                    response.raise_for_status() 

                    api_response = response.json()
                   
                    if isinstance(api_response, dict) and "detections" in api_response:
                        faces_detected_in_frame = api_response.get("detections", [])
                    elif isinstance(api_response, list):
                        faces_detected_in_frame = api_response
                    elif isinstance(api_response, dict) and (api_response.get("dominant_gender") or api_response.get("gender")):
                        faces_detected_in_frame = [api_response]
                    else:
                        print(f"DeepFaceDetector: Format de réponse API inattendu: {api_response}")
                        faces_detected_in_frame = []

                except requests.exceptions.Timeout:
                    print("DeepFaceDetector: Requête API expirée (timeout).")
                    faces_detected_in_frame = []
                except requests.exceptions.ConnectionError as ce:
                    print(f"DeepFaceDetector: Erreur de connexion à l'API: {ce}")
                    faces_detected_in_frame = []
                except requests.exceptions.HTTPError as he:
                    print(f"DeepFaceDetector: Erreur HTTP de l'API: {he.response.status_code} - {he.response.text}")
                    faces_detected_in_frame = []
                except Exception as e:
                    print(f"DeepFaceDetector: Erreur inattendue lors de l'appel API: {e}")
                    faces_detected_in_frame = []

                found_man_in_current_analyzed_frame = False
                for face_info in faces_detected_in_frame:
                    print(f"DeepFaceDetector: Analyse de visage (via API): {face_info}")
                    dominant_gender = face_info.get("dominant_gender")
                    gender_scores = face_info.get("gender", {})
                    man_prob = gender_scores.get("Man", 0)

                    if isinstance(man_prob, (int, float)) and dominant_gender == "Man" and man_prob > 85:
                        print(f"DeepFaceDetector: Homme détecté via API ! Proba Man={man_prob:.2f}%")
                        found_man_in_current_analyzed_frame = True
                        break 

                if found_man_in_current_analyzed_frame:
                    self._man_detection_streak += 1
                    print(f"DeepFaceDetector: Série de détections d'homme: {self._man_detection_streak} / 2")
                else:
                    if self._man_detection_streak > 0:
                        print(f"DeepFaceDetector: Pas d'homme détecté dans cette frame ou proba trop faible, réinitialisation de la série.")
                    self._man_detection_streak = 0

             
                if self._man_detection_streak >= 2:
                    print("DeepFaceDetector: Homme détecté 2 fois consécutives, envoi de l'alerte !")
                    self._on_man_detected_callback("Man") 
                    
                    self._is_active_for_detection = False
                    self._running = False 
                    self._man_detection_streak = 0
                    print("DeepFaceDetector: Alerte homme envoyée, détection arrêtée.")
                    break

            time.sleep(0.01) 

        cap.release() 
        print("DeepFaceDetector: Boucle de détection terminée.")