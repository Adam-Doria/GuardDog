# modules/pidog_hardware_interface.py

import time

# ----------------------------------------------------------------
# On teste si la bibliothèque PiDog (SunFounder) et Vilib sont disponibles.
# Si non, on crée une classe StubPiDogHardware qui fait simplement des prints/no-ops.
# ----------------------------------------------------------------
_try_import = True
try:
    from pidog import Pidog       # True PiDog hardware
    from vilib import Vilib        # True Vilib camera
except Exception as e:
    _try_import = False

# ----------------------------------------------------------------
# Si import a échoué → on définit une classe stub
# ----------------------------------------------------------------
if not _try_import:
    class PiDogHardware:
        """
        Version de substitution (stub) pour s'exécuter sur un PC sans PiDog ni Vilib.
        Toutes les méthodes font simplement un print et ne fassent rien.
        """
        def __init__(self):
            print("PiDogHardware (STUB) : pas de PiDog/Vilib présent, je ne fais que logger.")
            self.my_dog = None

        def _wait_dog_actions_done(self):
            # Rien à attendre dans le stub
            pass

        def start_patrol(self):
            print("PiDogHardware (STUB) : start_patrol() appelé → aucun hardware.")

        def stop_patrol(self):
            print("PiDogHardware (STUB) : stop_patrol() appelé → aucun hardware.")

        def start_barking(self):
            print("PiDogHardware (STUB) : start_barking() appelé → aucun hardware.")

        def stop_barking(self):
            print("PiDogHardware (STUB) : stop_barking() appelé → aucun hardware.")

        def get_distance(self):
            # Retour par défaut : aucune donnée (on simule “pas d’obstacle”)
            return -1

        def get_vilib_image(self):
            # Retourne None, pas de caméra
            return None

        def close_all_hardware(self):
            print("PiDogHardware (STUB) : close_all_hardware() appelé → aucun hardware.")

# ----------------------------------------------------------------
# Si import a réussi → on définit la classe réelle
# ----------------------------------------------------------------
else:
    class PiDogHardware:
        """
        Interface matérielle réelle pour PiDog SunFounder + Vilib.
        Encapsule les appels à la bibliothèque Pidog et Vilib.
        """
        def __init__(self):
            print("PiDogHardware: Initialisation du matériel PiDog + Vilib…")
            try:
                self.my_dog = Pidog()
                print("PiDogHardware: Pidog initialisé.")
                Vilib.camera_start(vflip=False, hflip=False)
                Vilib.display(local=False, web=True)
                # Attendre que Vilib soit prêt
                while not Vilib.flask_start:
                    time.sleep(0.01)
                print("PiDogHardware: Caméra Vilib démarrée.")
            except Exception as e:
                print(f"PiDogHardware ERROR: Impossible d'initialiser Pidog/Vilib → {e}")
                self.my_dog = None

        def _wait_dog_actions_done(self):
            if self.my_dog:
                self.my_dog.wait_all_done()
                time.sleep(0.1)

        def start_patrol(self):
            if not self.my_dog:
                print("PiDogHardware: (start_patrol) Pas de Pidog, no-op.")
                return
            print("PiDogHardware: Démarrage de la patrouille matérielle.")
            # Allumer un mode LED blanc “patrouille”
            try:
                self.my_dog.rgb_strip.set_mode('breath', 'white', bps=0.5)
            except Exception:
                pass
            # Exécuter quelques actions “stand” puis “forward” (exemple)
            try:
                self.my_dog.do_action('stand', speed=80)
                self._wait_dog_actions_done()
                self.my_dog.do_action('forward', step_count=2, speed=98)
                self._wait_dog_actions_done()
                # Simuler un virage aléatoire
                self.my_dog.do_action('turn_left', step_count=1, speed=98)
                self._wait_dog_actions_done()
            except Exception:
                pass

        def stop_patrol(self):
            if not self.my_dog:
                print("PiDogHardware: (stop_patrol) Pas de Pidog, no-op.")
                return
            print("PiDogHardware: Arrêt de la patrouille matérielle.")
            try:
                self.my_dog.body_stop()
                self.my_dog.rgb_strip.close()
                self._wait_dog_actions_done()
            except Exception:
                pass

        def start_barking(self):
            if not self.my_dog:
                print("PiDogHardware: (start_barking) Pas de Pidog, no-op.")
                return
            print("PiDogHardware: Début aboiement (alerte) !")
            try:
                self.my_dog.rgb_strip.set_mode('bark', 'red', bps=2)
                self.my_dog.speak('angry', volume=100)
                self.my_dog.do_action('sit', speed=70)
                self._wait_dog_actions_done()
            except Exception:
                pass

        def stop_barking(self):
            if not self.my_dog:
                print("PiDogHardware: (stop_barking) Pas de Pidog, no-op.")
                return
            print("PiDogHardware: Arrêt des aboiements.")
            try:
                self.my_dog.rgb_strip.set_mode('breath', 'white', bps=0.5)
            except Exception:
                pass

        def get_distance(self):
            if not self.my_dog:
                return -1
            try:
                return self.my_dog.read_distance()
            except Exception:
                return -1

        def get_vilib_image(self):
            if not self.my_dog:
                return None
            # On suppose que Vilib.flask_start est True (vu dans init)
            try:
                return Vilib.img
            except Exception:
                return None

        def close_all_hardware(self):
            if not self.my_dog:
                print("PiDogHardware: (close_all_hardware) Pas de Pidog, no-op.")
                return
            print("PiDogHardware: Arrêt complet du matériel PiDog et Vilib.")
            try:
                self.my_dog.close()
            except Exception:
                pass
            try:
                Vilib.camera_close()
            except Exception:
                pass
            print("PiDogHardware: Matériel arrêté.")
