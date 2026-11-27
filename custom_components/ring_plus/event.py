"""Ring Alarm events: arming blocked because sensors need a bypass."""
from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import callback

from .entity import RingAlarmEntity

NOT_READY = "security-panel.not-ready"
MODE_NAME = {"some": "home", "all": "away"}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        RingArmingBlockedEvent(conn, dev["zid"]) for conn, dev in entry.runtime_data.alarm_devices()
        if dev.get("deviceType") == "security-panel")


class RingArmingBlockedEvent(RingAlarmEntity, EventEntity):
    """Fires when the Ring keypad or app asks to bypass open sensors before arming."""

    _attr_name = "Arming blocked"
    _attr_event_types = ["not_ready"]

    def __init__(self, conn, zid: str) -> None:
        super().__init__(conn, zid, "arming_blocked")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._conn.add_impulse_listener(self._on_impulse))

    @callback
    def _on_impulse(self, zid: str, impulse_type: str, data: dict[str, Any]) -> None:
        if zid != self._zid or impulse_type != NOT_READY:
            return
        devices = [d for d in data.get("devices") or [] if isinstance(d, dict)]
        mode = data.get("mode")
        self._trigger_event("not_ready", {
            "mode": MODE_NAME.get(mode, mode),
            "sensors": [d.get("name") or d.get("zid") for d in devices],
            "reasons": {d.get("name") or d.get("zid"): d.get("reasons") or [] for d in devices},
        })
        self.async_write_ha_state()
