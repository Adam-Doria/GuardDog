# modules/observer_pattern.py

class Subject:
    """
    Sujet (Subject) dans le pattern Observer.
    Peut enregistrer, désenregistrer et notifier des observateurs.
    """
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)
            # print(f"Observer attaché: {observer.__class__.__name__}") # Uncomment for debug

    def detach(self, observer):
        try:
            self._observers.remove(observer)
            # print(f"Observer détaché: {observer.__class__.__name__}") # Uncomment for debug
        except ValueError:
            pass

    def notify_observers(self, *args, **kwargs):
        """Notifie tous les observateurs attachés."""
        for observer in self._observers:
            observer.update(*args, **kwargs)

class Observer:
    """
    Interface de l'Observateur (Observer) dans le pattern Observer.
    Toute classe qui veut "observer" un Subject doit implémenter cette méthode.
    """
    def update(self, *args, **kwargs):
        """
        Méthode appelée par le Subject pour notifier l'Observer d'un changement.
        Doit être implémentée par les sous-classes.
        """
        raise NotImplementedError("La méthode 'update' doit être implémentée par la sous-classe.")