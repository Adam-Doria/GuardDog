Tu as tout à fait raison ! C'est une excellente remarque. Mettre tout dans un seul fichier est pratique pour un exemple simple, mais pour un projet réel, la modularité est clé pour la maintenabilité, la testabilité et la lisibilité.

Je m'excuse pour le manque de découplage initial. Reprenons et structurons le code en modules plus logiques.

Voici la nouvelle organisation en fichiers et le code pour chaque module.

---

## Nouvelle structure des fichiers

```
pidog_project/
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

### Explication de la nouvelle structure

1.  **`main.py`**: Le point d'entrée principal. Il sera très concis, se contentant d'initialiser et de démarrer le contrôleur.
2.  **`config.py`**: Pour toutes les constantes de configuration (URL du serveur Socket.IO, etc.).
3.  **`modules/`**: Un répertoire pour encapsuler toutes les logiques spécifiques et réutilisables.
    *   **`observer_pattern.py`**: Contient les classes génériques `Subject` et `Observer`.
    *   **`pidog_state.py`**: Gère l'état du PiDog (Patrouille/Alerte) et agit comme le `Subject`.
    *   **`pidog_hardware_interface.py`**: Abstraie les interactions avec le matériel du PiDog (simulées ici).
    *   **`deepface_detector.py`**: Encapsule la logique DeepFace et la gestion de la caméra, agissant comme un `Observer`.
    *   **`socket_client.py`**: Gère la connexion et la communication avec le serveur Socket.IO.
4.  **`pidog_controller.py`**: Le "cerveau" principal qui assemble tous les modules, gère les flux et les callbacks. C'est l'arbitre principal.

---

## Le Code Modularisé

### `config.py`

```python
# config.py
# Fichier de configuration pour le projet PiDog

# URL du serveur Socket.IO (à adapter si nécessaire)
SOCKET_IO_SERVER_URL = "http://localhost:3000"

# Paramètres DeepFace
# Désactive l'utilisation du GPU pour DeepFace, utile sur Raspberry Pi
DEEPFACE_CUDA_VISIBLE_DEVICES = "-1" 
# Nombre de frames à sauter avant chaque analyse DeepFace (pour économiser les ressources)
DEEPFACE_FRAME_SKIP = 48
```

---

### `modules/observer_pattern.py`

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
            # print(f"Observer attaché: {observer.__class__.__name__}")

    def detach(self, observer):
        try:
            self._observers.remove(observer)
            # print(f"Observer détaché: {observer.__class__.__name__}")
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
        else:
            print("PiDogState: Déjà en mode PATROUILLE.")

    def set_alert_mode(self):
        """Change le mode du PiDog en ALERTE."""
        if self._current_mode != self.MODE_ALERT:
            self._current_mode = self.MODE_ALERT
            print(f"PiDogState: Changement d'état: Mode ALERTE activé!")
            self.notify_observers(mode=self._current_mode)
        else:
            print("PiDogState: Déjà en mode ALERTE.")

```

---

### `modules/pidog_hardware_interface.py`

```python
# modules/pidog_hardware_interface.py

import time

class PiDogHardware:
    """
    Simule les interactions avec le matériel du PiDog.
    Dans un vrai projet, cette classe contiendrait les appels aux bibliothèques
    spécifiques du PiDog (SunFounder PiDog Control Library).
    """
    def __init__(self):
        print("PiDogHardware: Interface matérielle initialisée (simulation).")
        # Ici, vous pourriez initialiser l'instance du PiDog si c'est nécessaire une seule fois
        # ex: self.pidog = PiDog()

    def start_patrol_sequence(self):
        """Simule le démarrage de la patrouille du chien."""
        print("PiDogHardware: Démarrage de la patrouille...")
        # Exemple réel:
        # self.pidog.set_mode("patrol")
        # self.pidog.move_forward(speed=50) # Ou une séquence de mouvements plus complexe

    def stop_movement(self):
        """Simule l'arrêt des mouvements du chien."""
        print("PiDogHardware: Arrêt des mouvements.")
        # Exemple réel:
        # self.pidog.stop()

    def bark(self):
        """Simule l'aboiement du chien."""
        print("PiDogHardware: Aboiements! Wouf wouf!")
        # Exemple réel:
        # self.pidog.play_sound("bark.wav")
        # self.pidog.set_led_color('red')

    def stop_bark(self):
        """Simule l'arrêt des aboiements."""
        print("PiDogHardware: Arrêt des aboiements.")
        # Exemple réel:
        # self.pidog.stop_sound()
        # self.pidog.set_led_color('blue')

    def stop_all_actions(self):
        """Arrête toutes les actions physiques simulées du chien."""
        self.stop_movement()
        self.stop_bark()
        print("PiDogHardware: Toutes les actions matérielles arrêtées.")

```

---

### `modules/deepface_detector.py`

```python
# modules/deepface_detector.py

import cv2
from deepface import DeepFace
import os
import threading
import time
import queue

from modules.observer_pattern import Observer
from modules.pidog_state import PiDogState # Pour les constantes de mode
from config import DEEPFACE_CUDA_VISIBLE_DEVICES, DEEPFACE_FRAME_SKIP

# Désactive l'utilisation du GPU si configuré
os.environ["CUDA_VISIBLE_DEVICES"] = DEEPFACE_CUDA_VISIBLE_DEVICES

class DeepFaceDetector(Observer):
    """
    Gère la détection de genre via DeepFace dans un thread séparé.
    Observe le PiDogState pour savoir quand démarrer ou arrêter l'analyse.
    """
    def __init__(self, on_man_detected_callback):
        self._on_man_detected_callback = on_man_detected_callback
        self._cap = None
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
            self._release_camera()
            print("DeepFaceDetector: Thread de détection arrêté.")

    def _get_camera(self):
        """Tente d'ouvrir la caméra ou de la récupérer si elle est déjà ouverte."""
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                print("DeepFaceDetector ERROR: Impossible d'ouvrir la webcam (index 0).")
                print("Vérifiez si elle est branchée et non utilisée par une autre application.")
                self._cap = None
        return self._cap

    def _release_camera(self):
        """Relâche les ressources de la caméra."""
        if self._cap:
            self._cap.release()
            print("DeepFaceDetector: Caméra relâchée.")
            self._cap = None
        cv2.destroyAllWindows() # Just in case, if any DeepFace window was opened (not expected here)

    def _detection_loop(self):
        """Boucle principale du thread de détection DeepFace."""
        cap = self._get_camera()
        if not cap:
            self._running = False # Arrêter si la caméra ne s'ouvre pas
            return

        frame_count = 0

        while self._running and not self._stop_event.is_set():
            ret, frame = cap.read()

            if self._stop_event.is_set(): # Vérifier l'événement d'arrêt après la lecture
                break

            if not ret:
                print("DeepFaceDetector: Erreur de lecture de frame. Tentative de reconnexion...")
                self._release_camera()
                cap = self._get_camera()
                if not cap:
                    print("DeepFaceDetector: Impossible de récupérer la caméra. Arrêt de la détection.")
                    self._running = False
                    break
                time.sleep(1) # Attendre un peu avant de réessayer
                continue

            # Inverser l'image si nécessaire (souvent le cas avec les webcams)
            frame = cv2.flip(frame, 1)

            frame_count += 1
            
            # N'effectuer l'analyse que si le détecteur est actif et au bon rythme de frame skip
            if self._is_active_for_detection and (frame_count % DEEPFACE_FRAME_SKIP == 0):
                try:
                    # print("DeepFaceDetector: Analyse d'un frame...")
                    current_faces_data = DeepFace.analyze(
                        img_path=frame, 
                        actions=['gender'], 
                        enforce_detection=False, # Ne pas lancer d'erreur si aucun visage détecté
                        detector_backend='opencv' 
                    )
                    
                    if current_faces_data:
                        for face_info in current_faces_data:
                            # Assurez-vous que 'gender' et 'Man'/'Woman' existent
                            if 'gender' in face_info and isinstance(face_info['gender'], dict):
                                gender_prob = face_info['gender']
                                if gender_prob.get('Man', 0) > gender_prob.get('Woman', 0):
                                    gender = "Man"
                                    # Déclencher le callback si un homme est détecté
                                    print(f"DeepFaceDetector: Homme détecté! Probabilité: {gender_prob.get('Man', 0):.2f}")
                                    self._on_man_detected_callback(gender)
                                else:
                                    gender = "Woman"
                                    # print(f"DeepFaceDetector: Femme détectée. Probabilité: {gender_prob.get('Woman', 0):.2f}")
                            else:
                                print("DeepFaceDetector: Données de genre inattendues.")
                except ValueError as e:
                    # print(f"DeepFace: Aucun visage détecté ou confiance trop basse. {e}")
                    pass # C'est normal de ne pas toujours détecter de visage
                except Exception as e:
                    print(f"DeepFaceDetector: ERREUR INATTENDUE lors de l'analyse : {e}")
                    pass 
            
            # Petite pause pour ne pas saturer le CPU/GPU et laisser d'autres threads s'exécuter
            time.sleep(0.01) # ~100 FPS max pour la lecture, analyse moins fréquente
        
        print("DeepFaceDetector: Boucle de détection terminée.")
        self._release_camera()

```

---

### `modules/socket_client.py`

```python
# modules/socket_client.py

import socketio
import time

class SocketIOClient:
    """
    Client Socket.IO pour la communication avec l'application web.
    """
    def __init__(self, server_url, on_alert_lifted_callback, on_connect_callback, on_disconnect_callback):
        self.sio = socketio.Client()
        self.server_url = server_url
        self._on_alert_lifted_callback = on_alert_lifted_callback
        self._on_connect_callback = on_connect_callback
        self._on_disconnect_callback = on_disconnect_callback
        self._register_events()

    def _register_events(self):
        """Enregistre les gestionnaires d'événements Socket.IO."""
        @self.sio.event
        def connect():
            print("SocketIO: Connecté au serveur!")
            self._on_connect_callback()

        @self.sio.event
        def disconnect():
            print("SocketIO: Déconnecté du serveur.")
            self._on_disconnect_callback()

        @self.sio.on('alert_lifted')
        def on_alert_lifted(data):
            print(f"SocketIO: Message 'alert_lifted' reçu: {data}")
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

    def disconnect(self(self):
        """Déconnecte du serveur Socket.IO."""
        if self.sio.connected:
            self.sio.disconnect()
            print("SocketIO: Déconnexion initiée.")

    def emit(self, event, data):
        """Émet un événement vers le serveur Socket.IO."""
        if self.sio.connected:
            self.sio.emit(event, data)
            print(f"SocketIO: Événement '{event}' émis avec données: {data}")
        else:
            print(f"SocketIO ERROR: Non connecté, impossible d'émettre l'événement '{event}'.")

```

---

### `pidog_controller.py`

```python
# pidog_controller.py
import time

from modules.observer_pattern import Observer
from modules.pidog_state import PiDogState
from modules.pidog_hardware_interface import PiDogHardware
from modules.deepface_detector import DeepFaceDetector
from modules.socket_client import SocketIOClient
from config import SOCKET_IO_SERVER_URL

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
        self.pidog_hardware = PiDogHardware()
        
        # 2. Initialiser le détecteur DeepFace avec un callback vers ce contrôleur
        self.deepface_detector = DeepFaceDetector(
            on_man_detected_callback=self._on_man_detected
        )
        
        # 3. Initialiser le client Socket.IO avec des callbacks vers ce contrôleur
        self.socket_client = SocketIOClient(
            server_url=SOCKET_IO_SERVER_URL,
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

    def _on_socket_connect(self):
        """Callback appelé lorsque le client Socket.IO se connecte au serveur."""
        print("PiDogController: Socket.IO connecté. Prêt à démarrer la patrouille.")
        # Une fois connecté, le chien peut passer en mode patrouille initial
        self.pidog_state.set_patrol_mode() 

    def _on_socket_disconnect(self):
        """Callback appelé lorsque le client Socket.IO se déconnecte du serveur."""
        print("PiDogController: Socket.IO déconnecté.")
        # En cas de déconnexion, arrêtez toutes les actions du chien
        self.pidog_hardware.stop_all_actions()

    def _on_man_detected(self, gender):
        """Callback appelé par DeepFaceDetector lorsqu'un homme est détecté."""
        if self.pidog_state.current_mode == PiDogState.MODE_PATROL:
            print(f"PiDogController: Détection de '{gender}' en mode patrouille. Passage en mode ALERTE.")
            self.pidog_state.set_alert_mode() # Le changement d'état notifiera les observateurs
            self._trigger_alert(gender)

    def _on_alert_lifted_from_app(self):
        """Callback appelé par SocketIOClient lorsque l'alerte est levée par l'application."""
        if self.pidog_state.current_mode == PiDogState.MODE_ALERT:
            print("PiDogController: Alerte levée par l'application. Retour en mode PATROUILLE.")
            self.pidog_state.set_patrol_mode() # Le changement d'état notifiera les observateurs

    def _trigger_alert(self, detected_gender):
        """Actions spécifiques à effectuer lors du déclenchement d'une alerte."""
        print("PiDogController: Déclenchement de l'alerte (émission Socket.IO)...")
        # Envoi de l'alerte au serveur Socket.IO
        self.socket_client.emit('alert_triggered', {'detected_gender': detected_gender, 'timestamp': time.time()})

    def update(self, mode):
        """
        Implémentation de la méthode update de l'Observer.
        Le PiDogController réagit aux changements d'état de PiDogState
        pour déclencher les actions matérielles du chien.
        """
        print(f"PiDogController: Mise à jour basée sur le mode: {mode}")
        if mode == PiDogState.MODE_PATROL:
            self.pidog_hardware.stop_bark()
            self.pidog_hardware.start_patrol_sequence()
        elif mode == PiDogState.MODE_ALERT:
            self.pidog_hardware.stop_movement()
            self.pidog_hardware.bark()
        
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
        
        # Détacher les observateurs pour un arrêt propre
        self.pidog_state.detach(self.deepface_detector)
        self.pidog_state.detach(self) 

        # Arrêter les modules
        self.deepface_detector.stop_detection()
        self.socket_client.disconnect()
        self.pidog_hardware.stop_all_actions()
        print("PiDogController: Tous les modules arrêtés.")

```

---

### `main.py`

```python
# main.py
import time
from pidog_controller import PiDogController

def main():
    """
    Fonction principale qui initialise et gère le cycle de vie du PiDogController.
    """
    controller = PiDogController()
    try:
        controller.start()
        print("main.py: Le contrôleur PiDog est en cours d'exécution. Appuyez sur Ctrl+C pour quitter.")
        # Garde le thread principal en vie pour que les threads secondaires (SocketIO, DeepFace) fonctionnent
        while controller._running: # Utiliser le flag _running du contrôleur
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("\nmain.py: Arrêt demandé par l'utilisateur (Ctrl+C).")
    finally:
        controller.stop()
        print("main.py: Application PiDog terminée.")

if __name__ == "__main__":
    main()
```

---

### Comment lancer le projet :

1.  **Créez la structure de dossiers** comme décrit ci-dessus (`pidog_project/`, `modules/`).
2.  **Copiez chaque bloc de code** dans le fichier correspondant.
3.  **Installez les dépendances** si ce n'est pas déjà fait :
    ```bash
    pip install python-socketio opencv-python deepface
    ```
4.  **Assurez-vous que votre serveur Node.js/Socket.IO** est en cours d'exécution (utilisez l'exemple de `server.js` fourni précédemment).
5.  **Naviguez dans le dossier `pidog_project/`** (le dossier parent de `main.py` et `modules/`).
6.  **Exécutez le script principal :**
    ```bash
    python main.py
    ```

Cette architecture est beaucoup plus propre :
*   Chaque fichier a une **responsabilité unique** (Single Responsibility Principle).
*   Les **dépendances sont claires** (via les imports).
*   Le `main.py` est un **simple orchestrateur**, déléguant le travail au `PiDogController`.
*   Les modules sont **plus faciles à tester** indépendamment.
*   Le **pattern Observer** est maintenu, garantissant un découplage entre les changements d'état et les actions qui en découlent.

C'est une base bien plus robuste pour faire évoluer votre projet !