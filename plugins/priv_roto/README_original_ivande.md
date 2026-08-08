# roto_plugin

Deutsche Beschreibung: https://github.com/ivan73/roto_plugin/wiki/roto_plugin.Doku.de

(sorry für mein Englisch: die Englische Version der Beschreibung wurde größtenteils mit Google-Translate übersetzt..)

The plugin calculates the current position of the skylight (alternatively, the blinds / shutters) over the runtime.
The position is continuously updated in to the position Item. For this, the plugin will trigger itself (by scheduler)
About the (external) setting the position Item also positions can be approached.

referencing:
When you first start the plugin, the position is assumed to be 50%. (Item is set with value = 50 to initial value 50%)
If the skylight / the blind completely opened or closed, the position corrected roto_time_up or roto_time_down.

# Requirements 

Two items for the shutter push-button or buttons in the visualization for up_down and Stop_Step.
Two actuators channels on a Roto roof windows (up and down).

(Alternatively, a shutter actuator (which no position determination has))

# Configuration

## plugin.conf

Please provide a plugin.conf snippet for your plugin with ever option your plugin supports. Optional attributes should be commented out.

<pre>
[roto]
    class_name = Roto
    class_path = plugins.roto

</pre>

items.conf
--------------

*roto_plugin(mandatory) = active
    Identifies the item as an object of the Roto-plugin. The value of this attribute must necessarily be "active"
    roto_plugin = active

*type (mandatory):
   Data type of the object item. Must use "bool".
   type = bool

*eval_trigger (mandatory)
    The property items must be triggered when a key (or button) is pressed, or when a position to be approached.
    
*eval (mandatory)
    In each triggers the state of the object is to change items.
    eval = not sh.Dg.Flur.Dachfenster.Roto
    
*roto_up_down (mandatory)
    The button item that is to be monitored must be specified at the level of object items.
    With a 0-signal, the actuator moves up.
    With a 1-signal, the actuator moves down.

*roto_stop (mandatory)
    The button item that is to be monitored must be specified at the level of object items.
    If the item changed during the journey:
    With a 0 or 1 signal, the drive is stopped.
    
     otherwise:
     With a 0 signal, the actuator moves one step up. (Increment adjustable via roto_time_step)
     With a 1-signal, the actuator moves one step down. (Increment adjustable via roto_time_step)

*roto_position (0-100)(mandatory)
    The position item that is to be monitored or set must be specified at the level of object items.
    About this item, the calculated position is updated.
    If this item is set to a value, this position is approached.
    
### Roto skylight:
*roto_actor_open (mandatory)
    Actuator Item to open the roto skylight
*roto_actor_close (mandatory)
    Actuator Item to close the roto skylight
    
### alternative whit shutter actuators:
*roto_actor_up_down
    Actuator Item to open the shutter
*roto_actor_stop 
    Actuator Item to close the shutter
    
*roto_time_up (seconds)(optional, default 60 seconds)
    mx. Runtime when opening (necessary for the calculation of the position)
    
*roto_time_down (seconds)(optional, default 60 seconds)
    Max. Runtime when closing (necessary for the calculation of the position)
    
*roto_time_step (seconds)(optional, default 10 seconds)
    the step time
    
*roto_cycle_time (seconds)(optional, default 5 seconds)
    time interval the Position - item updated while running

# Example

<pre>
# items/example.conf
[Dg]    
    [[Flur]]
        [[[Dachfenster]]]
			[[[[Auf_ab]]]]  # Gruppenadresse des KNX- Taster oder Button in Visu
				type = bool
				visu = yes
				visu_acl = rw
                knx_dpt = 1
				knx_listen = 3/2/114
				enforce_updates = True
			[[[[Lamellenverstellung_stop]]]]    # Gruppenadresse des KNX- Taster oder Button in Visu
				type = bool
				visu = yes
				visu_acl = rw
                knx_dpt = 1
				knx_listen = 3/2/115
				enforce_updates = True
			[[[[Position]]]]    # errechnete Position; beim Setzen dieses Items wird diese Position angefahren 0-100
				type = num
                value = 50      # Initialer Wert 50%
                cache = True
				visu = yes
				visu_acl = rw
                enforce_updates = True
			[[[[Aktor_Zu]]]]  # Schaltaktor für ZuFahren - für Roto Dachfenster!!
				type = bool
				knx_dpt = 1
				knx_send = 4/2/114
               enforce_updates = True
			[[[[Aktor_Auf]]]]  # Schaltaktor für Auffahren - für Roto Dachfenster!!
				type = bool
				enforce_updates = True
				knx_dpt = 1
				knx_send = 4/2/115
            #[[[[Aktor_Auf_ab]]]] # Gruppenadresse des Jalousieaktors
			#	type = bool
			#	enforce_updates = True
			#	knx_dpt = 1
			#	knx_send = 4/2/114
			#[[[[Aktor_stop]]]] # Gruppenadresse des Jalousieaktors
			#	type = bool
			#	enforce_updates = True
			#	knx_dpt = 1
			#	knx_send = 4/2/115
			[[[[Roto]]]]    # Objekt Item / wird für das Plugin benötigt!!
				roto_plugin = active # Kennzeichen für das Plugin
				type = bool # muss bool sein
				eval_trigger = Dg.Flur.Dachfenster.Auf_ab | Dg.Flur.Dachfenster.Lamellenverstellung_stop | Dg.Flur.Dachfenster.Position # Triggern des Items wenn Taster gedrückt wird
				eval = not sh.Dg.Flur.Dachfenster.Roto # wird für das Plugin benötigt
				roto_up_down = Dg.Flur.Dachfenster.Auf_ab # Taster 0 ab ; 1 auf
				roto_stop = Dg.Flur.Dachfenster.Lamellenverstellung_stop # Stop oder 0 Schritt ab ; 1 Schritt auf
				roto_position = Dg.Flur.Dachfenster.Position # aktuelle Position oder Position anfahren 0-100
				#roto_actor_up_down = Dg.Flur.Dachfenster.Aktor_Auf_ab # Item GA des Jalousiekators
				#roto_actor_stop = Dg.Flur.Dachfenster.Aktor_stop # Item GA des Jalousiekators
                roto_actor_open = Dg.Flur.Dachfenster.Aktor_Auf  # Item Schaltaktor für Roto Dachfenster!!
				roto_actor_close = Dg.Flur.Dachfenster.Aktor_Zu # Item Schaltaktor für Roto Dachfenster!!
				roto_time_up = 60 # [Sekunden] max. Fahrzeit beim Auffahren
				roto_time_down = 58 # [Sekunden] max. Fahrzeit beim Ab(Zu)fahren
				roto_time_step = 6 # [Sekunden] Zeit beim Schrittweise fahren
                roto_cycle_time = 5 # [Sekunden] Aktualisierungsintervall des Positionsitems
</pre>

To use the plugin whith shutter actuators the Items "Aktor_Zu" and "Aktor_Auf" are disabled, and the two items "Aktor_Auf_ab" and "Aktor_stop" are activated. Disable "roto_actor_open" the items and "roto_actor_close" and enable the two items "roto_actor_up_down" and "roto_actor_stop" in the Objekt-Item "[[[[Roto]]]]" (the Item addresses has to be adjusted)

<pre>
# items/example.conf

			#[[[[Aktor_Zu]]]]  # Schaltaktor für ZuFahren - für Roto Dachfenster!!
			#	type = bool
			#	knx_dpt = 1
	 		#	knx_send = 4/2/114
			#	enforce_updates = True
			#[[[[Aktor_Auf]]]]  # Schaltaktor für Auffahren - für Roto Dachfenster!!
			#	type = bool
			#	enforce_updates = True
			#	knx_dpt = 1
			#	knx_send = 4/2/115
            [[[[Aktor_Auf_ab]]]] # Gruppenadresse des Jalousieaktors
				type = bool
				enforce_updates = True
				knx_dpt = 1
				knx_send = 4/2/114
			[[[[Aktor_stop]]]] # Gruppenadresse des Jalousieaktors
				type = bool
				enforce_updates = True
				knx_dpt = 1
				knx_send = 4/2/115
			[[[[Roto]]]]    # Objekt Item / wird für das Plugin benötigt!!
				roto_plugin = active # Kennzeichen für das Plugin
				type = bool # muss bool sein
				eval_trigger = Dg.Flur.Dachfenster.Auf_ab | Dg.Flur.Dachfenster.Lamellenverstellung_stop | Dg.Flur.Dachfenster.Position # Triggern des Items wenn Taster gedrückt wird
				eval = not sh.Dg.Flur.Dachfenster.Roto # wird für das Plugin benötigt
				roto_up_down = Dg.Flur.Dachfenster.Auf_ab # Taster 0 ab ; 1 auf
				#roto_stop = Dg.Flur.Dachfenster.Lamellenverstellung_stop # Stop oder 0 Schritt ab ; 1 Schritt auf
				#roto_position = Dg.Flur.Dachfenster.Position # aktuelle Position oder Position anfahren 0-100
				roto_actor_up_down = Dg.Flur.Dachfenster.Aktor_Auf_ab # Item GA des Jalousiekators
				roto_actor_stop = Dg.Flur.Dachfenster.Aktor_stop # Item GA des Jalousiekators
                roto_actor_open = Dg.Flur.Dachfenster.Aktor_Auf  # Item Schaltaktor für Roto Dachfenster!!
				roto_actor_close = Dg.Flur.Dachfenster.Aktor_Zu # Item Schaltaktor für Roto Dachfenster!!
				roto_time_up = 60 # [Sekunden] max. Fahrzeit beim Auffahren
				roto_time_down = 58 # [Sekunden] max. Fahrzeit beim Ab(Zu)fahren
				roto_time_step = 6 # [Sekunden] Zeit beim Schrittweise fahren
                roto_cycle_time = 5 # [Sekunden] Aktualisierungsintervall des Positionsitems
</pre>

