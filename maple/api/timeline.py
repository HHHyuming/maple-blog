#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ********************************************************************************
# Copyright © 2018 jianglin
# File Name: timeline.py
# Author: jianglin
# Email: mail@honmaple.com
# Created: 2018-03-11 20:51:54 (CST)
# Last Update: Tuesday 2018-11-06 13:52:22 (CST)
#          By:
# Description:
# ********************************************************************************
from flask_maple.views import MethodView
from flask_maple.serializer import Serializer

from maple.model import TimeLine
from maple.response import HTTP


class TimeLineAPI(MethodView):
    def get(self):
        page, number = self.pageinfo
        filter_dict = {'is_hidden': False}
        order_by = ('-created_at', )
        timelines = TimeLine.query.filter_by(
            **filter_dict).order_by(*order_by).paginate(page, number)
        serializer = Serializer(
            timelines,
            exclude=['user', 'user_id', 'is_hidden'],
            extra=['datetime_format'])
        return HTTP.OK(data=serializer.data)
