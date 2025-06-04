# modules/deepface_detector.py

import cv2
from deepface import DeepFace
import os
import threading
import time
import queue

# Importe Vilib directement car c'est la bibliothèque pour la caméra du PiDog
from vilib import Vilib 

from modules.observer_pattern import Observer
from modules.pidog_state import PiDogState # Pour les constantes de mode
from config import DEEPFACE_CUDA_VISIBLE_DEVICES, DEEPFACE_FRAME_SKIP

# Désactive l'utilisation du GPU si configuré
os.environ["CUDA_VISIBLE_DEVICES"] = DEEPFACE_CUDA_VISIBLE_DEVICES

class DeepFaceDetector(Observer):
    """
    Gère la détection de genre via DeepFace dans un thread séparé.
    Observe le PiDogState pour savoir quand démarrer ou arrêter l'analyse.
    Utilise Vilib pour l'accès à la caméra.
    """
    def __init__(self, on_man_detected_callback):
        self._on_man_detected_callback = on_man_detected_callback
        self._detection_thread = None
        self._running = False  # Flag pour contrôler le thread de détection
        self._stop_event = threading.Event() # Événement pour signaler l'arrêt du thread
        self._is_active_for_detection = False # Indique si le détecteur doit activement détecter (basé sur le mode du PiDog)

    def update(self, mode):
        """
        Implémentation de la méthode update de l'Observer.
        Réagit aux changements de mode du PiDogState.
        """
        if mode == PiDogState.MODE_PATROL:
            print("DeepFaceDetector: Réactivation pour la détection (mode Patrouille).")
            self._is_active_for_detection = True
            self.start_detection()
        elif mode == PiDogState.MODE_ALERT:
            print("DeepFaceDetector: Désactivation de la détection (mode Alerte).")
            self._is_active_for_detection = False
            self.stop_detection()

    def start_detection(self):
        """Démarre le thread de détection DeepFace."""
        if not self._running:
            print("DeepFaceDetector: Démarrage du thread de détection...")
            self._running = True
            self._stop_event.clear() # S'assurer que l'événement d'arrêt est effacé
            self._detection_thread = threading.Thread(target=self._detection_loop, name="DeepFaceThread")
            self._detection_thread.start()

    def stop_detection(self):
        """Arrête le thread de détection DeepFace."""
        if self._running:
            print("DeepFaceDetector: Signal d'arrêt envoyé au thread de détection...")
            self._running = False
            self._stop_event.set() # Déclencher l'événement d'arrêt
            if self._detection_thread and self._detection_thread.is_alive():
                self._detection_thread.join(timeout=5) # Attendre la fin du thread
                if self._detection_thread.is_alive():
                    print("DeepFaceDetector: Le thread de détection n'a pas pu s'arrêter proprement.")
            print("DeepFaceDetector: Thread de détection arrêté.")

    def _detection_loop(self):
        """Boucle principale du thread de détection DeepFace."""
        frame_count = 0

        while self._running and not self._stop_event.is_set():
            if not Vilib.flask_start: # Attendre que Vilib ait démarré son serveur Flask
                print("DeepFaceDetector: Vilib.flask_start est False, attente...")
                time.sleep(1)
                continue

            frame = Vilib.img # Obtenir le dernier frame de Vilib
            if frame is None:
                print("DeepFaceDetector: Aucun frame de Vilib.img, attente...")
                time.sleep(0.5)
                continue

            frame_count += 1
            
            # N'effectuer l'analyse que si le détecteur est actif et au bon rythme
            if self._is_active_for_detection and (frame_count % DEEPFACE_FRAME_SKIP == 0):
                try:
                    current_faces_data = DeepFace.analyze(
                        img_path=frame, 
                        actions=['gender'], 
                        enforce_detection=False, # Ne pas lancer d'erreur si aucun visage détecté
                        detector_backend='opencv' 
                    )
                    
                    if current_faces_data:
                        for face_info in current_faces_data:
                            if 'gender' in face_info and isinstance(face_info['gender'], dict):
                                gender_prob = face_info['gender']
                                # Comparer les probabilités pour déterminer le genre dominant
                                if gender_prob.get('Man', 0) > gender_prob.get('Woman', 0):
                                    gender = "Man"
                                    print(f"DeepFaceDetector: Homme détecté! Probabilité: {gender_prob.get('Man', 0):.2f}")
                                    self._on_man_detected_callback(gender) # Déclencher le callback
                                else:
                                    gender = "Woman"
                                    # print(f"DeepFaceDetector: Femme détectée. Probabilité: {gender_prob.get('Woman', 0):.2f}") # Uncomment for debug
                            # else:
                                # print("DeepFaceDetector: Données de genre inattendues.") # Uncomment for debug
                except ValueError as e:
                    # print(f"DeepFace: Aucun visage détecté ou confiance trop basse. {e}") # Uncomment for debug
                    pass # C'est normal de ne pas toujours détecter de visage
                except Exception as e:
                    print(f"DeepFaceDetector: ERREUR INATTENDUE lors de l'analyse : {e}")
                    pass 
            
            # Petite pause pour ne pas saturer le CPU/GPU et laisser d'autres threads s'exécuter
            time.sleep(0.01) 
        
        print("DeepFaceDetector: Boucle de détection terminée.")