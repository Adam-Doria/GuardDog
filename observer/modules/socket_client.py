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