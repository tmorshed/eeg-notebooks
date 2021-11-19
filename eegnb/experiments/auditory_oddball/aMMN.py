import os
from time import time, sleep
from glob import glob
from random import choice
from optparse import OptionParser
import numpy as np
from pandas import DataFrame
from psychopy import visual, core, event, sound, prefs, logging
import h5py
import socket
import json
from eegnb import generate_save_fn
import eegnb.devices.eeg as eeg


prefs.resetPrefs()
prefs.hardware['audioDriver'] = ["portaudio"]
prefs.hardware['audioLib'] = ['PTB', 'pyo','pygame']

def sendpack(data_to_send):
    event_to_send = json.dumps(data_to_send).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(event_to_send, ("239.128.35.86", 7891))
    
def present(
    save_fn: str = None,
    duration=120,
    stim_types=None,
    itis=None,
    additional_labels={},
    secs=0.07,
    volume=0.8,
    eeg=None,
    kernel=None
):
    markernames = [1, 2]
    record_duration = np.float32(duration)

    ## Initialize stimuli
    # aud1 = sound.Sound('C', octave=5, sampleRate=44100, secs=secs)
    aud1 = sound.Sound(440, secs=secs)  # , octave=5, sampleRate=44100, secs=secs)
    aud1.setVolume(volume)

    # aud2 = sound.Sound('D', octave=6, sampleRate=44100, secs=secs)
    aud2 = sound.Sound(528, secs=secs)
    aud2.setVolume(volume)
    auds = [aud1, aud2]

    # Setup trial list
    trials = DataFrame(dict(sound_ind=stim_types, iti=itis))

    for col_name, col_vec in additional_labels.items():
        trials[col_name] = col_vec

    # Setup graphics
    mywin = visual.Window(
        [1920, 1080], monitor="testMonitor", units="deg", fullscr=True
    )
    fixation = visual.GratingStim(win=mywin, size=0.2, pos=[0, 0], sf=0, rgb=[1, 0, 0])
    fixation.setAutoDraw(True)
    mywin.flip()
    iteratorthing = 0

    # start the EEG stream, will delay 5 seconds to let signal settle
    if eeg:
        eeg.start(save_fn, duration=record_duration)

    show_instructions(10)

    # Start EEG Stream, wait for signal to settle, and then pull for start point
    start = time()
    
    if kernel:
        timestamp = start*1e9
        timestamp = int(timestamp)
        data_to_send = {
        "id": 0,
        "timestamp": timestamp,
        "event": "start_experiment",
        "value": "0",
        }
        sendpack(data_to_send)
        evlen=0
        
    # Iterate through the events
    for ii, trial in trials.iterrows():

        iteratorthing = iteratorthing + 1

        # Inter trial interval
        core.wait(trial["iti"])

        # Select and display image
        ind = int(trial["sound_ind"])
        auds[ind].stop()
        auds[ind].play()

        # Push sample
        if eeg:
            timestamp = time()
            if eeg.backend == "muselsl":
                marker = [additional_labels["labels"][iteratorthing - 1]]
                marker = list(map(int, marker))
            else:
                marker = additional_labels["labels"][iteratorthing - 1]
            eeg.push_sample(marker=marker, timestamp=timestamp)
        
        if kernel:
            if trial['sound_ind']==0:
              dev_v_st = "event_deviant"
            if trial['sound_ind']==1:
              dev_v_st = "event_standard"
            timestamp = time()*1e9
            timestamp = int(timestamp)
            data_to_send = {
            "id": ii+1,
            "timestamp": timestamp,
            "event": dev_v_st,
            "value":"1",
            }
            sendpack(data_to_send)
            evlen += 1            
            
        mywin.flip()
        if len(event.getKeys()) > 0:
            break
        if (time() - start) > record_duration:
            break

        event.clearEvents()

        if iteratorthing == 1798:
            sleep(10)

    # Cleanup
    if eeg:
        eeg.stop()

    mywin.close()
    
    if kernel:
        timestamp = time()*1e9
        timestamp = int(timestamp)
        data_to_send = {
        "id": evlen+1,
        "timestamp": timestamp,
        "event": "end_experiment",
        "value": "2",
        }
        sendpack(data_to_send)

def show_instructions(duration):

    instruction_text = """
    Welcome to the aMMN experiment! 
 
    Stay still, focus on the centre of the screen, and try not to blink. 

    This block will run for %s seconds.

    Press spacebar to continue. 
    
    """
    instruction_text = instruction_text % duration

    # graphics
    mywin = visual.Window([1600, 900], monitor="testMonitor", units="deg", fullscr=True)

    mywin.mouseVisible = False

    # Instructions
    text = visual.TextStim(win=mywin, text=instruction_text, color=[-1, -1, -1])
    text.draw()
    mywin.flip()
    event.waitKeys(keyList="space")

    mywin.mouseVisible = True
    mywin.close()
