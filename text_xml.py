from lxml import etree

def getGPSw(el):
    data = []
    if el == None:
        return None
    else:
        data.append({"GPSDateTime": el.text})
    for i in range(0, 500):
        el = el.getnext()
        if el == None:
            break
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSDateTime":
            break
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSLatitude":
            data.append({"GPSLatitude": el.text})
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSLongitude":
            data.append({"GPSLongitude": el.text})
        if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSAltitude":
            data.append({"GPSAltitude": el.text})
    return data


tree = etree.parse('VIDEO_META.xml')
root = tree.getroot()
for el in root[0]:
    print(el)
    if el.tag == "{http://ns.exiftool.org/QuickTime/Track3/1.0/}GPSDateTime":
        data = getGPSw(el)
        print(len(data))

print(data)


