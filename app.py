import cv2
import urllib3
import tkinter as tk
from PIL import Image, ImageTk
import requests
from PIL import Image
import zxingcpp
import time
import subprocess
from threading import Thread
import psutil
from dotenv import load_dotenv
from os import getenv
import customtkinter

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

load_dotenv()
# Suppress only the single InsecureRequestWarning from urllib3 needed for this use case
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
readingWithCamera = True
waitingForInput = False
asset_tag_read = ""


# Processes and other global objects
keyboard_process = None
onscreen_error_message = ""
updatingCompName = ""
updatingOldLocationName = ""
updatingNewLocationName = ""
SNIPEIT_API_KEY = getenv('SNIPEIT_API_KEY')
SNIPEIT_ROUTE = getenv("SNIPEIT_ROUTE")
headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {SNIPEIT_API_KEY}"
}

# Camera, VideoCapture(n), where n is the camera index, front and back.
# I set it to 1, this is for the back camera. 0 is for the front camera. 0 is also for the first webcam in a pc.
# If there is no camera feed, replace this for a valid index.
camera = cv2.VideoCapture(1)

'''
WHEN BARCODE CAN BE READ
This sets a success message to the barcode label.
Sets the updating thread to None, force sleeps for 5 seconds (cannot read barcodes during this time)
After 5 seconds, set the barcode label to 'Ready to read' again.
'Restart' the updating thread to this function, so it runs when detecting a barcode.
'''
def update_message():
    global updatingThread
    barcodeEntry.pack_forget()
    barcode_label.configure(text=f"Barcode Found, Audit {updatingCompName}. Location change: {updatingOldLocationName} to {updatingNewLocationName}", text_color="green")
    updatingThread = None
    time.sleep(5)
    barcode_label.configure(text="Ready to Read Barcode", text_color="black")
    barcodeEntry.pack()
    barcodeEntry.delete(0, tk.END)
    updatingThread = Thread(target=update_message)

'''
WHEN BARCODE CANNOT BE READ
This sets an eror message to the barcode label.
Sets the error thread to None, force sleeps for 5 seconds (cannot read barcodes during this time)
After 5 seconds, set the barcode label to 'Ready to read' again.
'Restart' the error thread to this function, so it runs when detecting a barcode. Reset the error message.

'''
def error_message():
    global errorThread
    global onscreen_error_message
    barcodeEntry.pack_forget()
    barcode_label.configure(text=onscreen_error_message, text_color="red")
    errorThread = None
    time.sleep(5)
    barcode_label.configure(text="Ready to read barcode", text_color="black")
    barcodeEntry.pack()
    barcodeEntry.delete(0, tk.END)
    errorThread = Thread(target=error_message)
    onscreen_error_message = ""

# Define the threads, after defining the functions.
errorThread = Thread(target=error_message)
updatingThread = Thread(target=update_message)

'''
REQUESTS TO ITSAM TO CHANGE LOCATION AND AUDIT
Gets passed serial by the barcode reader and the location by locationEntry.get()
'''
def update_location(serial,location):
    global updatingCompName
    global updatingOldLocationName
    global updatingNewLocationName
    global onscreen_error_message
    
    # Get the computer ID, its computer name, and its current location.
    response = requests.get(f"{SNIPEIT_ROUTE}/api/v1/hardware/bytag/{serial}", headers=headers, verify=False)
    data = response.json()
    id_value = data.get("id")
    name_value = data.get("name")
    serial_value = data.get("serial")
    actual_name = ""
    if serial_value:
        actual_name = serial_value
    elif name_value:
        actual_name = name_value
    else:
        actual_name = "No Name"

    # Check if this is on a location already or not
    if not data.get("location"):
        location_value = "Nowhere"
    else:
        location_value = data.get("location").get("name")

    response = requests.get(f"{SNIPEIT_ROUTE}/api/v1/locations?search={location}", headers=headers, verify=False)
    validLocation = response.json()

    if not validLocation["rows"]:
        onscreen_error_message = "Location not found"
        errorThread.start()
        return
    validLocationId = validLocation["rows"][0]["id"]

    # If this is not checked out to a user, check it out to this Location
    if not data.get('assigned_to'):
        payload3 = { "checkout_to_type": "location",
                         "assigned_location":  validLocationId}
            # Get the location ID from a location string.
        response = requests.post(f"{SNIPEIT_ROUTE}/api/v1/hardware/{id_value}/checkout", headers=headers, verify=False, json=payload3)
    if data.get("assigned_to") and (not data.get('assigned_to').get('username')):
        if not data.get("assigned_to").get("username"):
            payload3 = { "checkout_to_type": "location",
                         "assigned_location":  validLocationId}
            # Get the location ID from a location string.
            response = requests.post(f"{SNIPEIT_ROUTE}/api/v1/hardware/{id_value}/checkout", headers=headers, verify=False, json=payload3)
    else:
        pass
    
    # Payload for change location and audit.
    payload = {
        'location_id': validLocationId 
    }
    
    payload2 = {
        'asset_tag': serial,
        'location_id': validLocationId
    }

    # Request to change location of computer
    response = requests.put(f"{SNIPEIT_ROUTE}/api/v1/hardware/{id_value}", headers=headers, json=payload, verify=False)
    updatingCompName = actual_name
    updatingOldLocationName = location_value
    updatingNewLocationName = location

    # Request to audit computer with selected location
    response = requests.post(f"{SNIPEIT_ROUTE}/api/v1/hardware/audit", headers=headers, json=payload2, verify=False)

    # At this point, both requests are successful, start the success thread, which runs update_message()
    updatingThread.start()


'''
TO SWITCH FROM CAMERA READ TO READER
This will run when the change button is pressed and will change whether the camera will
be used to read the barcode or the physical barcode scanner will be used instead,
and viceversa.
'''
def switchMethod():
    global readingWithCamera
    global scannerThread
    global savedInputFromLocation
    if readingWithCamera:
        camera_label.pack_forget()
        readingWithCamera = False
        barcodeForm.pack()
        barcodeFormMessage.pack(side=tk.LEFT, padx=5)
        barcodeEntry.pack(side=tk.LEFT, padx=5)

    else:        
        barcodeEntry.pack_forget()
        barcodeFormMessage.pack_forget()
        camera_label.pack()
        readingWithCamera = True
        update_frame()

'''
TO DECODE BARCODE FROM FEED
This runs every frame, will try to read barcodes from the current frame.
'''
def decodeBarcode(frame):
    results = zxingcpp.read_barcodes(frame)
    if results:
        asset_tag = results[0].text[1:]
        update_location(asset_tag, locationEntry.get())

'''
UPDATES THE FRAME
Get a frame from the camera feed.
update the camera label to contained the imaged frame
If updating thread is active (not updating) and the entry for location is not emtpy, try decoding.
Update the frame every 10ms
'''
def update_frame():
    global readingWithCamera
    global tk_img
    if readingWithCamera:
        result, frame = camera.read()
        if result:
            # Convert the frame from BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert the frame into a PIL image and then to a Tkinter-compatible image
            img = Image.fromarray(frame_rgb)
            tk_img = customtkinter.CTkImage(img, size=(700,500))
            # Update the label with the new image
            camera_label.configure(image=tk_img)
            if updatingThread is not None and locationEntry.get() != "" and errorThread is not None:
                decodeBarcode(frame)
            # Continue updating the frame every 10ms
            camera_label.after(20, update_frame)

'''
OPEN THE ON SCREEN KEYBOARD FOR THE TABLETS
if keyboard is not open, start the process TabTip.exe (native on-screen keyboard)
'''

def openOnScreenKeyboard(o):
    global keyboard_process
    if keyboard_process is None:
        keyboard_process = subprocess.Popen(r"C:\Program Files\Common Files\microsoft shared\ink\TabTip.exe", shell=True)
'''
CLOSE THE ON SCREEN KEYBOARD FOR THE TABLETS
Apparently process.terminate() process.kill() won't actually do either, and the process is still running,
Thus we loop through all active processes, if its name is 'TabTip.exe' terminate it.
Set the process to none.
'''
def closeOnScreenKeyboard(o):
    global keyboard_process
    if keyboard_process is not None:
        for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'TabTip.exe':
                    try:
                        proc.terminate()
                    except psutil.AccessDenied:
                        print("Access denied for terminating TabTip.exe")
                    except psutil.NoSuchProcess:
                        pass
        keyboard_process = None
    
def checkKey(event):
    global asset_tag_read
    if updatingThread is None:
        return
    if event.char in ["0","1","2","3","4","5","6","7","8","9"]:
        asset_tag_read += str(event.char)
    elif event.keysym == "Return":
        asset_tag_read = asset_tag_read[1:]  # Check if the Enter key was pressed
        if locationEntry.get() != "":
            update_location(asset_tag_read, locationEntry.get())
        asset_tag_read = ""
        barcodeEntry.delete(0, tk.END)
    else:
        barcodeEntry.delete(0, tk.END)



'''
CLOSE ON SCREEN KEYBOARD IF WINDOW IS CLOSED
Then destroy the root window
'''
def on_window_close():
    closeOnScreenKeyboard(None)
    camera.release()
    root.destroy()

# This configures the main window, divides it into rows.
root = customtkinter.CTk()
root_width = root.winfo_screenwidth()
root_height = root.winfo_screenheight()
root.geometry(f"{root_width}x{root_height}")

root.rowconfigure(0, weight=1)
root.rowconfigure(1, weight=1)
root.rowconfigure(2, weight=1)
root.columnconfigure(0, weight=1)


# This is about the top section which displays a message: Ready to read, cannot update, or updated successfully.
# has the textbox

topsection = customtkinter.CTkFrame(root)
topsection.grid(row=0, column=0, sticky="nsew")

barcode_label = customtkinter.CTkLabel(topsection, text="Ready to read barcode", font=("Arial", 40, "bold"), pady=10, fg_color="transparent")
barcode_label.pack()

locationForm = customtkinter.CTkFrame(topsection)
locationForm.pack()
newLocationMessage = customtkinter.CTkLabel(locationForm, text="Location:", font=("Arial", 40, "bold"), fg_color="transparent")
newLocationMessage.pack(side=tk.LEFT, padx=5)
locationEntry = customtkinter.CTkEntry(locationForm, width=200, font=("Arial", 40), fg_color="transparent")
locationEntry.bind("<FocusIn>", openOnScreenKeyboard)
locationEntry.bind("<Button-1>", openOnScreenKeyboard)
locationEntry.pack(side=tk.LEFT, padx=5)

# This is about the middle section, which shows the camera or the barcode entry

camera_place = customtkinter.CTkFrame(root)
camera_place.grid(row=1, column=0, sticky="nsew")
camera_label = customtkinter.CTkLabel(camera_place, text="")
camera_label.pack()

#Barcode
barcodeForm = customtkinter.CTkFrame(camera_place)
barcodeFormMessage = customtkinter.CTkLabel(barcodeForm, text="Barcode (Click here to Start Scanning):", font=("Arial", 26), fg_color="transparent")
barcodeEntry = customtkinter.CTkEntry(barcodeForm, width=200, font=("Arial", 26), fg_color="transparent")
barcodeEntry.bind("<KeyPress>", checkKey)


# This is the lower section, to change from camera to reader

lowersection = customtkinter.CTkFrame(root)
choice_button = customtkinter.CTkButton(lowersection, text='Change Camera / Reader', command=switchMethod, font=("Arial", 26), corner_radius=5, border_spacing=30)
choice_button.pack()
lowersection.grid(row=2, column=0, sticky="nsew")

# This binds 'closeOnScreenKeyboard' (actually only kills the process) if the user left clicks (Button 1) on any part of the screen
# Also binds on_window_close to the close window protocol on root.

root.bind("<Button-1>", closeOnScreenKeyboard)
root.protocol("WM_DELETE_WINDOW", on_window_close)

# Start the camera feed update loop, run the window.
update_frame()
root.mainloop()