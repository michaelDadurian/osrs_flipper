#!/usr/bin/env python3
import time
import subprocess
import logging
import pyautogui
import os
import threading, queue
import numpy
import PIL
import pytesseract as pytesseract
import cv2 as cv2
from enum import Enum
from modules.real_mouse import move_mouse_click

log = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.ERROR)
stream_handler.setFormatter(formatter)

log.addHandler(stream_handler)


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
        self.window_id = create_window(self.window_info)

        log.info("Running instance " + str(self.id))

        time.sleep(3)
        take_screenshot(self.window_info, self.screenshots_path + '/login.png')

        log.info('INSTANCE ' + str(self.id) + ': logging in user ' + self.acct_info['user'])

        # Login user
        loc = None
        while loc is None:
            loc = locate_center('existing_user.png', self.window_info, confidence=.8)
        
        move_mouse_click(loc.x, loc.y)

        pyautogui.write(self.acct_info['user'])
        pyautogui.press('enter')
        pyautogui.write(self.acct_info['pw'])
        pyautogui.press('enter')

        time.sleep(10)

        loc = locate_center('click_to_play.png', self.window_info, confidence=.6)
        move_mouse_click(loc.x, loc.y)

        time.sleep(2)

        #logged_in = take_screenshot(self.window_info, self.screenshots_path + '/starting_inventory.png')

        adjusted_region = self.window_info
        adjusted_region.size_y += 40
        # Turn public chat off
        loc = locate_center('public_on.png', adjusted_region, confidence=.6)
        move_mouse_click(loc.x, loc.y, button='right')
        move_mouse_click(loc.x, loc.y - 80)

        # Examine money
        loc = locate_center('money_icon.png', self.window_info, confidence=.7)
        move_mouse_click(loc.x, loc.y, button='right')
        move_mouse_click(loc.x, loc.y + 60)

        gp_text_region = self.window_info
        gp_text_region.location_x += 165
        gp_text_region.location_y += 505
        gp_text_region.size_x = 100
        gp_text_region.size_y = 19

        log.info("Checking gp region")
        log.info(str(gp_text_region.location_x), str(gp_text_region.location_y), str(gp_text_region.size_x), 
        str(gp_text_region.size_y))
        gp_img_path = self.screenshots_path + '/gp_text.png'
        gp_text_img = take_screenshot(gp_text_region, gp_img_path)

        val = tesser_money_image(gp_img_path)
        print(val)

        '''
        loc = None
        while loc is None:
            loc = locate_box('money_icon.png', region=self.window_info, confidence=.6)

        pyautogui.screenshot('gp_img.png', region=(loc.left-5, loc.top-15, loc.width+5, loc.height-8))
        val = tesser_money_image('gp_img.png')
        print(val)
        '''
        #change world to member or f2p (member=305 f2p=308)
        #login user

def locate_box(img_name, region, confidence=1):
    loc = None
    log.info("Looking for " + img_name + " box...")
    while loc is None:
        loc = pyautogui.locateOnScreen(os.getcwd() + '/compare_ss/' + img_name,
            region=(region.location_x, region.location_y, region.size_x, region.size_y),
            confidence=confidence)

    log.info("Found image")
    return loc

def locate_center(img_name, region, confidence=1):
    loc = None
    log.info("Looking for " + img_name + " center...")
    log.info(str(region.location_x) + ' ' + str(region.location_y) + ' ' + str(region.size_x) + ' ' + str(region.size_y))
    while loc is None:
        loc = pyautogui.locateCenterOnScreen(os.getcwd() + '/compare_ss/' + img_name, 
            region=(region.location_x, region.location_y, region.size_x, region.size_y), 
            confidence=confidence)
    
    log.info("Found image")
    return loc

def tesser_money_image(image):
    image = cv2.imread(image, 0)
    thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    txt = pytesseract.image_to_string(thresh, lang='eng',config='--psm 7')

    txt = ''.join(txt.split())
    txt_list = list(txt)
    
    for i in range(len(txt_list)):
        if txt_list[i] in ['o', 'O']:
            txt_list[i] = '0'
        elif txt_list[i] in ['l', 'I', 'i']:
            txt_list[i] = '1'
        elif txt_list[i] in ['M', 'm']:
            txt_list[i] = '000000'
        elif txt_list[i] in ['K', 'k']:
            txt_list[i] = '000'
        elif txt_list[i] in ['s', 'S']:
            txt_list[i] = '5'
        elif txt_list[i] == 'W':
            txt_list[i] = '40'
        
    print(txt_list)
    txt = int(''.join(txt_list))
    return(txt)
    
def take_screenshot(window_info, screenshot_path):
    return pyautogui.screenshot(
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
