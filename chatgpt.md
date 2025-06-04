Voici une proposition de découpage en modules/fichiers pour rendre le code plus propre et plus maintenable. L’idée est d’avoir :

```
iot_pidog/
├── config.py
├── subject.py
├── controllers/
│   └── pidog_controller.py
├── observers/
│   ├── __init__.py
│   ├── patrol_observer.py
│   └── detection_observer.py
├── socket_client.py
└── main.py
```

Chaque fichier est autonome et se concentre sur une unique responsabilité.

---

## 1. `config.py`

On y place toutes les constantes globales (URL du serveur, fréquence d’analyse, etc.).

```python
# iot_pidog/config.py

# URL de votre serveur Socket.IO (à adapter selon votre installation)
SERVER_URL = "http://localhost:3000"

# Nombre d'images sautées entre chaque appel à DeepFace.analyze
FRAME_SKIP = 48
```

---

## 2. `subject.py`

Contient la classe `DogStateSubject`, implémentant le pattern « Observer » pour gérer l’état du chien (`"patrol"` ou `"alert"`).

```python
# iot_pidog/subject.py

class DogStateSubject:
    """
    Sujet (Subject) qui maintient l'état courant du chien (patrol ou alert)
    et notifie ses observateurs à chaque changement d'état.
    """
    def __init__(self):
        self._observers = []
        self._state = None  # Valeur possible : "patrol" ou "alert"

    def register_observer(self, observer):
        self._observers.append(observer)

    def unregister_observer(self, observer):
        self._observers.remove(observer)

    def set_state(self, new_state):
        if new_state == self._state:
            return
        print(f"[Subject] Changement d'état : {self._state} → {new_state}")
        self._state = new_state
        self._notify_observers()

    def get_state(self):
        return self._state

    def _notify_observers(self):
        for obs in self._observers:
            try:
                obs.update(self._state)
            except Exception as e:
                print(f"[Subject] Erreur lors de la notification à {obs} : {e}")
```

---

## 3. `controllers/pidog_controller.py`

Wrapper pour la librairie PiDog (SunFounder). Adaptez les méthodes `patrol_start`, `patrol_stop`, `bark` selon votre version de la librairie.

```python
# iot_pidog/controllers/pidog_controller.py

class PidogController:
    """
    Wrapper pour la (future) librairie PiDog de SunFounder.
    Remplacez les appels fictifs par ceux fournis par SunFounder.
    """
    def __init__(self):
        # Exemple : 
        # from pidog import Pidog
        # self.dog = Pidog()
        # Ici on laisse self.dog = None pour illustrer.
        self.dog = None

    def patrol_start(self):
        """
        Démarre la patrouille. Selon votre version de la librairie PiDog,
        cela peut être dog.patrol(), dog.auto_patrol(), etc.
        """
        if self.dog is not None:
            print("[PiDogController] Lancement de la patrouille.")
            try:
                self.dog.patrol()  # Remplacez par la méthode réelle
            except AttributeError:
                pass

    def patrol_stop(self):
        """
        Arrête la patrouille. Par exemple dog.stop() ou dog.idle().
        """
        if self.dog is not None:
            print("[PiDogController] Arrêt de la patrouille.")
            try:
                self.dog.stop()  # Remplacez par la méthode réelle
            except AttributeError:
                pass

    def bark(self):
        """
        Fait aboyer le robot. Par exemple dog.bark() ou dog.play_sound(...).
        """
        if self.dog is not None:
            print("[PiDogController] Bark !")
            try:
                self.dog.bark()  # Remplacez par la méthode réelle
            except AttributeError:
                pass
```

---

## 4. `observers/patrol_observer.py`

Gère exclusivement la patrouille. Quand l’état passe en `"patrol"`, on démarre un thread pour patrouiller ; quand l’état passe en `"alert"`, on arrête ce thread.

```python
# iot_pidog/observers/patrol_observer.py

import threading
import time

class PatrolObserver:
    """
    Observateur en charge de la patrouille.
    - Si état == "patrol", on démarre la boucle de patrouille (thread).
    - Si état == "alert", on stoppe la patrouille.
    """
    def __init__(self, dog_controller):
        """
        dog_controller : instance de PidogController
        """
        self.dog = dog_controller
        self._thread = None
        self._running = False

    def update(self, state):
        if state == "patrol" and not self._running:
            self._start_patrol()
        elif state == "alert" and self._running:
            self._stop_patrol()

    def _patrol_loop(self):
        """
        Boucle de patrouille. Selon la lib PiDog, la méthode patrol()
        peut être bloquante ou non. Ici, on suppose qu’on peut appeler
        self.dog.patrol() et que, pour l’arrêter, on appellera self.dog.stop().
        """
        print("[Patrol] Démarrage de la patrouille.")
        # Si patrol() est bloquant, on l'appelle une seule fois :
        try:
            self.dog.patrol()  
        except Exception:
            pass

        # Si, au contraire, vous devez faire plusieurs "steps", vous pouvez remplacer
        # le bloc ci-dessus par :
        # while self._running:
        #     self.dog.patrol_step()
        #     time.sleep(0.1)

        # Tant que _running reste True, on est en patrouille. 
        # Si la librairie gère elle-même l’interruption interne, on n’a rien à faire ici.
        while self._running:
            time.sleep(0.1)

        # À l'arrêt, on appelle patrol_stop pour être sûr que le robot s’immobilise.
        try:
            self.dog.stop()
        except Exception:
            pass
        print("[Patrol] Patrouille interrompue.")

    def _start_patrol(self):
        self._running = True
        self._thread = threading.Thread(target=self._patrol_loop, daemon=True)
        self._thread.start()

    def _stop_patrol(self):
        print("[Patrol] Arrêt en cours…")
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        print("[Patrol] Arrêté.")
```

---

## 5. `observers/detection_observer.py`

Gère la détection via DeepFace. Quand l’état passe en `"patrol"`, on démarre un thread qui scrute la caméra ; si on détecte un homme, on envoie l’alerte au serveur et on passe en `"alert"`.

```python
# iot_pidog/observers/detection_observer.py

import threading
import cv2
from deepface import DeepFace

from config import FRAME_SKIP

class DetectionObserver:
    """
    Observateur en charge de la détection (DeepFace).
    - Si état == "patrol", on démarre un thread de détection continue.
    - Si état == "alert", on stoppe ce thread.
    """
    def __init__(self, dog_subject, socketio_client, dog_controller):
        """
        dog_subject       : instance de DogStateSubject
        socketio_client   : socketio.Client déjà connecté
        dog_controller    : instance de PidogController (pour faire aboyer, etc.)
        """
        self.subject = dog_subject
        self.sio = socketio_client
        self.dog = dog_controller
        self._thread = None
        self._running = False
        self.frame_skip = FRAME_SKIP

    def update(self, state):
        if state == "patrol" and not self._running:
            self._start_detection()
        elif state == "alert" and self._running:
            self._stop_detection()

    def _start_detection(self):
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        print("[Detection] Boucle de détection démarrée.")

    def _stop_detection(self):
        print("[Detection] Arrêt en cours…")
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        print("[Detection] Détection arrêtée.")

    def _detection_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Detection] Impossible d'ouvrir la webcam.")
            return

        frame_count = 0
        last_faces = []

        while self._running:
            ret, frame = cap.read()
            if not ret:
                print("[Detection] Erreur lecture flux vidéo.")
                break

            frame = cv2.flip(frame, 1)
            frame_count += 1

            # Ne traiter qu'une frame sur FRAME_SKIP
            if frame_count % self.frame_skip == 0:
                try:
                    results = DeepFace.analyze(
                        img_path=frame,
                        actions=["gender"],
                        enforce_detection=False,
                        detector_backend="opencv"
                    )
                    if results:
                        # Si un seul visage, DeepFace renvoie un dict
                        faces = [results] if isinstance(results, dict) else results
                        last_faces = faces
                    else:
                        faces = []
                except ValueError:
                    # Aucun visage détecté ou confiance trop basse
                    faces = []
                except Exception as e:
                    print(f"[Detection] Erreur DeepFace inattendue : {e}")
                    faces = []

                # Parcourir les visages retenus
                for face_info in last_faces:
                    gender_scores = face_info.get("gender", {})
                    is_man = gender_scores.get("Man", 0) > gender_scores.get("Woman", 0)
                    if is_man:
                        # On détecte un homme → on passe en alert
                        print("[Detection] Homme détecté ! Passage en mode ALERT.")
                        # On fait aboyer le PiDog
                        try:
                            self.dog.bark()
                        except Exception:
                            pass
                        # On envoie l’événement "alert" au serveur
                        self.sio.emit("alert", {"message": "Homme détecté par le PiDog"})
                        # On change l'état global
                        self.subject.set_state("alert")
                        # On arrête la détection
                        self._running = False
                        break

            # (Optionnel) Pour debug, afficher la frame :
            # for face_info in last_faces:
            #     r = face_info.get("region", {})
            #     x, y, w, h = r.get("x", 0), r.get("y", 0), r.get("w", 0), r.get("h", 0)
            #     cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            #     gender_scores = face_info.get("gender", {})
            #     label = "Homme" if gender_scores.get("Man",0) > gender_scores.get("Woman",0) else "Femme"
            #     cv2.putText(frame, f"Genre: {label}", (x, y - 10),
            #                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            # cv2.imshow("Détection de genre", frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

        cap.release()
        # cv2.destroyAllWindows()
        print("[Detection] Fin de la boucle de détection.")
```

Dans ce fichier :

* On importe `FRAME_SKIP` depuis `config.py`.
* `socketio_client` est le client Socket.IO déjà connecté (on l’injecte depuis `main.py`).
* Dès qu’on détecte un homme, on émet l’événement `"alert"` et on fait `subject.set_state("alert")`.

---

## 6. `socket_client.py`

Contient la configuration du client Socket.IO, avec ses handlers. Quand on reçoit `"lift_alert"`, on fait passer l’état du chien en `"patrol"`.

```python
# iot_pidog/socket_client.py

import socketio

class SocketClient:
    """
    Wrapper autour de socketio.Client() pour gérer la connexion
    et les événements. On passe dog_subject pour pouvoir modifier son état.
    """
    def __init__(self, dog_subject, server_url):
        """
        dog_subject : instance de DogStateSubject
        server_url  : URL de connexion (ex. "http://localhost:3000")
        """
        self.sio = socketio.Client()
        self.dog_subject = dog_subject

        # Enregistrer les handlers AVANT de connecter
        self._register_handlers()
        try:
            print("[SocketClient] Connexion à", server_url)
            self.sio.connect(server_url)
        except Exception as e:
            print(f"[SocketClient] Échec de connexion : {e}")
            raise

    def _register_handlers(self):
        @self.sio.event
        def connect():
            print("[Socket.IO] Connecté au serveur.")

        @self.sio.event
        def disconnect():
            print("[Socket.IO] Déconnecté du serveur.")

        @self.sio.on("lift_alert")
        def on_lift_alert(data):
            """
            Quand le serveur envoie 'lift_alert', on repasse en mode 'patrol'.
            """
            print(f"[Socket.IO] Reçu lift_alert : {data}")
            self.dog_subject.set_state("patrol")

        # (Ajoutez d'autres événements si besoin, ex. 'ping', etc.)
```

---

## 7. `main.py`

Point d’entrée du programme : on instancie chaque composant, on relie tout, puis on démarre en mode `"patrol"`.

```python
# iot_pidog/main.py

import time

from config import SERVER_URL
from subject import DogStateSubject
from controllers.pidog_controller import PidogController
from observers.patrol_observer import PatrolObserver
from observers.detection_observer import DetectionObserver
from socket_client import SocketClient

if __name__ == "__main__":
    # 1) Initialisation du subject et du contrôleur PiDog
    dog_subject = DogStateSubject()
    dog_ctrl = PidogController()

    # 2) Création du client Socket.IO (on le connecte tout de suite)
    try:
        socket_client = SocketClient(dog_subject, SERVER_URL)
    except Exception:
        print("[Main] Impossible de démarrer Socket.IO. Abandon.")
        exit(1)

    # 3) Création des observers
    patrol_obs = PatrolObserver(dog_ctrl)
    detection_obs = DetectionObserver(dog_subject, socket_client.sio, dog_ctrl)

    # 4) Enregistrement auprès du subject
    dog_subject.register_observer(patrol_obs)
    dog_subject.register_observer(detection_obs)

    # 5) On démarre en mode "patrol"
    dog_subject.set_state("patrol")

    # 6) Boucle principale pour garder le script actif
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Main] Interruption clavier, on arrête tout…")
    finally:
        # Forcer l'arrêt des threads de patrol & detection
        dog_subject.set_state("alert")
        time.sleep(0.5)
        socket_client.sio.disconnect()
        print("[Main] Fermeture terminée.")
```

---

### Explications du découpage

1. **`config.py`**

   * Contient les constantes partagées partout : `SERVER_URL`, `FRAME_SKIP`, etc.

2. **`subject.py`**

   * Gère un état unique (`"patrol"` ou `"alert"`) et notifie tous les observateurs lorsqu’il change.
   * Cela isole complètement la logique de changement d’état du reste du code.

3. **`controllers/pidog_controller.py`**

   * Wrapper pour toutes les commandes hardware du PiDog (patrouille, arrêt, aboiement, etc.).
   * Si à l’avenir vous changez de version de la librairie PiDog, vous n’avez qu’à modifier cet unique fichier.

4. **`observers/patrol_observer.py`**

   * S’occupe seulement de la patrouille. Quand il reçoit `state == "patrol"`, il démarre un thread qui appelle `dog_controller.patrol()` ou `patrol_step()`.
   * Dès qu’il reçoit `state == "alert"`, il stoppe proprement la patrouille.

5. **`observers/detection_observer.py`**

   * S’occupe uniquement de la boucle DeepFace.
   * Il lit la webcam, analyse la frame toutes les `FRAME_SKIP` images, détecte la présence d’un homme (via `gender["Man"] > gender["Woman"]`), fait aboyer le chien (`dog_controller.bark()`), envoie l’alerte au serveur (`socketio.emit("alert", {...})`), puis change l’état du sujet en `"alert"`.
   * Dès qu’il reçoit `state == "alert"`, il interrompt la boucle DeepFace.

6. **`socket_client.py`**

   * Créé un `socketio.Client()` et définit les handlers de connexion/déconnexion.
   * Gère l’événement serveur `"lift_alert"`, qui fait passer l’état en `"patrol"`.
   * Comme c’est un wrapper, si vous voulez ajouter d’autres événements (ex. `"heartbeat"`, `"sync"`, etc.), il suffit de les déclarer ici.

7. **`main.py`**

   * Fait simplement les étapes suivantes :

     1. Instancier `DogStateSubject` et `PidogController`.
     2. Connecter `SocketClient` (il reçoit `dog_subject` pour pouvoir le notifier).
     3. Créer `PatrolObserver` et `DetectionObserver`, en leur passant les dépendances (`dog_ctrl` et `socket_client.sio`).
     4. Enregistrer ces observers dans `dog_subject`.
     5. Appeler `dog_subject.set_state("patrol")` pour lancer immédiatement la patrouille + détection.
     6. Entrer dans une boucle infinie pour maintenir l’application active, avec gestion de `Ctrl+C` pour bien tout arrêter.

---

## Comment adapter à votre contexte

1. **Installation des dépendances**

   ```bash
   pip install opencv-python deepface "python-socketio[client]"
   ```

   Et installez la librairie PiDog de SunFounder selon leurs instructions officielles.

2. **Vérifiez les noms de méthodes PiDog**

   * Remplacez `self.dog.patrol()`, `self.dog.stop()`, `self.dog.bark()` par les appels exacts de votre version de la librairie SunFounder.
   * Par exemple, si la méthode s’appelle `auto_patrol()` au lieu de `patrol()`, faites-en la mise à jour dans `PidogController.patrol_start()`.

3. **URL du serveur**

   * Changez `SERVER_URL = "http://localhost:3000"` dans `config.py` par l’adresse et le port de votre backend Socket.IO.

4. **Affichage vidéo (optionnel)**

   * Si votre PiDog n’a pas d’écran, commentez tout ce qui est `cv2.imshow(...)` et `cv2.waitKey(...)` pour la détection.
   * Si vous testez localement, décommentez-les dans `DetectionObserver` pour voir le flux en direct.

5. **Extensions futures**

   * Pour ajouter un nouvel observateur (par ex. log dans un fichier, ou envoi d’un SMS), créez un nouveau fichier `observers/mon_autre_observer.py`, héritez d’une interface commune ou implémentez `update(self, state)`, puis enregistrez-le dans `main.py` via `dog_subject.register_observer(...)`.

---

Avec cette architecture en modules, vous gagnez en :

* **Clarté** : chaque fichier a un rôle unique.
* **Testabilité** : vous pouvez tester isolément `DetectionObserver` sans lancer la partie `Patrol`.
* **Maintenance** : si un jour vous changez la version de PiDog, vous n’avez qu’un seul endroit à modifier (`controllers/pidog_controller.py`).
* **Extensibilité** : ajouter un nouvel observateur (logging, envoi de mails, etc.) ne casse rien aux autres composants.

Il ne vous reste plus qu’à copier/coller cette structure dans votre projet, adapter les méthodes fictives de PiDog et l’URL du serveur, et tout devrait être fonctionnel de façon propre et modulaire.
