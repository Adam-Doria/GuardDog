# modules/pidog_state.py

class PiDogState:
    MODE_PATROL = "patrol"
    MODE_ALERT  = "alert"

    def __init__(self):
        self._observers = []
        self._current_mode = self.MODE_PATROL
        print(f"PiDogState: Démarré en mode: {self._current_mode.upper()}")
        self._notify()  # <<<— notifie DIRECTEMENT "patrol" aux observers

    def attach(self, obs):
        self._observers.append(obs)

    def detach(self, obs):
        self._observers.remove(obs)

    def set_patrol_mode(self):
        self._current_mode = self.MODE_PATROL
        self._notify()

    def set_alert_mode(self):
        self._current_mode = self.MODE_ALERT
        self._notify()

    def _notify(self):
        for obs in self._observers:
            try:
                obs.update(self._current_mode)
            except Exception as e:
                print(f"PiDogState: Erreur update sur {obs} : {e}")
