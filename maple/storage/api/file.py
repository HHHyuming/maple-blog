#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ********************************************************************************
# Copyright © 2019 jianglin
# File Name: file.py
# Author: jianglin
# Email: mail@honmaple.com
# Created: 2019-05-13 16:36:36 (CST)
# Last Update: Wednesday 2019-07-10 00:02:01 (CST)
#          By:
# Description:
# ********************************************************************************
import json
import os

from flask import request
from flask_babel import gettext as _
from flask_maple.response import HTTP
from flask_maple.views import IsAuthMethodView
from maple.utils import filter_maybe, is_true, update_maybe, check_params

from maple.storage.db import File, FilePath
from maple.storage.serializer import FilePathSerializer, FileSerializer
from maple.storage.util import file_is_allowed, gen_hash, secure_filename, gen_size


class FileListView(IsAuthMethodView):
    def get(self, bucket):
        data = request.data
        user = request.user
        page, number = self.pageinfo

        bucket = user.buckets.filter_by(
            name=bucket).get_or_404("bucket not found")

        params = filter_maybe(data, {
            "name": "name__contains",
            "type": "file_type"
        })
        filepath = bucket.get_root_path(data.get("path", "/"))
        if not filepath:
            return HTTP.BAD_REQUEST(message="path not found")

        paths = filepath.child_paths.paginate(page, number)
        files = filepath.files.filter_by(**params).paginate(page, number)
        path_serializer = FilePathSerializer(paths)
        file_serializer = FileSerializer(files)
        return HTTP.OK(
            data=dict(
                paths=path_serializer.data,
                files=file_serializer.data,
            ))

    def post(self, bucket):
        data = request.data
        user = request.user
        bucket = user.buckets.filter_by(
            name=bucket).get_or_404("bucket not found")

        filepath = bucket.get_root_path(data.get("path", "/"), True)
        files = request.files.getlist('files')
        if files:
            return self.post_with_multi(filepath, files)
        return self.post_with_one(filepath)

    def post_with_one(self, filepath, f=None):
        if not f:
            f = request.files.get("file")
        if not f:
            return HTTP.BAD_REQUEST(message="file is null")

        force = is_true(request.data.get("force"))

        filename = secure_filename(f.filename)
        if not file_is_allowed(filename):
            msg = _("%(name)s unsupported extension", name=filename)
            return HTTP.BAD_REQUEST(message=msg)

        file_type = f.content_type
        hash = gen_hash(f)
        size = gen_size(f)
        ins = filepath.files.filter_by(name=filename, hash=hash).first()
        if ins and not force:
            msg = _(
                "%(name)s file is exists, use force to override file",
                name=filename)
            return HTTP.BAD_REQUEST(message=msg)
        if not ins:
            ins = File(
                name=filename,
                hash=hash,
                size=size,
                path_id=filepath.id,
                file_type=file_type,
            )
            ins.save()
        # 保存到磁盘中
        # http://stackoverflow.com/questions/42569942/calculate-md5-from-werkzeug-datastructures-filestorage-but-saving-the-object-as
        dirname = os.path.dirname(ins.abspath)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        f.seek(0)
        f.save(ins.abspath)
        rep = FileSerializer(ins).data
        return HTTP.OK(data=rep)

    def post_with_multi(self, filepath, files):
        fail = []
        success = []
        for f in files:
            resp = self.post_with_one(filepath, f)
            if resp.status_code != 200:
                fail.append(json.loads(resp.data)["message"])
            else:
                success.append(json.loads(resp.data)["data"])
        return HTTP.OK(data={
            "success": success,
            "fail": fail,
        })

    @check_params(["file"])
    def put(self, bucket):
        data = request.data
        user = request.user
        bucket = user.buckets.filter_by(
            name=bucket).get_or_404("bucket not found")

        ins = File.query.filter_by(
            id=data["file"],
            path__bucket_id=bucket.id).get_or_404("file not found")

        action = data.get("action", "rename")
        if action not in ["rename", "move", "copy"]:
            return HTTP.BAD_REQUEST()

        if action == "rename":
            newname = data.get("newname")
            if not newname or newname == ins.name:
                return HTTP.OK(message="file not change")
            serializer = FileSerializer(ins.rename(newname))
            return HTTP.OK(data=serializer.data)

        newpath = data.get("newpath")
        if not newpath:
            return HTTP.BAD_REQUEST(message="newpath is required")

        newfilepath = bucket.get_root_path(newpath)
        if not newfilepath:
            msg = "{0} path not found"
            return HTTP.BAD_REQUEST(message=msg)

        if action == "move":
            nfile = ins.move(newpath)
        else:
            nfile = ins.copy(newpath)

        serializer = FileSerializer(nfile)
        return HTTP.OK(data=serializer.data)

    @check_params(["file"])
    def delete(self, bucket):
        data = request.data
        user = request.user
        bucket = user.buckets.filter_by(
            name=bucket).get_or_404("bucket not found")

        ins = File.query.filter_by(
            id=data["file"],
            path__bucket_id=bucket.id).get_or_404("file not found")
        ins.delete()
        return HTTP.OK()
