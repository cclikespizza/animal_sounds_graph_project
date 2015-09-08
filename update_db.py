# -*- coding=utf-8 -*-

__author__ = 'elmira'

import sqlite3 as sqlite
import codecs


class DataBase(object):

    def __init__(self, db_file):
        self._connection = sqlite.connect(db_file)
        self._cursor = self._connection.cursor()
        self.__data = ''

    def insert(self, table, *args):
        query = self.__make_query(table, args)
        self._cursor.execute(query)
        self._connection.commit()

    def __make_query(self, table, args):
        try:
            q = u"INSERT into " + table + u" VALUES(" + u", ".join(unicode(i) for i in args) + u');'
            return q
        except:
            print table
            for i in args: print i


def loaddata(fname):
    arr = []
    f = codecs.open(fname, 'r', 'utf-8')
    data = f.readlines()
    f.close()
    for line in data:
        line = line.split('\t')
        line[-1] = line[-1].strip()
        arr.append(line)
    return arr

