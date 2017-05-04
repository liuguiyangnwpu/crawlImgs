#!/usr/bin/env python
# coding=utf-8

import os
import codecs
import hashlib
import shutil
from scrapy.utils.python import to_bytes
from pymongo import MongoClient
import pymongo
import datetime
import cv2

settings = {
    "MONGODB_SERVER":"10.18.103.154",
    "MONGODB_PORT":27017,
    "MONGODB_DB":"spiderdb",
    "MONGODB_COLLECTION":"imagetable"
}

class DataManager():
    def __init__(self):
        mc = MongoClient(settings["MONGODB_SERVER"], settings["MONGODB_PORT"])
        spiderdb = mc[settings["MONGODB_DB"]]
        self._collection = spiderdb[settings["MONGODB_COLLECTION"]]
        self._saveImgList = []
    
    def __del__(self):
        if len(self._saveImgList) > 0:
            self.flush2MongoDB()

    def insertSpiderItem(self, item, isBatch = False):
        '''
        如果参数选择的是isBatch, 
        那么需要调用 flush2MongoDB() 将数据直接写入到DB中
        '''
        imageItem = [{
            "imageurls":item["image_urls"][0],
            "imagepath":item["image_paths"],
            "imagelabel":item["image_label"],
            "imagefromurl":item["image_fromURL"],
            "imagefromurlhost":item["image_fromURLHost"],
            "imageheight":item["image_height"],
            "imagewidth":item["image_width"],
            "imagecrawdatetime":item["image_crawDateTime"]
        }]
        if isBatch == False:
            self._collection.insert_many(imageItem)
        else:
            self._saveImgList.extend(imageItem)
    
    def flush2MongoDB(self):
        if len(self._saveImgList) > 0:
            self._collection.insert_many(self._saveImgList)
            self._saveImgList = []

    def getCachedItemSize(self):
        return len(self._saveImgList)

    def updateByDistinct(self):
        itemlist = list(self._collection.distinct("imagepath"))
        for item in itemlist:
            tmplist = list(self._collection.find({"imagepath":item}).sort([
                                ("imagecrawdatetime", pymongo.ASCENDING)
                            ]))
            if len(tmplist) > 1:
                for i in range(1, len(tmplist)):
                    self._collection.delete_many(tmplist[i])

def updateRemoveDistinct():
    dataObj = DataManager()
    dataObj.updateByDistinct()

def loadData2DBfromThird():
    filepath = "/root/SPIDERIMAGESDB/DATASOURCE/第三方数据/total.csv"
    if not os.path.exists(filepath):
        raise IOError(filepath + " not exists !")

    def insertSpiderItem(item):
        '''
        如果参数选择的是isBatch,
        那么需要调用 flush2MongoDB() 将数据直接写入到DB中
        '''
        imageItem = [{
            "imageurls":item["image_urls"],
            "imagepath":item["image_paths"],
            "imagelabel":"",
            "imagefromurl":item["image_fromURL"],
            "imagefromurlhost":item["image_fromURL"],
            "imageheight":item["image_height"],
            "imagewidth":item["image_width"],
            "imagecrawdatetime":datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        }]
        return imageItem

    srcprefix = "/root/SPIDERIMAGESDB/DATASOURCE/第三方数据/tmp/"
    destprefix = "/root/SPIDERIMAGESDB/DATASOURCE/第三方数据/体育运动/"
    mc = MongoClient(settings["MONGODB_SERVER"], settings["MONGODB_PORT"])
    spiderdb = mc[settings["MONGODB_DB"]]
    dbtable = spiderdb[settings["MONGODB_COLLECTION"]]
    with codecs.open(filepath, 'r', 'utf-8') as handle:
        for line in handle.readlines():
            line = line.strip().split(',')
            name, imgurl, pageurl = line[0], line[1], line[2]
            if not os.path.exists(srcprefix + name):
                continue
            # 更改图像的原始名字
            image_guid = hashlib.sha1(to_bytes(imgurl)).hexdigest()
            image_guid += "."
            image_guid += name.split(".")[-1]
            try:
                shutil.copyfile(srcprefix+name, destprefix+image_guid)
                img = cv2.imread(srcprefix+name)
                height, width = img.shape[:2]
                item = {
                    "image_urls": imgurl,
                    "image_paths": "第三方数据/体育运动/" + image_guid,
                    "image_fromURL": pageurl,
                    "image_height": height,
                    "image_width": width
                }
                imageItem = insertSpiderItem(item=item)
                dbtable.insert_many(imageItem)
            except Exception as es:
                print(srcprefix+name, es)

def mergeOldData2DB():
    filepath = ""
    if not os.path.exists(filepath):
        raise IOError(filepath + " not exists !")

    def insertSpiderItem(item):
        '''
        如果参数选择的是isBatch,
        那么需要调用 flush2MongoDB() 将数据直接写入到DB中
        '''
        imageItem = [{
            "imageurls":item["image_urls"],
            "imagepath":item["image_paths"],
            "imagelabel":"",
            "imagefromurl":item["image_fromURL"],
            "imagefromurlhost":item["image_fromURL"],
            "imageheight":item["image_height"],
            "imagewidth":item["image_width"],
            "imagecrawdatetime": "Fri, 31 Mar 2017 15:01:28 GMT"
        }]
        return imageItem

    srcprefix = "/root/SPIDERIMAGESDB/DATASOURCE/"
    mc = MongoClient(settings["MONGODB_SERVER"], settings["MONGODB_PORT"])
    spiderdb = mc[settings["MONGODB_DB"]]
    dbtable = spiderdb[settings["MONGODB_COLLECTION"]]
    with codecs.open(filepath, 'r', 'utf-8') as handle:
        for line in handle.readlines():
            _, partpath, imgurl = line.strip().split(",")
            if not os.path.exists(srcprefix+partpath):
                continue
            try:
                img = cv2.imread(srcprefix+partpath)
                height, width = img.shape[:2]
                item = {
                    "image_urls": imgurl,
                    "image_paths": partpath,
                    "image_fromURL": imgurl,
                    "image_height": height,
                    "image_width": width
                }
                imageItem = insertSpiderItem(item=item)
                dbtable.insert_many(imageItem)
            except Exception as es:
                print(es)

def addImageMD5():
    # mc = MongoClient(settings["MONGODB_SERVER"], settings["MONGODB_PORT"])
    # spiderdb = mc[settings["MONGODB_DB"]]
    # dbtable = spiderdb[settings["MONGODB_COLLECTION"]]
    def _imgdiff(srcimg, w, h):
        diff = []
        for i in range(h):
            for j in range(w-1):
                c = srcimg[i,j]
                rc = srcimg[i,j+1]
                if c > rc:
                    diff.append('1')
                else:
                    diff.append('0')
            diff.append('0')
        imgKey = ''.join(diff)
        print(imgKey)

    file1 = "/Users/liuguiyang/Desktop/test.jpg"
    img1 = cv2.imread(file1)
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    width, height = 8, 9
    gray1 = cv2.resize(gray1, (width, height), interpolation=cv2.INTER_CUBIC)
    print(gray1.dtype)
    _imgdiff(gray1, width, height)

if __name__ == '__main__':
    addImageMD5()