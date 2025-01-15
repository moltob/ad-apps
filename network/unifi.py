"""Helpers to interact with Ubiquity Unifi controllers."""
import base64
import json

import aiohttp
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

        unifi = self.args['unifi']
        self.unifi_url = unifi['url']
        self.unifi_username = unifi['username']
        self.unifi_password = unifi['password']
        self.address_group_id = unifi['address_group_id']
        self.notify_service = self.args['notify'].get('service')

        self.logger.info('Watching IPv6 address sensor %r.', self.ent_ipv6_address.entity_id)
        await self.ent_ipv6_address.listen_state(self.update_address_group)

    async def update_address_group(self, entity, attribute, old, new, *args, **kwargs):
        self.logger.info(
            'Updating address group %r after IPv6 address has switched from %r to %r.',
            self.address_group_id,
            old,
            new,
        )

        async with aiohttp.ClientSession(self.unifi_url) as session:
            # log into unifi controller:
            response = await session.post(
                '/api/auth/login',
                json={'username': self.unifi_username, 'password': self.unifi_password},
                verify_ssl=False,
            )
            response.raise_for_status()
            self.logger.debug('Successfully logged into Unifi controller.')

            # extract csrf token from cookie:
            csrf_token = None
            for _, cookie in session.cookie_jar.filter_cookies(self.unifi_url).items():
                if cookie.key == 'TOKEN':
                    _, jwt_payload_b64, _ = cookie.value.split('.')
                    # add padding possibly needed (or ignored), as JWT does not contain any:
                    jwt_payload_dict = json.loads(base64.b64decode(f'{jwt_payload_b64}===='))
                    csrf_token = jwt_payload_dict['csrfToken']
                    break

            if not csrf_token:
                self.logger.error('CSRF token not found in response cookie.')
                return

            response = await session.put(
                f'/proxy/network/api/s/default/rest/firewallgroup/{self.address_group_id}',
                json={
                    '_id': self.address_group_id,
                    'name': 'Homeassistant',
                    'group_type': 'ipv6-address-group',
                    'group_members': [new],
                },
                headers={'x-csrf-token': csrf_token},
                verify_ssl=False,
            )
            response.raise_for_status()
            self.logger.debug('Successfully updated address group.')

            await self.call_service(
                f'notify/{self.notify_service}',
                title='Firewall Configuration Success',
                message=f'HA address group adapted to new IPv6 address {new!r}.',
            )
