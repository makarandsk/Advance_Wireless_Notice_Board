import time
import firebase_admin
import threading
from firebase_admin import credentials, firestore
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message, textsize
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT
from gpiozero import Buzzer
from time import sleep
from datetime import datetime


serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial,cascaded=16,block_orientation=-90,blocks_arranged_in_reverse_order=True)

cred = credentials.Certificate("/home/pi/Downloads/adv.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
# Create an Event for notifying main thread.
callback_done = threading.Event()

buzzer = Buzzer(17)

is_new_notice_available = False

old_notice_time = None

new_notice_data = {}

disp_notice_data = {}

# Create a callback on_snapshot function to capture changes
def convert_to_date_string(date):
	if date is not None:
		return date.strftime('%d/%b/%Y')
	else: return "-"
	
def convert_to_time_string(date):
	if date is not None:
		return date.strftime('%I:%M:%S %p')
	else: return "-"

def on_snapshot(doc_snapshot, changes, read_time):
    global old_notice_time
    global is_new_notice_available
    global new_notice_data
    
    for doc in doc_snapshot:
        timestamp = doc.get("DT")
        if old_notice_time is None:
            old_notice_time = timestamp
            
        if timestamp >= old_notice_time:
            timestamp_dt=datetime.fromtimestamp(doc.get("DT") / 1000)
            new_notice_data["text"] = doc.get('Text')
            new_notice_data["date"] = convert_to_date_string(timestamp_dt)
            new_notice_data["time"] = convert_to_time_string(timestamp_dt)
            
            
            uid=doc.get('uid')
            uid_doc = db.collection('users').document(uid).get()
            new_notice_data["uname"] = uid_doc.get('uname')
            
            old_notice_time = timestamp
            
            is_new_notice_available = True
                    
    #callback_done.set()
    #callback_done.wait()       

doc_ref = db.collection("data").order_by("DT",direction=firestore.Query.DESCENDING).limit(1)
print("test2")
#Watch the document
doc_watch = doc_ref.on_snapshot(on_snapshot)
#callback_done.wait()

while(True):
    if new_notice_data.keys() != {"text", "date", "time", "uname"}:
        print("waiting for msg")
        continue
    
    if is_new_notice_available or disp_notice_data.keys() != {"text", "date", "time", "uname"}:
        print(is_new_notice_available)
        buzzer.on()
        time.sleep(1)
        buzzer.off()
        disp_notice_data = new_notice_data
        is_new_notice_available = False
        
    display_text = disp_notice_data["text"]
    display_date = disp_notice_data["date"]
    display_time = disp_notice_data["time"]
    display_uname = disp_notice_data["uname"]
    
    v1= f'Notice: {display_text} on {display_date} at {display_time} by {display_uname}'
    w, h = textsize(v1, font=proportional(CP437_FONT))
    print("Show running text: " + v1)
    show_message(device,v1 , fill="white", font=proportional(CP437_FONT),scroll_delay=0.04)
    time.sleep(0.5)
        


