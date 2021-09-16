from lxml import etree
import time

def getGPSw(el):
    data = {"GPSDateTime": "", "GPSData":[]}
    if el == None:
        return None
    else:
        data["GPSDateTime"] = el.text
    for i in range(0, 500):
        el = el.getnext()
        if el == None:
            break
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSDateTime":
            break
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSLatitude":
            data["GPSData"].append({"GPSLatitude": el.text})
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSLongitude":
            data["GPSData"].append({"GPSLongitude": el.text})
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSAltitude":
            data["GPSData"].append({"GPSAltitude": el.text})
    return data

data = []
tree = etree.parse('VIDEO_META.xml')
root = tree.getroot()
print(etree.tostring(root))
time.sleep(3)
print(root)
time.sleep(3)
for el in root[0]:
    print(el)
    if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSDateTime":
        data = getGPSw(el)
        if data is not None:
            print(data)
            exit()

