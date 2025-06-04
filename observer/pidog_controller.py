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