"""Small explicitly constructed executable models for application tests."""

import json


def meter_model(name="meter", start=0, count=1):
    return {
        "@context": [
            "https://www.w3.org/2022/wot/td/v1.1",
            {
                "modpoll": "https://top-maker.github.io/modpoll/vocab/wot-modbus#",
                "modv": "https://www.w3.org/2019/wot/modbus",
            },
        ],
        "@type": "tm:ThingModel",
        "title": name,
        "modpoll:version": "0.1",
        "properties": {"value": {"type": "integer", "readOnly": True}},
        "modpoll:acquisition": [
            {
                "modv:entity": "HoldingRegister",
                "modv:address": start,
                "modv:quantity": count,
                "modv:mostSignificantByte": True,
                "modv:mostSignificantWord": True,
                "modpoll:members": [
                    {
                        "modpoll:property": "value",
                        "modpoll:offset": 0,
                        "modpoll:dataType": "uint16",
                    }
                ],
            }
        ],
    }


def write_meter(path, name="meter", start=0, count=1):
    path.write_text(json.dumps(meter_model(name, start, count)))
    return path
