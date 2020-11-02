#!/usr/bin/env python3
import time
import subprocess
import logging
import pyautogui
import os
import threading, queue
from enum import Enum
from modules.real_mouse import move_mouse_click

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

actions_queue = queue.Queue()

instances = {}
num_clients = 0

'''
window setup:
    RESOLUTION SIZE: xrandr | grep \* | cut -d' ' -f4
    FIND WINDOW IDS: xdotool search --onlyvisible --name runescape
    RESIZE WINDOW: xdotool windowsize $WINDOWID X Y
        e.g
        4 windows:
        window_width = resolution.width / 2
        window_height = resolution.height / 2

        move to 0 0
        move to 1080 0
        move to 0 1080
        move to 1080 1080
'''

class InstanceStatus(Enum):
    INACTIVE = 0
    RUNNING = 1
    ERROR = 2

class WindowInfo:
    def __init__(self, location_x, location_y, size_x, size_y):
        self.location_x = location_x
        self.location_y = location_y
        self.size_x = size_x
        self.size_y = size_y

class BotInstance:
    def __init__(self, id, acct_info, window_info):
        self.id = id
        self.acct_info = acct_info
        self.window_info = window_info
        self.status = InstanceStatus.INACTIVE
        self.screenshots_path = os.getcwd() + '/instance_' + str(self.id) + '_imgs'
        if not os.path.exists(self.screenshots_path):
            os.mkdir(self.screenshots_path)


    def run(self):
        self.status = InstanceStatus.RUNNING
        logging.info("Running instance " + str(self.id))
        self.window_id = create_window(self.window_info)

        time.sleep(3)
        take_screenshot(self.window_info, self.screenshots_path + '/login.png')

        logging.info('Logging in user ' + self.acct_info['user'] + ' with pass ' + self.acct_info['pw'])

        loc = None
        while loc is None:
            loc = locate_center('existing_user.png', confidence=.8)
        
        move_mouse_click(loc.x, loc.y)

        pyautogui.write(self.acct_info['user'])
        pyautogui.press('enter')
        pyautogui.write(self.acct_info['pw'])
        pyautogui.press('enter')

        time.sleep(10)
        loc = None
        while loc is None:
            loc = locate_center('click_to_play.png', confidence=.6)
    
        move_mouse_click(loc.x, loc.y)

        #change world to member or f2p (member=305 f2p=308)
        #login user

def locate_center(img_name, confidence=1):
    return pyautogui.locateCenterOnScreen(os.getcwd() + '/compare_ss/' + img_name, confidence=confidence)

def take_screenshot(window_info, screenshot_path):
    pyautogui.screenshot(
        screenshot_path,     
        region=(
            window_info.location_x,
            window_info.location_y,
            window_info.size_x,
            window_info.size_y        
        )
    )

def create_window(window_info):
    subprocess.Popen(["/snap/bin/runescape.osrs"], stdout=subprocess.DEVNULL)
    time.sleep(7)
    result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', 'runescape'], capture_output=True, text=True)
    
    window_id = result.stdout.split()[-1]

    subprocess.run(['xdotool', 'windowsize', window_id, str(window_info.size_x), str(window_info.size_y)])
    subprocess.run(['xdotool', 'windowmove', window_id, str(window_info.location_x), str(window_info.location_y)])

    return window_id

def worker():
    while True:
        instance_action = actions_queue.get()
        logging.info("Working on action: " + str(instance_action))
        instance_action()
        actions_queue.task_done()
        logging.info("Task done")

def main(args):
    global instances
    global num_clients

    num_clients = int(args.num_clients)
    acct_file = args.acct_file

    window_dimensions = {
        0: WindowInfo(0, 0, 990, 540), 
        1: WindowInfo(0, 1080, 990, 540),
        2: WindowInfo(1080, 0, 990, 540),
        3: WindowInfo(1080, 1080, 990, 540)
    }

    i = 0
    for line in open(acct_file):
        if i < num_clients:
            toks = line.split(' ')
            acct_info = {
                'user': toks[0],
                'pw': toks[1],
                'member': True if toks[2] == 'True' else False,
                'logged_in': False
            }

            # calc window dimensions based on resolution + num clients
            window_info = window_dimensions[i]

            instance = BotInstance(i, acct_info, window_info)
            instances[i] = instance

            actions_queue.put(instance.run)
        
        i += 1

    threading.Thread(target=worker, daemon=True).start()
    actions_queue.join()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Setup multiple clients and login")
    parser.add_argument('-a', action='store', dest='acct_file', help='Accounts file')
    parser.add_argument('-n', action='store', dest='num_clients', help="Number of clients to launch")

    args = parser.parse_args()
    main(args)
