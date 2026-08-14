.. index:: Plugins; priv_roto
.. index:: priv_roto

========
priv_roto
========

Positions- und Winkelsteuerung für Rollläden/Jalousien, die über einen Aktor ohne
Positions-Rückmeldung angesteuert werden (eine Gruppenadresse, nur Fahr-/Schritt-Telegramme -
z.B. Roto-Dachfenster-Antriebe). Die Position wird über die Fahrzeit, der Lamellenwinkel über
die Anzahl gesendeter Schritt-Telegramme berechnet und laufend in den Items nachgeführt.

Beim Start des Plugins wird die zuletzt gespeicherte Position/Winkel übernommen (Items sind
``cache: True``). Fährt die Jalousie komplett auf oder zu, wird die berechnete Position/Winkel
implizit auf den jeweiligen Endanschlag korrigiert.

Voraussetzungen
================

Ein Jalousie-Aktor mit einer Gruppenadresse für Fahr-/Schritt-Befehle, ohne eigene
Positionsauswertung.

Konfiguration
=============

plugin.yaml
-----------

.. code-block:: yaml

    roto:
        plugin_name: priv_roto

items.yaml
----------

Das Plugin stellt die Struktur ``priv_roto.shutter`` bereit, die die Items ``pos``,
``pos.soll``, ``winkel``, ``winkel.soll`` und das Konfigurations-Item ``Roto`` anlegt.
Das Item ``move`` (Fahrbefehle Richtung Aktor / vom Aktor empfangene Tasterbefehle) wird
selbst definiert und muss als Geschwister-Item von ``Roto`` liegen - das Plugin findet
``pos``/``winkel``/``move`` relativ zum Elternitem des ``Roto``-Konfigurations-Items.

Konfigurationsattribute (auf dem ``Roto``-Item):

- ``roto_plugin`` (mandatory) = ``active``
  Aktiviert das Plugin für diese Jalousie.
- ``roto_time_up`` (Sekunden, Default 60)
  Fahrzeit komplett auf.
- ``roto_time_down`` (Sekunden, Default 60)
  Fahrzeit komplett zu.
- ``roto_angle_step`` (Grad, Default 10)
  Winkeländerung pro Schritt-Telegramm.
- ``roto_angle_hyst`` (Schritte, Default 0)
  Hysterese beim ersten Aufwärts-Schrittbetrieb nach einer Zu-Fahrt.
- ``roto_cycle_time`` (Sekunden, Default 5)
  Zykluszeit der Positions-Nachführung während einer Fahrt.

Beispiel
--------

.. code-block:: yaml

    # items/example.yaml
    eg:
        wohnzimmer:
            jalousie:
                rechts:
                    move:
                        # 4 = hoch, 7 = Schritt hoch/Stopp, 8 = runter, 11 = Schritt runter
                        type: num
                        visu_acl: rw
                        knx_dpt: 5999
                        knx_listen: 2/0/2
                        knx_send: 2/0/2
                        enforce_updates: True

                    struct: priv_roto.shutter
                    Roto:
                        roto_time_up: 78
                        roto_time_down: 75
                        roto_angle_step: 18
                        roto_angle_hyst: 0
                        roto_cycle_time: 1
