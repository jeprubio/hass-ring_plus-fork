import asyncio
import json

from aioring.alarm import RingAlarmConnection


class FakeWs:
    closed = False

    def __init__(self):
        self.sent = []

    async def send_str(self, s):
        self.sent.append(json.loads(s))


def _run(coro_fn):
    conn = RingAlarmConnection(None, None, "loc")
    conn.asset_id = "asset"
    conn._ws = FakeWs()
    asyncio.run(coro_fn(conn))
    return conn._ws.sent[-1]["msg"]


def test_sound_siren_payload():
    msg = _run(lambda c: c.sound_siren("panel"))
    assert msg["msg"] == "DeviceInfoSet" and msg["dst"] == "asset"
    assert msg["body"] == [{"zid": "panel", "command": {"v1": [
        {"commandType": "security-panel.sound-siren", "data": {}}]}}]


def test_silence_siren_payload():
    msg = _run(lambda c: c.silence_siren("panel"))
    assert msg["body"][0]["command"]["v1"][0] == {
        "commandType": "security-panel.silence-siren", "data": {}}


def test_set_mode_payload_unchanged():
    msg = _run(lambda c: c.set_mode("panel", "all"))
    assert msg["body"][0]["command"]["v1"][0] == {
        "commandType": "security-panel.switch-mode", "data": {"mode": "all", "bypass": []}}


NOT_READY_MSG = {
    "msg": "DataUpdate", "datatype": "DeviceInfoDocType",
    "body": [{
        "general": {"v2": {"deviceType": "security-panel", "zid": "panel"}},
        "device": {"v1": {"mode": "none"}},
        "impulse": {"v1": [{"impulseType": "security-panel.not-ready", "data": {
            "devices": [{"name": "Porta Cuina", "reasons": ["fault"], "zid": "door"}],
            "initiatingZid": "keypad", "mode": "all"}}]},
    }],
}


def test_impulses_are_dispatched_after_state_update():
    conn = RingAlarmConnection(None, None, "loc")
    seen = []
    conn.add_impulse_listener(lambda zid, kind, data: seen.append((zid, kind, data["mode"],
                                                                   conn.devices[zid]["mode"])))
    assert conn._handle("DataUpdate", NOT_READY_MSG) is False
    assert seen == [("panel", "security-panel.not-ready", "all", "none")]


def test_impulses_ignored_in_initial_device_list():
    conn = RingAlarmConnection(None, None, "loc")
    seen = []
    conn.add_impulse_listener(lambda *a: seen.append(a))
    conn._handle("message", {**NOT_READY_MSG, "msg": "DeviceInfoDocGetList"})
    assert seen == [] and conn.devices["panel"]["mode"] == "none"
