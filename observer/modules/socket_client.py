# modules/socket_client.py

import socketio

class SocketIOClient:
    """
    Client Socket.IO pour la communication avec l'application web.
    - Émet 'register' à la connexion.
    - Émet 'intruderDetected' quand on le demande.
    - Écoute 'disableAlert' pour reprendre la patrouille.
    """
    def __init__(self, server_url, robot_id, on_alert_lifted_callback, on_connect_callback, on_disconnect_callback):
        self.sio = socketio.Client()
        self.server_url = server_url
        self.robot_id = robot_id
        self._on_alert_lifted_callback = on_alert_lifted_callback
        self._on_connect_callback = on_connect_callback
        self._on_disconnect_callback = on_disconnect_callback
        self._register_events()

    def _register_events(self):
        @self.sio.event
        def connect():
            print("SocketIO: Connecté au serveur !")
            self.sio.emit('register', {'type': 'robot', 'id': self.robot_id})
            print(f"SocketIO: 'register' émis pour robot_id={self.robot_id}")
            self._on_connect_callback()

        @self.sio.event
        def disconnect():
            print("SocketIO: Déconnecté du serveur.")
            self._on_disconnect_callback()

        @self.sio.on('disableAlert')
        def on_disable_alert(data):
            print(f"SocketIO: Message 'disableAlert' reçu : {data}")
            self._on_alert_lifted_callback()

        @self.sio.event
        def message(data):
            print(f"SocketIO: Message générique reçu : {data}")

    def connect(self):
        """Tente de se connecter au serveur WS (polling ou websocket)."""
        try:
            print(f"SocketIO: Tentative de connexion à {self.server_url} …")
            self.sio.connect(self.server_url)
        except Exception as e:
            print(f"SocketIO ERROR : impossible de se connecter : {e}")

    def disconnect(self):
        """Ferme la connexion WS."""
        if self.sio.connected:
            self.sio.disconnect()
            print("SocketIO: Déconnexion effectuée.")

    def emit_intruder_detected(self, payload):
        """
        Émet l'événement 'intruderDetected' avec payload sur le serveur.
        On ajoute le robotId automatiquement.
        """
        if self.sio.connected:
            payload['robotId'] = self.robot_id
            print(f"SocketIO: Émission 'intruderDetected' avec : {payload}")
            self.sio.emit('intruderDetected', payload)
        else:
            print("SocketIO ERROR : Non connecté, impossible d’émettre 'intruderDetected'.")
