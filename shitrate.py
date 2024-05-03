import platform

import ctypes as ct
import ctypes.util

from types import SimpleNamespace

import obspython as obs  # studio


###########################################################################

if platform.system() == "Linux":
    libobs = ct.CDLL(ct.util.find_library("obs"))
else:
    libobs = ct.CDLL("obs")


def wrap(lib, funcname, restype, argtypes):
    """Wraps a C function from the given lib into python
    """
    func = getattr(lib, funcname)
    func.restype = restype
    func.argtypes = argtypes
    return func



############################################################################

class ctSource(ct.Structure):
    pass


class ctVolmeter(ct.Structure):
    pass


volmeter_callback_t = ct.CFUNCTYPE(None, ct.c_void_p, ct.POINTER(ct.c_float),
                                   ct.POINTER(ct.c_float), ct.POINTER(ct.c_float))




obs.obs_volmeter_create             = wrap(libobs,
                                           "obs_volmeter_create",
                                           restype=ct.POINTER(ctVolmeter),
                                           argtypes=[ct.c_int])

obs.obs_volmeter_destroy            = wrap(libobs,
                                           "obs_volmeter_destroy",
                                           restype=None,
                                           argtypes=[ct.POINTER(ctVolmeter)])

obs.obs_volmeter_add_callback       = wrap(libobs,
                                           "obs_volmeter_add_callback",
                                           restype=None,
                                           argtypes=[ct.POINTER(ctVolmeter), volmeter_callback_t, ct.c_void_p])

obs.obs_volmeter_remove_callback    = wrap(libobs,
                                           "obs_volmeter_remove_callback",
                                           restype=None,
                                           argtypes=[ct.POINTER(ctVolmeter), volmeter_callback_t, ct.c_void_p])



_obs_volmeter_attach_source         = wrap(libobs,
                                           "obs_volmeter_attach_source",
                                           restype=ct.c_bool,
                                           argtypes=[ct.POINTER(ctVolmeter), ct.POINTER(ctSource)])

obs.obs_volmeter_attach_source      = lambda volmeter, source : _obs_volmeter_attach_source(volmeter,
                                                                                            ct.cast(int(source), ct.POINTER(ctSource)))

obs.obs_volmeter_detach_source         = wrap(libobs,
                                           "obs_volmeter_detach_source",
                                           restype=None,
                                           argtypes=[ct.POINTER(ctVolmeter)])

obs.OBS_FADER_LOG = 2

##########################################################################################



class Source:
    def __init__(self, name):
        self.name       = name
        self.volmeter   = obs.obs_volmeter_create(obs.OBS_FADER_LOG)
        obs.obs_volmeter_add_callback(self.volmeter, volmeter_callback, None)

        G.sources.append(self)
    
    def attach_source(self):
        obsSource = obs.obs_get_source_by_name(self.name)

        obs.obs_volmeter_detach_source(self.volmeter)
        if not obs.obs_volmeter_attach_source(self.volmeter, obsSource):
            raise
        
        obs.obs_source_release(obsSource)



#called by obs after processing volume data
@volmeter_callback_t
def volmeter_callback(data, mag, peak, input):
    try: # PENWY : try ... except so that if there is an error happening, it doesn't spam that error in log every volume tick but raises it and stops instead
        if G.outputActive:
            G.noises.append(float(peak[0]))
    except:
        for source in G.sources:
            obs.obs_volmeter_destroy(source.volmeter)
        raise




def update_bitrate():
    try:
        # getting loudest noise from all sources
        loudestNoise = max(G.noises)
        G.noises = [-999]

        # this is a fucked up piecewise function
        # checkitout: desmos.com/calculator/umastzlhoj
        bitrate = (G.maxBitrate / pow( G.maxVolume, G.dampening )) * pow(abs( loudestNoise ), G.dampening)
        d = (G.maxVolume - 40)
        if abs( loudestNoise ) < d:
            bitrate -= pow(abs( loudestNoise + d ), 4 * (1.1 - G.dampening))

        # keeping bitrate within bounds
        bitrate = min(G.maxBitrate, max( round(bitrate, 0), G.minBitrate ))

        # print("\nvolume:" + str(loudestNoise))
        # print("bitrate:" + str(bitrate))

        if G.outputType & 1:                                    # PENWY : if recording is active
            output   = obs.obs_frontend_get_recording_output()
            encoder  = obs.obs_output_get_video_encoder(output)
            settings = obs.obs_data_create()

            obs.obs_data_set_int(settings, "bitrate", int(bitrate))
            obs.obs_encoder_update(encoder, settings)

            obs.obs_data_release(settings)
            obs.obs_output_release(output)

        if G.outputType & 2:                                    # PENWY : if streaming is active
            output   = obs.obs_frontend_get_streaming_output()
            encoder  = obs.obs_output_get_video_encoder(output)
            settings = obs.obs_data_create()

            obs.obs_data_set_int(settings, "bitrate", int(bitrate))
            obs.obs_encoder_update(encoder, settings)

            obs.obs_data_release(settings)
            obs.obs_output_release(output)

    except:
        obs.remove_current_callback()
        raise



def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        G.outputType |= 1

    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STARTED:
        G.outputType |= 2

    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPING:
        G.outputType &= ~1

    if event == obs.OBS_FRONTEND_EVENT_STREAMING_STOPPING:
        G.outputType &= ~2

    if not G.outputActive and G.outputType:
        # print("\nRecording start\n")

        for source in G.sources:
            source.attach_source()

        obs.timer_add(G.callback, G.bitrate_tick)
        G.outputActive = True

    if G.outputActive and not G.outputType:
        # print("\nRecording end\n")

        obs.timer_remove(G.callback)
        G.outputActive = False




# declaring global variables
G = SimpleNamespace()

G.sources               = []
G.bitrate_tick          = 10        # PENWY : interval between each bitrate change
G.callback              = update_bitrate
G.maxVolume             = 60        # in dB
G.maxBitrate            = 5000      # in kbps
G.minBitrate            = 100       # in kbps
G.dampening             = 1
G.lock                  = False
G.noises                = [-999]    # volume (default at 999)
G.outputType            = 0         # ( 0 = None, 1 = recording, 2 = streaming, 3 = both)
G.outputActive          = False
G.settings              = None      # to set OBS saved settings



def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)


    savedSourceName = obs.obs_data_get_string(settings, "source_name0")

    if savedSourceName is not None:
        Source(obs.obs_data_get_string(settings, "source_name0"))
    else:
        Source("Desktop Audio")

def script_unload():
    obs.timer_remove(G.callback)
    obs.obs_frontend_remove_event_callback(on_event)

    for source in G.sources:
        if source.volmeter is not None:                  # PENWY : checking if a volmeter has actually been created before destroying it
            obs.obs_volmeter_remove_callback(source.volmeter, volmeter_callback, None)
            obs.obs_volmeter_destroy(source.volmeter)



##########################################################################################



# Description displayed in the Scripts dialog window
def script_description():
  return """<center><h2>Accurately Shitty Streams!!</h2></center>

            <p>Decreases the bitrate of the stream as audio levels increase!!</p>

            <p>By satalight (:</p>
            <p>Check <a href="https://github.com/satasatalight">the repo</a> for more information.</p>"""



# Called to display the properties GUI
def script_properties():
    props       = obs.obs_properties_create()
    sourceGroup = obs.obs_properties_create()
    
    obs.obs_properties_add_group            (props, "source_group", "Audio Sources:", obs.OBS_GROUP_NORMAL, sourceGroup)
    obs.obs_properties_add_button           (sourceGroup, "add_button", "Add Source", add_source_element)
    obs.obs_properties_add_button           (sourceGroup, "remove_button", "Remove Source", remove_source_element)
    sourceList = obs.obs_properties_add_list(sourceGroup, "source_name0", "Source #1:", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    
    obs.obs_properties_add_int              (props, "max_volume", "Maximum Volume (in dB):", 1, 99, 10)
    obs.obs_properties_add_int              (props, "max_bitrate", "Maximum Bitrate (in kbps):", 100, 99999, 100)
    obs.obs_properties_add_float_slider     (props, "damp_scale", "Dampening:", 0.2, 1, 0.01)

    populate_list_property_with_source_names(sourceList)

    return props



def add_source_element(props, prop, *args, **kwargs):
    source                  = Source("Desktop Audio")
    index                   = len(G.sources)
    sourceGroupProperties   = obs.obs_property_group_content( obs.obs_properties_get(props, "source_group") )
    sourceList              = obs.obs_properties_add_list(sourceGroupProperties, "source_name%d" % (index - 1), "Source #%d:" % index, 
                                obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    savedSourceName         = obs.obs_data_get_string(G.settings, "source_name%d" % (index - 1))
    
    if savedSourceName is not None:
        source.name = savedSourceName

    if G.outputActive:
        source.attach_source()
    
    populate_list_property_with_source_names(sourceList)

    # print(G.sources)

    return True # return True to update props screen

def remove_source_element(props, prop, *args, **kwargs):
    index = len(G.sources) - 1

    if index > 0:
        sourceGroupProperties   = obs.obs_property_group_content( obs.obs_properties_get(props, "source_group") )
        source                  = G.sources[index]
        
        obs.obs_properties_remove_by_name   (sourceGroupProperties, "source_name%d" % index)
        obs.obs_volmeter_destroy            (source.volmeter)
        G.sources.remove                    (source)
        
        # print(G.sources)

        return True



# Adds list of media sources (taken from https://github.com/obsproject/obs-studio/wiki/Scripting-Tutorial-Source-Shake) 
def populate_list_property_with_source_names(list_property):
  obsSources = obs.obs_enum_sources()
  obs.obs_property_list_clear(list_property)

  for obsSource in obsSources:
    name = obs.obs_source_get_name(obsSource)
    obs.obs_property_list_add_string(list_property, name, name)

  obs.source_list_release(obsSources)



# Called to set default values of data settings
def script_defaults(settings):
    obs.obs_data_set_default_int    (settings, "max_volume", 60)
    obs.obs_data_set_default_int    (settings, "max_bitrate", 5000)
    obs.obs_data_set_default_double (settings, "damp_scale", 0.7)
    obs.obs_data_set_default_string (settings, "source_name0", "Desktop Audio")



# Called after change of settings including once after script load
def script_update(settings):
    # print(obs.obs_data_get_json(settings))

    G.settings      = settings
    G.maxVolume     = obs.obs_data_get_int(settings, "max_volume")
    G.maxBitrate    = obs.obs_data_get_int(settings, "max_bitrate")
    G.dampening     = 1.2 - obs.obs_data_get_double(settings, "damp_scale")
    
    for i in range(len(G.sources)):
        sourceName = obs.obs_data_get_string(settings, "source_name" + str(i))
        # print("source_name%d: %s" % (i, sourceName))

        if G.sources[i].name != sourceName and sourceName is not None and sourceName is not "":
            # print("Setting Source " + str(i) + " from " + G.sources[i].name + " to " + sourceName)
            G.sources[i].name = sourceName

            if G.outputActive:
                G.sources[i].attach_source()