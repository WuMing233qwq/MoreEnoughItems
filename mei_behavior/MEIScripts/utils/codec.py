# coding=utf-8
# ----------------------------------------------------------------------
#  codec.py is part of MoreEnoughItems.
#  Copyright (C) 2026 WuMing233qwq <2691068930@qq.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation, version 3 only.
#
#  This program is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this program.
#  If not, see <https://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------

import json

from .stablehash import stable_text

try:
    basestring
except NameError:  # pragma: no cover
    basestring = (str, bytes)


class Codec(object):
    """ 递归对象字符串编解码器，支持可扩展类型注册。 """

    TYPE_KEY = "__mei_type__"
    PAYLOAD_KEY = "__mei_payload__"

    _ENCODERS = {}
    _DECODERS = {}

    @classmethod
    def register_type(cls, type_tag, type_cls, encoder, decoder):
        if not isinstance(type_tag, basestring) or not type_tag:
            raise ValueError("type_tag must be non-empty string")
        if type_cls is None:
            raise ValueError("type_cls cannot be None")
        if not callable(encoder) or not callable(decoder):
            raise ValueError("encoder and decoder must be callable")

        cls._ENCODERS[type_tag] = (type_cls, encoder)
        cls._DECODERS[type_tag] = decoder

    @classmethod
    def dumps(cls, obj):
        payload = cls._to_data(obj, set())
        return stable_text(payload)

    @classmethod
    def loads(cls, text):
        if not isinstance(text, basestring):
            raise ValueError("text must be string")
        payload = json.loads(text)
        return cls._from_data(payload)

    @classmethod
    def _to_data(cls, obj, stack):
        if isinstance(obj, (type(None), bool, int, float, basestring)):
            return obj

        for type_tag, (type_cls, encoder) in cls._ENCODERS.items():
            if isinstance(obj, type_cls):
                obj_id = id(obj)
                if obj_id in stack:
                    raise ValueError("Circular reference detected while encoding custom type")
                stack.add(obj_id)
                try:
                    raw_payload = encoder(obj)
                    return {
                        cls.TYPE_KEY: type_tag,
                        cls.PAYLOAD_KEY: cls._to_data(raw_payload, stack),
                    }
                finally:
                    stack.remove(obj_id)

        if isinstance(obj, list):
            obj_id = id(obj)
            if obj_id in stack:
                raise ValueError("Circular reference detected while encoding list")
            stack.add(obj_id)
            try:
                return [cls._to_data(item, stack) for item in obj]
            finally:
                stack.remove(obj_id)

        if isinstance(obj, tuple):
            obj_id = id(obj)
            if obj_id in stack:
                raise ValueError("Circular reference detected while encoding tuple")
            stack.add(obj_id)
            try:
                return {
                    cls.TYPE_KEY: "tuple",
                    cls.PAYLOAD_KEY: [cls._to_data(item, stack) for item in obj],
                }
            finally:
                stack.remove(obj_id)

        if isinstance(obj, set):
            obj_id = id(obj)
            if obj_id in stack:
                raise ValueError("Circular reference detected while encoding set")
            stack.add(obj_id)
            try:
                return {
                    cls.TYPE_KEY: "set",
                    cls.PAYLOAD_KEY: [cls._to_data(item, stack) for item in obj],
                }
            finally:
                stack.remove(obj_id)

        if isinstance(obj, dict):
            obj_id = id(obj)
            if obj_id in stack:
                raise ValueError("Circular reference detected while encoding dict")
            stack.add(obj_id)
            try:
                if all(isinstance(key, basestring) for key in obj):
                    result = {}
                    for key, value in obj.items():
                        result[key] = cls._to_data(value, stack)
                    return result

                items = []
                for key, value in obj.items():
                    items.append([cls._to_data(key, stack), cls._to_data(value, stack)])
                return {
                    cls.TYPE_KEY: "dict_items",
                    cls.PAYLOAD_KEY: items,
                }
            finally:
                stack.remove(obj_id)

        raise ValueError("Unsupported type for dumps: {}".format(type(obj).__name__))

    @classmethod
    def _from_data(cls, data):
        if isinstance(data, list):
            return [cls._from_data(item) for item in data]

        if isinstance(data, dict):
            type_tag = data.get(cls.TYPE_KEY)
            if type_tag is None:
                result = {}
                for key, value in data.items():
                    result[key] = cls._from_data(value)
                return result

            payload = cls._from_data(data.get(cls.PAYLOAD_KEY))

            if type_tag == "tuple":
                return tuple(payload)
            if type_tag == "set":
                return set(payload)
            if type_tag == "dict_items":
                return {key: value for key, value in payload}

            decoder = cls._DECODERS.get(type_tag)
            if decoder is None:
                raise ValueError("Unknown type tag: {}".format(type_tag))
            return decoder(payload)

        return data
