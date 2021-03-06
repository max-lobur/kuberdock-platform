
# KuberDock - is a platform that allows users to run applications using Docker
# container images and create SaaS / PaaS based on these applications.
# Copyright (C) 2017 Cloud Linux INC
#
# This file is part of KuberDock.
#
# KuberDock is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# KuberDock is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with KuberDock; if not, see <http://www.gnu.org/licenses/>.

from config import ConfigManager, TokenManager
from ..api_client import KDClient, RequestsLogger


class LoginRequired(Exception):
    message = 'Login required.'


class KDCtl(object):
    default_config = {
        'url': 'https://127.0.0.1'
    }

    @classmethod
    def create(cls, config_dir, debug):
        cm = ConfigManager(config_dir, cls.default_config)
        tm = TokenManager(config_dir)
        return cls(cm, tm, debug)

    def __init__(self, config_manager, token_manager, debug):
        self.cm = config_manager
        self.tm = token_manager
        self._config = None
        self._client = None
        self._token = None
        self.debug = debug

        if debug:
            RequestsLogger.turn_on_logging()

    @property
    def config(self):
        """:rtype: dict"""
        if self._config is None:
            self._config = self.cm.get_config()
        return self._config

    @property
    def client(self):
        """:rtype: KDClient"""
        if not self._client:
            self._client = KDClient(self.config['url'], token=self.token)
        return self._client

    @property
    def token(self):
        if not self._token:
            try:
                self._token = self.tm.get_token()
            except self.tm.TokenNotFound:
                raise LoginRequired
        return self._token

    @token.setter
    def token(self, value):
        self.tm.save_token(value)
        self._token = value
        self._client.token = value

    def login(self, username, password):
        conf = self.config
        client = KDClient(conf['url'], username, password)
        token = client.auth.token()['token']
        self.tm.save_token(token)
        self._token = token

    def update_config(self, **kwargs):
        self.config.update(**kwargs)
        self.cm.save_config(self.config)
        return self.config

    def __getattr__(self, item):
        """Redirect to kdclient if method is not defined here"""
        return getattr(self.client, item)
