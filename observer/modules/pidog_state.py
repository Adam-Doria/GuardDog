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