# roto_plugin for Tebis TS shutters

The plugin calculates the current position of a shutter over the running time and the blade angle over the step increments.
The position is continuously updated in the position item using a scheduler with adjustable cycle time. 

Referencing:
When you first start the plugin, the position is taken from item cache. 
If the shutter is completely opened or closed, the position will be corrected to roto_time_up or roto_time_down.

# Requirements 

A shutter actuator with only one group address and no return channel. The plugin uses control values from a Tebis TS system (see wiki section for some hints)

# Configuration

## plugin.yaml

Add the plugin to etc/plugin.yaml. Currently, no more options are available for the plugin.

<pre>
roto:
    plugin_name: priv_roto

</pre>

items.yaml
--------------

The plugin provides a predefined struct which provides the following items:

- item.pos
    actual position of the shutter
    
- item.pos.soll
    set position for the shutter

- item.winkel
    actual angle of the shutter blades

- item.winkel.soll
    set angle for the shutter blade

Individual parameters for each shutter ehich are needed for position and angle calculation:

- roto_plugin(mandatory) = active
    Identifies the item as an object of the Roto-plugin. The value of this attribute must necessarily be "active"
    roto_plugin = active
    
- roto_time_up (seconds) (mandatory)
    mx. Runtime when opening (necessary for the calculation of the position)
    
- roto_time_down (seconds)(mandatory)
    Max. Runtime when closing (necessary for the calculation of the position)
    
- roto_angle_step (degrees) (mandatory)
    the angle movement per step 

- roto_angle_hyst (steps) (mandatory)
    the hysteresis of the angle when stepping upward

- roto_cycle_time (seconds)(mandatory)
    time interval the Position - item updated while running

# Example

<pre>
# items/example.yaml
eg:
    wohnzimmer:
        jalousie:
            rechts:
                move:
                    # 4 = up, 7 = step up / Stop, 8 = down, 11 = step down
                    type: num
                    visu_acl: rw
                    knx_dpt: 5999
                    knx_listen: 2/0/2
                    knx_send: 2/0/2
                    enforce_updates: True

                struct: priv_roto.shutter
                Roto:
                    # refer to plugin struct. We need only the individual parameters here.
                    roto_plugin: active
                    roto_time_up: 78
                    roto_time_down: 75
                    roto_angle_step: 18
                    roto_angle_hyst: 0
                    roto_cycle_time: 1
</pre>
