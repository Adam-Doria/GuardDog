# main.py
import time
from pidog_controller import PiDogController

def main():
    """
    Fonction principale qui initialise et gère le cycle de vie du PiDogController.
    """
    controller = None
    try:
        controller = PiDogController()
        controller.start()
        print("main.py: Le contrôleur PiDog est en cours d'exécution. Appuyez sur Ctrl+C pour quitter.")
        # Garde le thread principal en vie pour que les threads secondaires (SocketIO, DeepFace, Patrol) fonctionnent
        while controller._running:
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("\nmain.py: Arrêt demandé par l'utilisateur (Ctrl+C).")
    except Exception as e:
        print(f"\nmain.py ERROR: Une erreur inattendue est survenue: {e}")
    finally:
        if controller:
            controller.stop()
        print("main.py: Application PiDog terminée.")

if __name__ == "__main__":
    main()