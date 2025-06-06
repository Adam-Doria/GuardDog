# pidog_controller.py

import time
import threading

from modules.observer_pattern         import Observer
from modules.pidog_state              import PiDogState
from modules.pidog_hardware_interface import PiDogHardware
from modules.deepface_detector        import DeepFaceDetector
from modules.socket_client            import SocketIOClient
from config                            import SERVER_URL, ROBOT_ID, PATROL_DANGER_DISTANCE_CM, ALERT_BARK_DURATION_SEC

class PiDogController(Observer):
    """
    Contrôleur principal du PiDog.
    Orchestration des états (Patrol / Alert), de la détection, du client Socket.IO
    et du contrôle matériel via PiDogHardware.
    """

    def __init__(self):
        print("PiDogController: Initialisation du contrôleur...")
        # 1. Initialiser PiDogState (Subject). __init__ notifie tout de suite “PATROL”.
        self.pidog_state = PiDogState()

        # 2. Interface matérielle (stub si pas de PiDog/Vilib)
        self.pidog_hardware = PiDogHardware()

        # 3. Détecteur DeepFace
        self.deepface_detector = DeepFaceDetector(on_man_detected_callback=self._on_man_detected)

        # 4. Client Socket.IO
        self.socket_client = SocketIOClient(
            server_url=SERVER_URL,
            robot_id=ROBOT_ID,
            on_alert_lifted_callback=self._on_alert_lifted_from_app,
            on_connect_callback=self._on_socket_connect,
            on_disconnect_callback=self._on_socket_disconnect
        )

        # 5. Enregistrer les observers
        self.pidog_state.attach(self.deepface_detector)
        self.pidog_state.attach(self)

        # Variables pour la boucle de patrouille (stub)
        self._running = False
        self._patrol_thread = None
        self._patrol_stop_event = threading.Event()

    def _on_socket_connect(self):
        """Callback lorsque le client WS se connecte au serveur."""
        print("PiDogController: Socket.IO connecté. Prêt à démarrer la patrouille.")

    def _on_socket_disconnect(self):
        """Callback quand le client WS se déconnecte."""
        print("PiDogController: Socket.IO déconnecté. Arrêt du hardware.")
        self.pidog_hardware.stop_patrol()
        self.pidog_hardware.stop_barking()

    def _on_man_detected(self, gender, base64_img):
        """Callback lorsqu'un homme est détecté par DeepFaceDetector."""
        if self.pidog_state._current_mode == PiDogState.MODE_PATROL:
            print(f"PiDogController: Détection de '{gender}'. Passage en mode ALERT.")
            self.pidog_state.set_alert_mode()
            self._trigger_alert(gender, base64_img)

    def _on_alert_lifted_from_app(self):
        """Callback quand l'alerte est levée depuis l'application."""
        if self.pidog_state._current_mode == PiDogState.MODE_ALERT:
            print("PiDogController: Alerte levée par l'application. Retour en mode PATROL.")
            self.pidog_state.set_patrol_mode()

    def _trigger_alert(self, detected_gender, base64_img):
        """Actions spécifiques à effectuer lors du déclenchement d'une alerte."""
        print("PiDogController: Déclenchement de l'alerte (émission Socket.IO)...")
        payload = {
            "detected_gender": detected_gender,
            "timestamp": int(time.time() * 1000),
            "image": base64_img
        }
        self.socket_client.emit_intruder_detected(payload)

    def _patrol_loop(self):
        """Boucle de patrouille stub (pas de mouvement réel en local)."""
        while not self._patrol_stop_event.is_set():
            if self.pidog_state._current_mode == PiDogState.MODE_PATROL:
                distance = self.pidog_hardware.get_distance()
                print(f"[Patrol] Distance (stub) = {distance} cm")
                # Si obstacle, aboyer stub, sinon “patrouille” stub
                if 0 < distance < PATROL_DANGER_DISTANCE_CM:
                    self.pidog_hardware.start_barking()
                    time.sleep(ALERT_BARK_DURATION_SEC)
                    self.pidog_hardware.stop_barking()
                else:
                    self.pidog_hardware.start_patrol()
            time.sleep(1)

    def update(self, mode):
        """Réagit au changement de mode (PATROL / ALERT)."""
        print(f"PiDogController: Mise à jour reçue, mode = {mode}")
        if mode == PiDogState.MODE_PATROL:
            self._patrol_stop_event.clear()
            if not (self._patrol_thread and self._patrol_thread.is_alive()):
                self._patrol_thread = threading.Thread(target=self._patrol_loop, daemon=True)
                self._patrol_thread.start()
            self.pidog_hardware.stop_barking()
        elif mode == PiDogState.MODE_ALERT:
            self._patrol_stop_event.set()
            if self._patrol_thread and self._patrol_thread.is_alive():
                self._patrol_thread.join(timeout=1)
            self.pidog_hardware.stop_patrol()
            self.pidog_hardware.start_barking()

    def start(self):
        """Démarre la connexion WS ET lance le mode PATROL localement."""
        print("PiDogController: Démarrage du contrôleur.")
        self.socket_client.connect()
        # Forcer PATROL pour déclencher DeepFace dès que possible
        self.pidog_state.set_patrol_mode()

    def stop(self):
        """Arrêt complet."""
        print("PiDogController: Arrêt du contrôleur.")
        # Stopper loop
        self._patrol_stop_event.set()
        if self._patrol_thread and self._patrol_thread.is_alive():
            self._patrol_thread.join(timeout=2)
        # Détacher observers
        self.pidog_state.detach(self.deepface_detector)
        self.pidog_state.detach(self)
        # Stop Détection
        self.deepface_detector.stop_detection()
        # Déconnexion WS
        self.socket_client.disconnect()
        # Arrêt hardware
        self.pidog_hardware.close_all_hardware()
        print("PiDogController: Tous les modules arrêtés.")
