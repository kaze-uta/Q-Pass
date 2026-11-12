import sys
import os
import threading
import re
import qrcode
from PIL import Image
import time
import cv2
import base64

qr_num = 0
CAPACITY = 200

def getfile(file_name):

    if re.match(r'.*\..*', file_name):
        with open(file_name, "rb") as f:
            data = f.read()
            extension = os.path.splitext(file_name)[1][1:]

    return data, extension

def create_qr(data, qr_num):
    qr = qrcode.QRCode(
    version = 1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=5,
    border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    img.save(f"qrcode{qr_num + 1}.png")
        
def show_qr():
    show_num = 1

    time.sleep(3)
    while(True):   
        try:
            img = cv2.imread(f"qrcode{show_num}.png")
            img = cv2.resize(img, (700, 700))
            cv2.imshow("img", img)
            cv2.waitKey(2000)
            delete_qr(show_num)
            show_num += 1
        except:
            cv2.destroyAllWindows()
            break
    

def delete_qr(del_num):
    try:
        os.remove(f"qrcode{del_num}.png")
    except:
        pass

def send_qr():
    i = 0
    while (long > CAPACITY * ( i - 1 )):
        if i == 0:
            bextension = extension.encode()
            create_qr(base64.b64encode(bextension), i)
        else:
            shift_data = base64.b64encode(data[CAPACITY * ( i - 1 ):CAPACITY * i])
            create_qr(shift_data, i)
        i += 1
    else:
        blast = "last".encode()
        create_qr(base64.b64encode(blast), i)

if __name__ == "__main__":
    args = sys.argv
    if 2 == len(args):
        data, extension = getfile(args[1])
        long = len(data)
        
        thread1 = threading.Thread(target = send_qr)
        thread2 = threading.Thread(target = show_qr)

        thread1.start()
        thread2.start()