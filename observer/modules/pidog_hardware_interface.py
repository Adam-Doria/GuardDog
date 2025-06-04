# modules/pidog_hardware_interface.py

import time
import os
from pidog import Pidog 
from vilib import Vilib 

from pidog.preset_actions import bark, shake_head, wag_tail 

from config import PATROL_DANGER_DISTANCE_CM, ALERT_BARK_DURATION_SEC

class PiDogHardware:
    """
    Interface réelle pour contrôler le PiDog SunFounder.
    Encapsule les appels à la bibliothèque Pidog, en utilisant les fonctions
    de pidog.preset_actions pour des actions complexes et natives.
    """
    def __init__(self):
        print("PiDogHardware: Initialisation de l'interface matérielle réelle...")
        try:
            self.my_dog = Pidog() # Instancie le chien Pidog
            print("PiDogHardware: Pidog initialisé.")
            Vilib.camera_start(vflip=False, hflip=False)
            Vilib.display(local=False, web=True) # Affichage web de la caméra si nécessaire
            while not Vilib.flask_start:
                time.sleep(0.01)
            print("PiDogHardware: Caméra Vilib démarrée.")
        except Exception as e:
            print(f"PiDogHardware ERROR: Impossible d'initialiser Pidog ou Vilib: {e}")
            self.my_dog = None 
            raise RuntimeError(f"Échec de l'initialisation du matériel PiDog: {e}")

    def _wait_dog_actions_done(self):
        """Attends que toutes les actions du chien soient terminées."""
        if self.my_dog:
            self.my_dog.wait_all_done()
            time.sleep(0.1) 

    def set_patrol_lighting(self):
        """Active le mode d'éclairage de patrouille (blanc, respiration)."""
        if not self.my_dog: return
        self.my_dog.rgb_strip.set_mode('breath', 'white', bps=0.5)

    def set_alert_lighting(self):
        """Active le mode d'éclairage d'alerte (rouge, aboiement)."""
        if not self.my_dog: return
        self.my_dog.rgb_strip.set_mode('bark', 'red', bps=2)

    def perform_patrol_movement(self):
        """
        Exécute un pas de mouvement de patrouille, incluant des actions comme
        avancer, secouer la tête et remuer la queue (inspiré de examples/3_patrol.py).
        """
        if not self.my_dog: return
        print("PiDogHardware: Exécution d'un pas de patrouille standard.")
        self.my_dog.do_action('forward', step_count=2, speed=98)
        shake_head(self.my_dog) 
        wag_tail(self.my_dog) 
        self._wait_dog_actions_done() 

    def perform_turn_movement(self):
        """Exécute un mouvement de virage (pour éviter un obstacle), inspiré de examples/3_patrol.py."""
        if not self.my_dog: return
        print("PiDogHardware: Exécution d'un virage (évitement d'obstacle).")
        self.my_dog.do_action('turn_right', step_count=1, speed=98)
        self._wait_dog_actions_done()

    def start_patrol(self):
        """Met le chien en position de patrouille initiale et active les lumières."""
        if not self.my_dog: return
        print("PiDogHardware: Préparation pour la patrouille.")
        self.set_patrol_lighting()
        self.my_dog.do_action('stand', speed=80) 
        self._wait_dog_actions_done()

    def stop_patrol(self):
        """Arrête les mouvements de patrouille du chien et éteint les lumières."""
        if not self.my_dog: return
        print("PiDogHardware: Arrêt complet de la patrouille.")
        self.my_dog.body_stop() 
        self.my_dog.rgb_strip.close() 
        self._wait_dog_actions_done()

    def start_barking(self):
        """Fait aboyer le chien avec la posture et le son d'alerte."""
        if not self.my_dog: return
        print("PiDogHardware: Début des aboiements (alerte)!")
        self.set_alert_lighting()
        
  
        head_yaw = self.my_dog.head_current_angles[0] if hasattr(self.my_dog, 'head_current_angles') else 0
        bark(self.my_dog, yrp=[head_yaw, 0, 0], volume=100) # Utilise la fonction `bark` de `pidog.preset_actions`
        self._wait_dog_actions_done()
        
       
        self.my_dog.do_action('sit', speed=70) 
        self._wait_dog_actions_done()

    def stop_barking(self):
        """Arrête les aboiements du chien (si en cours) et revient à l'éclairage de patrouille."""
        if not self.my_dog: return
        print("PiDogHardware: Arrêt des aboiements.")

        self.set_patrol_lighting()
        self._wait_dog_actions_done()

    def get_distance(self):
        """Lit la distance du capteur ultrasonique (utilisé dans examples/3_patrol.py)."""
        if not self.my_dog: return -1
        try:
            return self.my_dog.read_distance()
        except Exception as e:
            print(f"PiDogHardware ERROR: Erreur de lecture de distance: {e}")
            return -1

    def get_vilib_image(self):
        """Retourne le dernier frame de la caméra Vilib."""
   
        if not Vilib.flask_start: 
            return None
        try:
            return Vilib.img
        except Exception as e:
            print(f"PiDogHardware ERROR: Erreur de récupération d'image Vilib: {e}")
            return None

    def close_all_hardware(self):
        """Arrête toutes les actions du chien et ferme la caméra Vilib."""
        if not self.my_dog:
            print("PiDogHardware: (close_all_hardware) Pas de Pidog à fermer.")
            return
        print("PiDogHardware: Arrêt complet du matériel PiDog et Vilib.")
        try:
            self.my_dog.close() 
        except Exception as e:
            print(f"PiDogHardware ERROR: Erreur lors de la fermeture de Pidog: {e}")
        try:
            Vilib.camera_close()
        except Exception as e:
            print(f"PiDogHardware ERROR: Erreur lors de la fermeture de la caméra Vilib: {e}")
        print("PiDogHardware: Matériel arrêté.")