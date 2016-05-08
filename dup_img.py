#!/usr/bin/env python

from PIL import Image
import imagehash
from mimetypes import MimeTypes
import os
import sys
import filecmp
import pickle
import signal
import time

if len(sys.argv) != 2:
    print('usage: ' + sys.argv[0] + ' <root_dir> | tee result.csv')
    exit(1)

def searchImages(rootDir):
    imageList = []
    mime = MimeTypes()
    for root, subFolders, files in os.walk(rootDir):
        for file in files:
            mt = mime.guess_type(file)[0]
            if mt and mt.startswith('image/'):
                imageList = imageList + [os.path.join(root,file)]
    return imageList

#def computeHash(file):

hashedImg = {}

def main():
    global hashedImg
    # search all images on disk
    print('Scanning %s for images...' % sys.argv[1]) # TODO: readargs
    imageList = searchImages(sys.argv[1])
    total = len(imageList)
    print('Found %d image files in %s\n' % (total, sys.argv[1]))

    count = 0

    # load previously computed hashed files
    dbFileName = 'pics.db'
    hashedImg = {}
    # hashedImg['/pat/to/file.jpg'] = (hash, timestamp)
    if os.path.isfile(dbFileName):
        hashedImg = pickle.load(open(dbFileName, 'rb'))
        count = count + len(hashedImg)
        print('Succesfuly loaded %d hashed images from database' % len(hashedImg))


    # compute hash for new files or modified pictures since last scan
    percent = 0
    startTime = time.time()
    for file in imageList:
        fileTs = os.path.getmtime(file)
        if file not in hashedImg or hashedImg[file][1] < fileTs:
            # compute hash
            try:
                image = Image.open(file)
                hashedImg[file] = (imagehash.dhash(image), fileTs)
            except SystemExit:
                break
            except:
                e = sys.exc_info()[0]
                print('Error in %s: %s' % (file, e))
            count = count + 1
            percent = (count * 100) / total
            elapsedTime = time.time() - startTime
            deltaT = (100 * (elapsedTime) / percent) - elapsedTime
            sys.stdout.write("Process images... %d%% #%d - %s\r" % (percent, count, file))
            sys.stdout.flush()
    saveDb()
    print('Images process finished and saved to database. Continuing with compare...')

    # remove deleted files
    if len(hashedImg) < len(imageList):
        print('some file could not be processed?')
#        raise Exception('Internal error.')
    if len(hashedImg) > len(imageList):
        print('TODO: Remove deleted files from database...')
#        for key in hashedImg:
#            if key not in imageList:
#                del hashedImg[key]
        hashedImg = {x:hashedImg[x] for x in hashedImg if x in imageList}
        print('done')

    saveDb()

    # compare
    unikH = {} # key = hash, value = file name
    with open("ident.csv", "wt") as fident, open("percept.csv", "wt") as fpercept, open("differential.csv", "wt") as fdiff:
        for file in hashedImg:
            imgHash = hashedImg[file][0]
            if imgHash not in unikH:
                unikH[imgHash] = file
                continue
            # found one
            if filecmp.cmp(file, unikH[imgHash]):
                # identity
                fident.write(file + "," + unikH[imgHash] + "\n")
            else:
                h1 = imagehash.phash(Image.open(file)) # perceptual hash
                h2 = imagehash.phash(Image.open(unikH[imgHash])) # perceptual hash
                if h1 == h2:
                    # perceptual
                    fpercept.write(file + "," + unikH[imgHash] + "\n")
                else:
                    # difference hash
                    fdiff.write(file + "," + unikH[imgHash] + "\n")


def saveDb():
    pickle.dump(hashedImg, open('pics.db', 'wb'))

def ctrlc(signal, frame):
    print('\nExit requested...')
    saveDb()
    sys.exit(0)
signal.signal(signal.SIGINT, ctrlc)

main()
saveDb()
