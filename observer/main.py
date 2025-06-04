# main.py

import time

from pidog_controller import PiDogController

def main():
    controller = None
    try:
        controller = PiDogController()
        controller.start()
        print("main.py: PiDogController est en cours d'exécution. Ctrl+C pour quitter.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nmain.py: Arrêt demandé.")
    finally:
        if controller:
            controller.stop()
        print("main.py: Application terminée.")

if __name__ == "__main__":
    main()
