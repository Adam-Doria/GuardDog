# modules/deepface_detector.py

import cv2
from deepface import DeepFace
import os
import threading
import time

from .observer_pattern import Observer
from .pidog_state      import PiDogState
from config            import DEEPFACE_CUDA_VISIBLE_DEVICES, DEEPFACE_FRAME_SKIP

_try_vilib = False 

os.environ["CUDA_VISIBLE_DEVICES"] = DEEPFACE_CUDA_VISIBLE_DEVICES

class DeepFaceDetector(Observer):
    """
    Gère la détection de genre via DeepFace dans un thread séparé,
    **uniquement** sur la webcam PC (cv2.VideoCapture).
    Observe PiDogState pour savoir quand démarrer ou arrêter.
    """
    def __init__(self, on_man_detected_callback):
        self._on_man_detected_callback = on_man_detected_callback
        self._detection_thread = None
        self._running = False
        self._stop_event = threading.Event()
        self._is_active_for_detection = False
        self._man_detection_streak = 0 

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

    def stop_detection(self):
        """Arrête la thread de détection en cours (si active)."""
        if self._running:
            print("DeepFaceDetector: Signal d'arrêt envoyé au thread de détection...")
            self._running = False
            self._stop_event.set()
            self._man_detection_streak = 0 
            if self._detection_thread and self._detection_thread.is_alive():
                self._detection_thread.join(timeout=5)
                if self._detection_thread.is_alive():
                    print("DeepFaceDetector: Thread de détection n'a pas pu s'arrêter proprement.")
            print("DeepFaceDetector: Thread de détection arrêté.")

    def _detection_loop(self):
        """
        Boucle permanente qui lit la frame depuis la webcam PC,
        puis envoie à DeepFace.analyze toutes les DEEPFACE_FRAME_SKIP images.
        """
        print(f"DeepFaceDetector: (_try_vilib = {_try_vilib}) → tentative d'ouverture de VideoCapture(0)…")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("DeepFaceDetector: Impossible d'ouvrir la webcam locale.")
            return
        print("DeepFaceDetector: Webcam locale ouverte avec succès, début du loop.")

        frame_count = 0

        while self._running and not self._stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print("DeepFaceDetector: Erreur lecture webcam.")
                break

            frame = cv2.flip(frame, 1)
            frame_count += 1

            if self._is_active_for_detection and (frame_count % DEEPFACE_FRAME_SKIP == 0):
                faces_detected_in_frame = []
                try:
                    results = DeepFace.analyze(
                        img_path=frame,
                        actions=["gender"],
                        enforce_detection=True,
                        detector_backend="opencv"
                    )
                    if results:
                        faces_detected_in_frame = [results] if isinstance(results, dict) else results
                 
                except ValueError:
                    print("DeepFaceDetector: Pas de visage détecté ou erreur de format pour cette frame.")
                    faces_detected_in_frame = []
                except Exception as e:
                    print(f"DeepFaceDetector: Erreur inattendue DeepFace : {e}")
                    faces_detected_in_frame = []

                found_man_in_current_analyzed_frame = False
                for face_info in faces_detected_in_frame:
                    print(f"DeepFaceDetector: Analyse de visage: {face_info}")
                    dominant_gender = face_info.get("dominant_gender")
                    gender_scores = face_info.get("gender", {})
                    man_prob = gender_scores.get("Man", 0)

                    if dominant_gender == "Man" and man_prob > 85:
                        print(f"DeepFaceDetector: Homme détecté ! Proba Man={man_prob:.2f}%")
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
                    print("DeepFaceDetector: Homme détecté 3 fois consécutives, envoi de l'alerte !")
                    self._on_man_detected_callback("Man")
                    
                    self._is_active_for_detection = False
                    self._running = False
                    self._man_detection_streak = 0

            time.sleep(0.01)

        cap.release()
        print("DeepFaceDetector: Boucle de détection terminée.")