import os
from time import time
from glob import glob
from random import choice
from optparse import OptionParser

import numpy as np
from pandas import DataFrame
from psychopy import visual, core, event, prefs, logging
import h5py
import socket
import json
from eegnb import generate_save_fn
from eegnb.stimuli import FACE_HOUSE

__title__ = "Visual N170"

prefs.resetPrefs()
prefs.hardware['audioDriver'] = ["portaudio"]
prefs.hardware['audioLib'] = ['PTB', 'pyo','pygame']

def sendpack(data_to_send):
    event_to_send = json.dumps(data_to_send).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(event_to_send, ("239.128.35.86", 7891))
    
def present(duration=120, eeg=None, kernel=None, save_fn=None):
    n_trials = 2010
    iti = 0.4
    soa = 0.3
    jitter = 0.2
    record_duration = np.float32(duration)
    markernames = [1, 2]

    # Setup trial list
    image_type = np.random.binomial(1, 0.5, n_trials)
    trials = DataFrame(dict(image_type=image_type, timestamp=np.zeros(n_trials)))

    def load_image(fn):
        return visual.ImageStim(win=mywin, image=fn)

    # start the EEG stream, will delay 5 seconds to let signal settle

    # Setup graphics
    mywin = visual.Window([1600, 900], monitor="testMonitor", units="deg", fullscr=True)

    faces = list(map(load_image, glob(os.path.join(FACE_HOUSE, "faces", "*_3.jpg"))))
    houses = list(map(load_image, glob(os.path.join(FACE_HOUSE, "houses", "*.3.jpg"))))
    stim = [houses, faces]

    # Show the instructions screen
    show_instructions(duration)

    if eeg:
        if save_fn is None:  # If no save_fn passed, generate a new unnamed save file
            save_fn = generate_save_fn(eeg.device_name, "visual_n170", "unnamed")
            print(
                f"No path for a save file was passed to the experiment. Saving data to {save_fn}"
            )
        eeg.start(save_fn, duration=record_duration + 5)
    
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
        
    # Start EEG Stream, wait for signal to settle, and then pull timestamp for start point
    start = time()
    
    # Iterate through the events
    for ii, trial in trials.iterrows():
        # Inter trial interval
        core.wait(iti + np.random.rand() * jitter)

        # Select and display image
        label = trials["image_type"].iloc[ii]
        image = choice(faces if label == 1 else houses)
        image.draw()

        # Push sample
        if eeg:
            timestamp = time()
            if eeg.backend == "muselsl":
                marker = [markernames[label]]
            else:
                marker = markernames[label]
            eeg.push_sample(marker=marker, timestamp=timestamp)
        
        if kernel:
            if trial['image_type']==0:
              dev_v_st = "houses"
            if trial['image_type']==1:
              dev_v_st = "faces"
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

        # offset
        core.wait(soa)
        mywin.flip()
        if len(event.getKeys()) > 0 or (time() - start) > record_duration:
            break

        event.clearEvents()

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
    Welcome to the N170 experiment! 
 
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
