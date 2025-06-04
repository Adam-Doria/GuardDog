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