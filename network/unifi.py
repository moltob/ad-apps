"""Helpers to interact with Ubiquity Unifi controllers."""
import appdaemon.entity

from util.base import MyHomeAssistantApp


class FirewallAddressGroupUpdaterApp(MyHomeAssistantApp):
    """Update the IP address contained in a firewall address group.

    The intention of this update is to fix an outdated ingress firewall rule if the IPv6 address of
    homeassistant changed after a prefix change by the ISP. The class is watching the global IPv6
    address of HA and runs the update on change.
    """

    ent_ipv6_address: appdaemon.entity.Entity

    async def initialize(self):
        await super().initialize()

        unifi = self.args["unifi"]
        self.unifi_url = unifi["url"]
        self.unifi_auth = unifi["username"], unifi["password"]
        self.address_group_id = unifi["address_group_id"]
        self.notify_service = self.args["notify"].get("service")

        self.logger.info("Watching IPv6 address sensor %r.", self.ent_ipv6_address.entity_id)
        await self.ent_ipv6_address.listen_state(self.update_address_group)

    async def update_address_group(self, entity, attribute, old, new, *args, **kwargs):
        self.logger.info(
            "Updating address group %r after IPv6 address has switched from %r to %r.",
            self.address_group_id,
            old,
            new,
        )

        # TODO: update firewall address group
