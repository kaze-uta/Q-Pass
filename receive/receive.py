import cv2 as cv
import copy
import re
import time
import os
from pyzbar.pyzbar import decode
import numpy as np
import base64

def read_qr():
    cap = cv.VideoCapture(1)
    check = ""
    i = 0
    j = 0
    k = 0

    while True:
        ret,frame = cap.read()
        for barcode in decode(frame):
            print(barcode)
            pts =np.array([barcode.polygon],np.int32)
            cv.polylines(frame,[pts],True,(255,0,0),5)  

            if barcode.data[0] != "" and i == 0:
                extension = barcode.data.decode() 
                i += 1         
            
            if barcode.data[0] != "" and check != barcode.data:

                if barcode.data == base64.b64encode(b"last"):
                    blast = "last".encode()
                    base64.b64encode(blast)
                    j += 1
                    break
                    
                elif barcode.data != extension:
                    if k == 0:
                        extension += '=' * (-len(extension) % 4)
                        extension = base64.b64decode(extension)
                        extension = extension.decode()
                        k += 1
                    with open(f"get.{extension}", "ab") as f:
                        if i == 1:
                            pass
                            i += 1
                        else:
                            f.write(base64.b64decode(barcode.data))
            check = copy.copy(barcode.data)
        if (j >= 1):
            break
            
        
        cv.imshow('test',frame)
        if cv.waitKey(1) & 0xFF == ord('q'):
            break

read_qr()