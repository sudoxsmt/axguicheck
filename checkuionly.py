import subprocess
import re


import time
import os
from ppadb.client import Client as AdbClient
import pytesseract
from PIL import Image
import json
import cv2
name_of_config = "checkui.json"

with open(name_of_config, "r") as file:
    config = json.load(file)

checkAxUITime = config["checkAxUI"]
CHECK_INTERVAL = config["waitTime"]

# Constants
PACKAGE_NAME = "com.roblox.client"
TARGET_ACTIVITY = ".ActivityNativeMain"
SCREENSHOT_PATH_DEVICE = "/sdcard/checkui.png"  # Screenshot path on the device
LOCAL_SCREENSHOT_PATH = "./screenshots/"
NAME_SCREENSHOT = "checkui.png"
IMG_FOLDER = "./img"

#for check ui
json_file = 'image.json'
robloxui = cv2.imread('screenshots/robloxui.png', cv2.IMREAD_GRAYSCALE)
axui = cv2.imread('screenshots/ax_file.png', cv2.IMREAD_GRAYSCALE)
axui2 = cv2.imread('screenshots/ax_file2.png', cv2.IMREAD_GRAYSCALE)
guiadk = cv2.imread('screenshots/guiadk.png', cv2.IMREAD_GRAYSCALE)

# Functions
def is_app_running(adb_device, package_name):
    try:
        processes = adb_device.shell("ps -A")
        return package_name in processes
    except Exception as e:
        return False

def stop_app(adb_device, package_name):
    try:
        command = f"am force-stop {package_name}"
        adb_device.shell(command)
    except Exception as e:
        return False

def is_activity_in_foreground(adb_device, package_name, target_activity):
    try:
        activity_info = adb_device.shell("dumpsys activity activities | grep ResumedActivity")
        return f"{package_name}/{target_activity}" in activity_info
    except Exception as e:
        return False 

def is_activity_splash(adb_device, package_name):
    try:
        activity_info = adb_device.shell("dumpsys activity activities | grep ResumedActivity")
        return f"{package_name}/.ActivitySplash" in activity_info
    except Exception as e:
        return False

def capture_screenshot(adb_device):
    try:
        adb_device.shell(f"screencap -p {SCREENSHOT_PATH_DEVICE}")
        adb_device.pull(SCREENSHOT_PATH_DEVICE, f"{LOCAL_SCREENSHOT_PATH}{adb_device.serial.split(":")[1]}{NAME_SCREENSHOT}")
    except Exception as e:
        return False

def search_image(query_image_path , target_image_path):
        query_image = query_image_path
        target_image = cv2.imread(target_image_path, cv2.IMREAD_GRAYSCALE)

        # Perform template matching
        result = cv2.matchTemplate(target_image, query_image, cv2.TM_CCOEFF_NORMED)

        # Define a threshold
        threshold = 0.8  # Adjust this value based on your needs

        # Find locations in the result that exceed the threshold
        locations = cv2.minMaxLoc(result)
        max_val = locations[1]

        # Check if the maximum value exceeds the threshold
        if max_val >= threshold:
                return True
        else:
                return False

def has_20_seconds_passed(file_name, json_file , flag):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            if file_name in data:
                logged_time = data[file_name]
                current_time = time.time()
                if (current_time - logged_time) >= checkAxUITime or flag:
                    # Remove the entry from the JSON file
                    del data[file_name]
                    with open(json_file, 'w') as f:
                        json.dump(data, f, indent=4)
                    return True
                else:
                    return False
            else:
                return False
    except FileNotFoundError:
        return False

def log_unprocessed_file(file_name, json_file):
    data = {}
    current_time = time.time()
    
    # Read existing data if the JSON file exists
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        pass

    # Add or update the entry
    data[file_name] = current_time

    # Write data back to the JSON file
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=4)

def check_exist(file_name, json_file):
        try:
                with open(json_file, 'r') as f:
                        data = json.load(f)
                        if file_name not in data:
                                log_unprocessed_file(file_name, json_file)
        except FileNotFoundError:
                # Log the unprocessed file if the JSON file does not exist
                log_unprocessed_file(file_name, json_file)

def checkAxUIRunning(adb_device,target_image_path):
    if search_image(robloxui,target_image_path):
            xxx = search_image(axui,target_image_path)
            yyy = search_image(axui2,target_image_path)
            if not xxx and not yyy:
                    print(f"Device {adb_device.serial}: AX UI didn't popup. Recheck..")
                    check_exist(target_image_path, json_file)
                    if has_20_seconds_passed(target_image_path, json_file,False):
                            return False
            else:
                has_20_seconds_passed(target_image_path, json_file,True)
                #return checkGuiAdk(adb_device,target_image_path)
                    
    return True

def checkGuiAdk(adb_device,target_image_path):
    nameCheckGuiAdk = f"{target_image_path}adk"
    if not search_image(guiadk,target_image_path):
        print(f"Device {adb_device.serial}: ADK didn't popup. Recheck..")
        check_exist(nameCheckGuiAdk, json_file)
        if has_20_seconds_passed(nameCheckGuiAdk, json_file,False):
            return False
    else:
        has_20_seconds_passed(nameCheckGuiAdk, json_file,True)
    
    return True


def running_process(adb_device):
    try:
        if is_app_running(adb_device, PACKAGE_NAME):
            print(f"Device {adb_device.serial}: Check UI")
            if is_activity_in_foreground(adb_device, PACKAGE_NAME, TARGET_ACTIVITY):
                capture_screenshot(adb_device)
                checkAx = checkAxUIRunning(adb_device,f"{LOCAL_SCREENSHOT_PATH}{adb_device.serial.split(":")[1]}{NAME_SCREENSHOT}")
                if not checkAx:
                    print(f"Device {adb_device.serial}: AX UI or ADK is not running on {checkAxUITime} second. Close Client")
                    stop_app(adb_device, PACKAGE_NAME)
    except RuntimeError as e:
        print(f"Device {adb_device.serial}: Offline")

start_index = 0
end_index = 9999
# ADB Client
adb_client = AdbClient(host="127.0.0.1", port=5037)
devices = adb_client.devices()
if not devices:
    raise RuntimeError("No devices connected. Check ADB setup and device connection.")

devices = devices[start_index:end_index + 1]

start_time = time.time()

try:
    # Main monitoring loop
    while True:

        for adb_device in devices:               
            running_process(adb_device)
            time.sleep(CHECK_INTERVAL)
except KeyboardInterrupt:
    print("Program interrupted. Exiting...")