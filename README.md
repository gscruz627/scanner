# Location Audit App
This app will try to read the State Tag barcode from a computer either with the camera or a physical barcode reader (keyboard-like) and audit the computer with the selected location on ITSAM
The computer's location will also be set to the selected location. Also, if the computer is checked out to a location, it will check it out again with this new location instead.
If the computer is checked out to a user, the location won't change, but the computer will still be audited.

## Instructions
Before running the program:
- Make sure Python 3.12 or under is installed (The Library zxing-cpp, used for reading barcode from camera does not yet support the newest version of Python)
- If this is your first time running it, run `pip install -r '\\itsfs\Software\TRC\Code\Audit Scanner App\requirements.txt'`
- Run the app with `python '\\itsfs\Software\TRC\Code\Audit Scanner App\app.py`

When Running the program:
1. Set up a location to audit the computers to be read, touch on the "Location" textbar and use the on-screen keyboard
2. If using the camera, get as close and clear as possible to the barcode with the camera.
3. If using the barcode scanner, touch on the "Barcode" textbar before scanning anything, and keep the focus there.
4. When a message appears on top "Barcode Found. Audit ..." or "Location Not Found", wait until the message disappears (5 seconds) before trying to scan again.
   ![image](https://github.com/user-attachments/assets/cd063250-69df-4b1c-9972-b009363ec4d6)

6. You can switch between camera and physical reader mode with a button on the lower part.
7. Preferibly only plug in the physical reader when reading with it, because it makes the camera slower on camera mode.

## Troubleshooting
- If you get an error on the terminal [ERROR:0@1.386] ... Camera index out of range. Open the python file and set `camera = cv2.VideoCapture(0)` to a different index. (If on a computer, 0 is the first webcam, if on a tablet, 0 is the front camera, 1 is the back camera, 2 if more external cameras)
- If you get a Location Not Found error, format the location to BB XXX, where BB is the building, and XXX is the room number, like BA 269 or SM 130.
- If you are scanning with the barcode and the location textbar fills with numbers, that means you did not click on the "Barcode" textbar, remove the numbers (this is the asset tag) from the location textbar and touch the "Barcode" textbar.

## App with Location Only
The second python file works very similar to the other one, but instead, it will only show the current location (on ITSAM) if you were ever to only need this instead of auditing.
