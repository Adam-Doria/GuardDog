Excellent point ! Effective modularization is indeed crucial for a clean, maintainable, and scalable project. My apologies for the initial oversight.

Based on the provided PiDog library structure and your existing Node.js backend, I will refactor the Python code to integrate seamlessly and adhere to a clear separation of concerns.

Here's the detailed breakdown and the updated code for each module, assuming your `sunfounder-pidog` library is installed and accessible in your Python environment.

---

## Nouvelle structure des fichiers (projet PiDog)

```
your_project_root/
├── main.py
├── config.py
├── modules/
│   ├── observer_pattern.py
│   ├── pidog_state.py
│   ├── pidog_hardware_interface.py  # Now directly controls PiDog
│   ├── deepface_detector.py         # Uses Vilib for camera input
│   └── socket_client.py
└── pidog_controller.py
```

### Explication de la nouvelle structure et intégration du PiDog réel

1.  **`config.py`**: Contient les constantes de configuration, y compris l'ID du robot et l'URL du serveur Socket.IO.
2.  **`modules/observer_pattern.py`**: Classes génériques `Subject` et `Observer` pour le découplage.
3.  **`modules/pidog_state.py`**: Le sujet de l'Observer, gérant l'état `Patrol` ou `Alert` du chien.
4.  **`modules/pidog_hardware_interface.py`**:
    *   C'est ici que le chien réel `Pidog` est instancié.
    *   Il expose des méthodes de haut niveau (`start_patrol`, `stop_patrol`, `start_barking`, `stop_barking`, `get_distance`, `set_rgb_mode`) qui encapsulent les appels à la bibliothèque `Pidog`.
    *   Il contient des actions `do_action` pour les patrouilles.
5.  **`modules/deepface_detector.py`**:
    *   Observateur de l'état du chien.
    *   Il utilise `Vilib` (fourni avec la bibliothèque PiDog) pour accéder au flux vidéo.
    *   Il analyse les frames avec `DeepFace` et notifie le contrôleur si un homme est détecté.
    *   S'exécute dans un thread séparé pour ne pas bloquer le chien.
6.  **`modules/socket_client.py`**: Gère la connexion et l'émission/réception d'événements Socket.IO, y compris l'enregistrement du robot et les alertes.
7.  **`pidog_controller.py`**: Le contrôleur principal qui :
    *   Instancie tous les modules.
    *   Enregistre les observateurs.
    *   Gère la logique de haut niveau (déclenchement des alertes, changement de mode suite aux commandes Socket.IO ou aux détections).
    *   Contient la logique de la boucle de patrouille.
8.  **`main.py`**: Le point d'entrée minimaliste du programme.

---

## Le Code Modularisé et Intégré

Assurez-vous que les fichiers sont placés dans la structure de répertoires indiquée.

### `config.py`

```python
# config.py
# Fichier de configuration pour le projet PiDog

# URL du serveur Socket.IO
SOCKET_IO_SERVER_URL = "http://127.0.0.1:4500" 

# Identifiant unique pour ce PiDog (important pour le serveur Node.js)
ROBOT_ID = "pidog-sunfounder-001" 

# Paramètres DeepFace
# Désactive l'utilisation du GPU pour DeepFace, utile sur Raspberry Pi
DEEPFACE_CUDA_VISIBLE_DEVICES = "-1" 
# Nombre de frames à sauter avant chaque analyse DeepFace (pour économiser les ressources)
DEEPFACE_FRAME_SKIP = 48 
# Seuil de distance pour la patrouille (en cm)
PATROL_DANGER_DISTANCE_CM = 20

# Durée de l'aboiement d'alerte (en secondes)
ALERT_BARK_DURATION_SEC = 3 
```

---

### `modules/observer_pattern.py`

*(Ce fichier reste inchangé)*

```python
# modules/observer_pattern.py

class Subject:
    """
    Sujet (Subject) dans le pattern Observer.
    Peut enregistrer, désenregistrer et notifier des observateurs.
    """
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)
            # print(f"Observer attaché: {observer.__class__.__name__}") # Uncomment for debug

    def detach(self, observer):
        try:
            self._observers.remove(observer)
            # print(f"Observer détaché: {observer.__class__.__name__}") # Uncomment for debug
        except ValueError:
            pass

    def notify_observers(self, *args, **kwargs):
        """Notifie tous les observateurs attachés."""
        for observer in self._observers:
            observer.update(*args, **kwargs)

class Observer:
    """
    Interface de l'Observateur (Observer) dans le pattern Observer.
    Toute classe qui veut "observer" un Subject doit implémenter cette méthode.
    """
    def update(self, *args, **kwargs):
        """
        Méthode appelée par le Subject pour notifier l'Observer d'un changement.
        Doit être implémentée par les sous-classes.
        """
        raise NotImplementedError("La méthode 'update' doit être implémentée par la sous-classe.")

```

---

### `modules/pidog_state.py`

*(Ce fichier reste inchangé)*

```python
# modules/pidog_state.py

from modules.observer_pattern import Subject

class PiDogState(Subject):
    """
    Gère l'état actuel du PiDog (Patrouille ou Alerte).
    Agit comme un Subject dans le pattern Observer, notifiant ses observateurs
    lorsque l'état change.
    """
    MODE_PATROL = "patrol"
    MODE_ALERT = "alert"

    def __init__(self):
        super().__init__()
        self._current_mode = self.MODE_PATROL
        print(f"PiDogState: Démarré en mode: {self._current_mode.upper()}")

    @property
    def current_mode(self):
        return self._current_mode

    def set_patrol_mode(self):
        """Change le mode du PiDog en PATROUILLE."""
        if self._current_mode != self.MODE_PATROL:
            self._current_mode = self.MODE_PATROL
            print(f"PiDogState: Changement d'état: Mode PATROUILLE activé.")
            self.notify_observers(mode=self._current_mode)
        # else:
            # print("PiDogState: Déjà en mode PATROUILLE.") # Uncomment for debug

    def set_alert_mode(self):
        """Change le mode du PiDog en ALERTE."""
        if self._current_mode != self.MODE_ALERT:
            self._current_mode = self.MODE_ALERT
            print(f"PiDogState: Changement d'état: Mode ALERTE activé!")
            self.notify_observers(mode=self._current_mode)
        # else:
            # print("PiDogState: Déjà en mode ALERTE.") # Uncomment for debug

```

---

### `modules/pidog_hardware_interface.py`

*(Ce fichier est grandement modifié pour utiliser la bibliothèque `Pidog` réelle)*

```python
# modules/pidog_hardware_interface.py

import time
import os
from pidog import Pidog # Importe la classe Pidog de la bibliothèque SunFounder
from vilib import Vilib # Importe Vilib pour la caméra
from config import PATROL_DANGER_DISTANCE_CM, ALERT_BARK_DURATION_SEC

class PiDogHardware:
    """
    Interface réelle pour contrôler le PiDog SunFounder.
    Encapsule les appels à la bibliothèque Pidog.
    """
    def __init__(self):
        print("PiDogHardware: Initialisation de l'interface matérielle réelle...")
        try:
            self.my_dog = Pidog() # Instancie le chien Pidog
            print("PiDogHardware: Pidog initialisé.")
            # Initialiser la caméra Vilib une seule fois au démarrage
            Vilib.camera_start(vflip=False, hflip=False)
            Vilib.display(local=False, web=True) # Affichage web de la caméra si nécessaire
            # Attendre que le serveur Flask de Vilib soit prêt (vu dans gpt_examples/gpt_dog.py)
            while not Vilib.flask_start:
                time.sleep(0.01)
            print("PiDogHardware: Caméra Vilib démarrée.")
        except Exception as e:
            print(f"PiDogHardware ERROR: Impossible d'initialiser Pidog ou Vilib: {e}")
            # Gérer l'erreur, potentiellement quitter ou fonctionner en mode dégradé
            self.my_dog = None # Assurez-vous que my_dog est None si l'initialisation échoue
            raise RuntimeError(f"Échec de l'initialisation du matériel PiDog: {e}")

    def _wait_dog_actions_done(self):
        """Attends que toutes les actions du chien soient terminées."""
        if self.my_dog:
            self.my_dog.wait_all_done()
            time.sleep(0.1) # Petite pause pour laisser le temps aux servos de se stabiliser

    def start_patrol(self):
        """Met le chien en mode patrouille (mouvements) et allume la lumière."""
        if not self.my_dog: return
        print("PiDogHardware: Démarrage de la patrouille.")
        self.my_dog.rgb_strip.set_mode('breath', 'white', bps=0.5)
        self.my_dog.do_action('stand', speed=80)
        self._wait_dog_actions_done()
        self.my_dog.do_action('forward', step_count=2, speed=98)
        self._wait_dog_actions_done()
        # Simulation d'un virage aléatoire ou autre logique de patrouille
        # Pour une patrouille continue, on laisserait 'forward' dans une boucle externe ou ici.
        # Ici, j'ajoute un virage pour l'exemple.
        self.my_dog.do_action('turn_left', step_count=1, speed=98)
        self._wait_dog_actions_done()


    def stop_patrol(self):
        """Arrête les mouvements de patrouille du chien."""
        if not self.my_dog: return
        print("PiDogHardware: Arrêt de la patrouille.")
        self.my_dog.body_stop()
        self.my_dog.rgb_strip.close() # Éteindre la lumière ou changer de mode
        self._wait_dog_actions_done()

    def start_barking(self):
        """Fait aboyer le chien et change le mode RGB en alerte."""
        if not self.my_dog: return
        print("PiDogHardware: Début des aboiements (alerte)!")
        self.my_dog.rgb_strip.set_mode('bark', 'red', bps=2)
        # Utiliser un aboiement plus "agressif"
        self.my_dog.speak('angry', volume=100) # Assurez-vous que 'angry.mp3' ou 'angry.wav' existe dans sounds/
        # Optionnel: faire une posture d'alerte
        self.my_dog.do_action('sit', speed=70) # ou une autre action d'alerte
        self._wait_dog_actions_done()

    def stop_barking(self):
        """Arrête les aboiements du chien."""
        if not self.my_dog: return
        print("PiDogHardware: Arrêt des aboiements.")
        # La bibliothèque Pidog ne semble pas avoir un stop_sound direct pour un son en cours.
        # On peut soit laisser le son se terminer, soit changer rapidement de mode pour l'interrompre.
        # Pour cet exemple, nous allons juste attendre que le son se termine si c'était un son court,
        # ou changer le mode RGB pour indiquer la fin de l'alerte.
        self.my_dog.rgb_strip.set_mode('breath', 'white', bps=0.5) # Retour à une lumière neutre
        # Le music.sound_play_threading est non bloquant, donc il n'y a pas de "stop" direct ici,
        # le son se termine de lui-même après sa durée.

    def get_distance(self):
        """Lit la distance du capteur ultrasonique."""
        if not self.my_dog: return -1
        return self.my_dog.read_distance()

    def get_vilib_image(self):
        """Retourne le dernier frame de la caméra Vilib."""
        if not Vilib.flask_start: # S'assurer que Vilib est démarré
            return None
        return Vilib.img

    def close_all_hardware(self):
        """Arrête toutes les actions du chien et ferme la caméra Vilib."""
        if not self.my_dog: return
        print("PiDogHardware: Arrêt de toutes les actions matérielles et fermeture de la caméra.")
        self.my_dog.close() # Méthode de nettoyage complète de la classe Pidog
        Vilib.camera_close()
        print("PiDogHardware: Matériel PiDog et Vilib fermés.")

```

---

### `modules/deepface_detector.py`

*(Modifié pour utiliser `Vilib`)*

```python
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

```

---

### `modules/socket_client.py`

*(Adapté pour les noms d'événements du serveur Node.js)*

```python
# modules/socket_client.py

import socketio
import time

class SocketIOClient:
    """
    Client Socket.IO pour la communication avec l'application web.
    """
    def __init__(self, server_url, robot_id, on_alert_lifted_callback, on_connect_callback, on_disconnect_callback):
        self.sio = socketio.Client()
        self.server_url = server_url
        self.robot_id = robot_id # L'ID du robot
        self._on_alert_lifted_callback = on_alert_lifted_callback
        self._on_connect_callback = on_connect_callback
        self._on_disconnect_callback = on_disconnect_callback
        self._register_events()

    def _register_events(self):
        """Enregistre les gestionnaires d'événements Socket.IO."""
        @self.sio.event
        def connect():
            print("SocketIO: Connecté au serveur!")
            # Une fois connecté, s'enregistrer comme un robot
            self.sio.emit('register', {'type': 'robot', 'id': self.robot_id})
            print(f"SocketIO: Événement 'register' émis pour le robot ID: {self.robot_id}")
            self._on_connect_callback()

        @self.sio.event
        def disconnect():
            print("SocketIO: Déconnecté du serveur.")
            self._on_disconnect_callback()

        @self.sio.on('disableAlert') # Écoute l'événement 'disableAlert' du serveur Node.js
        def on_disable_alert(data):
            print(f"SocketIO: Message 'disableAlert' reçu: {data}")
            self._on_alert_lifted_callback()

        @self.sio.event
        def message(data):
            print(f"SocketIO: Message générique reçu: {data}")

    def connect(self):
        """Tente de se connecter au serveur Socket.IO."""
        try:
            print(f"SocketIO: Tentative de connexion à {self.server_url}...")
            self.sio.connect(self.server_url, transports=['websocket'])
        except Exception as e:
            print(f"SocketIO ERROR: Impossible de se connecter au serveur: {e}")

    def disconnect(self):
        """Déconnecte du serveur Socket.IO."""
        if self.sio.connected:
            self.sio.disconnect()
            print("SocketIO: Déconnexion initiée.")

    def emit_intruder_detected(self, payload):
        """Émet l'événement 'intruderDetected' vers le serveur Socket.IO."""
        if self.sio.connected:
            # Assurez-vous d'inclure le robotId dans le payload
            payload['robotId'] = self.robot_id 
            self.sio.emit('intruderDetected', payload)
            print(f"SocketIO: Événement 'intruderDetected' émis avec données: {payload}")
        else:
            print(f"SocketIO ERROR: Non connecté, impossible d'émettre l'événement 'intruderDetected'.")

```

---

### `pidog_controller.py`

*(Le cœur de la logique, observe l'état et orchestre les autres modules)*

```python
# pidog_controller.py
import time
import threading

from modules.observer_pattern import Observer
from modules.pidog_state import PiDogState
from modules.pidog_hardware_interface import PiDogHardware
from modules.deepface_detector import DeepFaceDetector
from modules.socket_client import SocketIOClient
from config import SOCKET_IO_SERVER_URL, ROBOT_ID, PATROL_DANGER_DISTANCE_CM, ALERT_BARK_DURATION_SEC

class PiDogController(Observer):
    """
    Contrôleur principal du PiDog.
    Il orchestre les états du chien, la détection DeepFace, la communication Socket.IO
    et les actions matérielles du PiDog.
    Agit comme un Observer de son propre PiDogState pour déclencher les actions physiques.
    """
    def __init__(self):
        print("PiDogController: Initialisation du contrôleur...")
        # 1. Initialiser les modules internes
        self.pidog_state = PiDogState()
        self.pidog_hardware = PiDogHardware() # La vraie interface matérielle
        
        # 2. Initialiser le détecteur DeepFace avec un callback vers ce contrôleur
        self.deepface_detector = DeepFaceDetector(
            on_man_detected_callback=self._on_man_detected
        )
        
        # 3. Initialiser le client Socket.IO avec des callbacks et l'ID du robot
        self.socket_client = SocketIOClient(
            server_url=SOCKET_IO_SERVER_URL,
            robot_id=ROBOT_ID, 
            on_alert_lifted_callback=self._on_alert_lifted_from_app,
            on_connect_callback=self._on_socket_connect,
            on_disconnect_callback=self._on_socket_disconnect
        )
        
        # 4. Enregistrer les observateurs auprès du PiDogState
        # Le DeepFaceDetector observe l'état pour savoir quand détecter
        self.pidog_state.attach(self.deepface_detector)
        # Le PiDogController lui-même observe l'état pour déclencher les actions matérielles
        self.pidog_state.attach(self) 
        
        self._running = False
        self._patrol_thread = None
        self._patrol_stop_event = threading.Event()

    def _on_socket_connect(self):
        """Callback appelé lorsque le client Socket.IO se connecte au serveur."""
        print("PiDogController: Socket.IO connecté. Prêt à démarrer la patrouille.")
        self.pidog_state.set_patrol_mode() 

    def _on_socket_disconnect(self):
        """Callback appelé lorsque le client Socket.IO se déconnecte du serveur."""
        print("PiDogController: Socket.IO déconnecté.")
        self.pidog_hardware.stop_all_hardware() # Arrête tout en cas de perte de connexion

    def _on_man_detected(self, gender):
        """Callback appelé par DeepFaceDetector lorsqu'un homme est détecté."""
        if self.pidog_state.current_mode == PiDogState.MODE_PATROL:
            print(f"PiDogController: Détection de '{gender}' en mode patrouille. Passage en mode ALERTE.")
            self.pidog_state.set_alert_mode() 
            self._trigger_alert(gender)

    def _on_alert_lifted_from_app(self):
        """Callback appelé par SocketIOClient lorsque l'alerte est levée par l'application (via 'disableAlert')."""
        if self.pidog_state.current_mode == PiDogState.MODE_ALERT:
            print("PiDogController: Alerte levée par l'application. Retour en mode PATROUILLE.")
            self.pidog_state.set_patrol_mode() 

    def _trigger_alert(self, detected_gender):
        """Actions spécifiques à effectuer lors du déclenchement d'une alerte."""
        print("PiDogController: Déclenchement de l'alerte (émission Socket.IO)...")
        self.socket_client.emit_intruder_detected({'detected_gender': detected_gender, 'timestamp': time.time()})

    def _patrol_loop(self):
        """Boucle de patrouille du chien."""
        while not self._patrol_stop_event.is_set():
            if self.pidog_state.current_mode == PiDogState.MODE_PATROL:
                distance = self.pidog_hardware.get_distance()
                print(f"Patrol: Distance: {distance} cm")

                if 0 < distance < PATROL_DANGER_DISTANCE_CM:
                    print(f"Patrol: Obstacle détecté à {distance}cm. Alerte imminente ou évitement.")
                    # Ici, on pourrait soit déclencher une alerte, soit initier un comportement d'évitement.
                    # Pour cet exemple, nous allons juste aboyer une fois et tourner pour ne pas rester bloqué.
                    self.pidog_hardware.start_barking()
                    time.sleep(ALERT_BARK_DURATION_SEC) # Aboiement pour signaler l'obstacle
                    self.pidog_hardware.stop_barking()
                    self.pidog_hardware.my_dog.do_action('turn_right', step_count=1, speed=90)
                    self.pidog_hardware.my_dog.wait_all_done()
                else:
                    self.pidog_hardware.start_patrol() # Continue la patrouille

            time.sleep(1) # Vérifier l'état de patrouille toutes les secondes

    def update(self, mode):
        """
        Implémentation de la méthode update de l'Observer.
        Le PiDogController réagit aux changements d'état de PiDogState
        pour déclencher les actions matérielles du chien.
        """
        print(f"PiDogController: Mise à jour basée sur le mode: {mode}")
        if mode == PiDogState.MODE_PATROL:
            self._patrol_stop_event.clear() # Réinitialiser l'événement d'arrêt
            if not self._patrol_thread or not self._patrol_thread.is_alive():
                self._patrol_thread = threading.Thread(target=self._patrol_loop, name="PatrolThread")
                self._patrol_thread.start()
            self.pidog_hardware.stop_barking()
            # La logique de patrouille est gérée dans _patrol_loop
            
        elif mode == PiDogState.MODE_ALERT:
            self._patrol_stop_event.set() # Signaler l'arrêt de la patrouille
            if self._patrol_thread and self._patrol_thread.is_alive():
                self._patrol_thread.join(timeout=1) # Attendre que la boucle de patrouille s'arrête
            self.pidog_hardware.stop_patrol() # S'assurer que le mouvement est arrêté
            self.pidog_hardware.start_barking() # Commence à aboyer

        # Mettre le chien en position neutre après le changement de mode
        self.pidog_hardware.my_dog.wait_all_done()
        self.pidog_hardware.my_dog.do_action('stand', speed=80) # Rester debout pour les détections
        self.pidog_hardware.my_dog.wait_all_done()


    def start(self):
        """Démarre le contrôleur principal du PiDog."""
        print("PiDogController: Démarrage de la logique du chien.")
        self._running = True
        self.socket_client.connect() # La connexion Socket.IO est le point de départ
                                     # Après la connexion, le mode patrouille sera défini.

    def stop(self):
        """Arrête le contrôleur du PiDog et toutes ses fonctions."""
        print("PiDogController: Arrêt de la logique du chien.")
        self._running = False
        
        # Signaler l'arrêt de la patrouille
        self._patrol_stop_event.set()
        if self._patrol_thread and self._patrol_thread.is_alive():
            self._patrol_thread.join(timeout=2) # Attendre que la boucle de patrouille s'arrête

        # Détacher les observateurs pour un arrêt propre
        self.pidog_state.detach(self.deepface_detector)
        self.pidog_state.detach(self) 

        # Arrêter les modules
        self.deepface_detector.stop_detection()
        self.socket_client.disconnect()
        self.pidog_hardware.close_all_hardware() # Appelle la fonction de nettoyage complète du PiDog
        print("PiDogController: Tous les modules arrêtés.")

```

---

### `main.py`

*(Point d'entrée principal)*

```python
# main.py
import time
from pidog_controller import PiDogController

def main():
    """
    Fonction principale qui initialise et gère le cycle de vie du PiDogController.
    """
    controller = None
    try:
        controller = PiDogController()
        controller.start()
        print("main.py: Le contrôleur PiDog est en cours d'exécution. Appuyez sur Ctrl+C pour quitter.")
        # Garde le thread principal en vie pour que les threads secondaires (SocketIO, DeepFace, Patrol) fonctionnent
        while controller._running:
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("\nmain.py: Arrêt demandé par l'utilisateur (Ctrl+C).")
    except Exception as e:
        print(f"\nmain.py ERROR: Une erreur inattendue est survenue: {e}")
    finally:
        if controller:
            controller.stop()
        print("main.py: Application PiDog terminée.")

if __name__ == "__main__":
    main()
```

---

## Étapes pour faire fonctionner ce code :

1.  **Prérequis du PiDog (très important !) :**
    *   Assurez-vous que votre Raspberry Pi a la bibliothèque SunFounder PiDog installée, y compris `robot-hat` et `vilib`, comme spécifié dans votre `README.md` (`i2samp.sh`, `setup.py` etc.). Si ce n'est pas déjà fait, suivez scrupuleusement les étapes d'installation de la documentation SunFounder pour le PiDog.
    *   La caméra doit être activée et fonctionnelle sur votre Raspberry Pi.

2.  **Installation des dépendances Python :**
    Dans l'environnement de votre PiDog, assurez-vous d'avoir :
    ```bash
    pip install python-socketio opencv-python deepface
    ```
    *Note: L'installation de `deepface` peut être longue sur un Raspberry Pi et nécessite de la RAM. Vous pourriez avoir besoin de créer un swap file plus grand si la RAM est insuffisante.*

3.  **Créez la structure de dossiers** comme suit :
    ```
    your_project_root/
    ├── main.py
    ├── config.py
    ├── modules/
    │   ├── observer_pattern.py
    │   ├── pidog_state.py
    │   ├── pidog_hardware_interface.py
    │   ├── deepface_detector.py
    │   └── socket_client.py
    └── pidog_controller.py
    ```
    Placez le code de chaque module dans le fichier correspondant.

4.  **Mettre à jour `config.py` :**
    Vérifiez que `SOCKET_IO_SERVER_URL` correspond à l'adresse de votre serveur Node.js (par défaut `http://127.0.0.1:4500`).
    L'ID du robot (`ROBOT_ID`) doit être unique si vous avez plusieurs PiDogs.

5.  **Lancez votre serveur Node.js :**
    Naviguez dans le dossier `back-robot` et assurez-vous que votre serveur Socket.IO est en cours d'exécution.
    ```bash
    cd back-robot
    npm install # Si pas déjà fait
    npm start   # Ou node main.js
    ```
    Vous devriez voir `Socket.IO serveur en écoute sur http://[votre_ip]:4500`.

6.  **Lancez le script Python du PiDog :**
    Naviguez dans le dossier `your_project_root` (le dossier qui contient `main.py` et le dossier `modules/`) et exécutez :
    ```bash
    python main.py
    ```

### Comportement attendu :

*   Le PiDog devrait se connecter au serveur Socket.IO et s'enregistrer.
*   Il devrait démarrer en mode patrouille, effectuer des mouvements (simulés ici par `do_action('forward')` puis `turn_left`), et activer la détection DeepFace.
*   Si un "Homme" est détecté par la caméra, le chien passera en mode alerte : il arrêtera sa patrouille, "aboyera" (simulé par `my_dog.speak('angry')` et changera le motif de ses LEDs. Une alerte sera envoyée au serveur Node.js.
*   Si vous envoyez un `disableAlert` depuis votre application web (par exemple, en accédant à `http://localhost:3000/lift-alert` ou via un bouton dans votre React app), le PiDog devrait repasser en mode patrouille, arrêter d'aboyer et reprendre ses mouvements.
*   Le capteur ultrasonique sera lu en continu pendant la patrouille pour éviter les obstacles.

Cette structure est beaucoup plus claire et modulaire, vous permettant de gérer chaque aspect du comportement du PiDog de manière indépendante.