import unittest

from configparser import ConfigParser
from unittest import mock

from app.utils import get_auth_users, get_auth_ips


class GetAuthUsersTestCase(unittest.TestCase):
    """
    Test utils.get_auth_users
    """

    def setUp(self):
        self.config = ConfigParser()

    def test_valid_single_user_single_group(self):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstpass"
            }
        })
        self.assertEqual(
            get_auth_users(self.config),
            {
                "userfirstname_userfirstpass": {
                    "username": "userfirstname",
                    "password": "userfirstpass",
                    "groups": ["groupfirst"],
                }
            }
        )

    def test_valid_multi_user_single_group(self):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstpass",
                "usersecondname": "usersecondpass",
            }
        })
        self.assertEqual(
            get_auth_users(self.config),
            {
                "userfirstname_userfirstpass": {
                    "username": "userfirstname",
                    "password": "userfirstpass",
                    "groups": ["groupfirst"],
                },
                "usersecondname_usersecondpass": {
                    "username": "usersecondname",
                    "password": "usersecondpass",
                    "groups": ["groupfirst"],
                }
            }
        )

    def test_valid_single_user_multi_group(self):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstpass",
            },
            "groupsecond": {
                "userfirstname": "userfirstpass",
            }
        })
        self.assertEqual(
            get_auth_users(self.config),
            {
                "userfirstname_userfirstpass": {
                    "username": "userfirstname",
                    "password": "userfirstpass",
                    "groups": ["groupfirst", "groupsecond"],
                }
            }
        )

    def test_valid_multi_user_multi_group(self):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstpass",
                "usersecondname": "usersecondpass",
            },
            "groupsecond": {
                "userfirstname": "userfirstpass",
                "usersecondname": "usersecondpass",
            }
        })
        self.assertEqual(
            get_auth_users(self.config),
            {
                "userfirstname_userfirstpass": {
                    "username": "userfirstname",
                    "password": "userfirstpass",
                    "groups": ["groupfirst", "groupsecond"],
                },
                "usersecondname_usersecondpass": {
                    "username": "usersecondname",
                    "password": "usersecondpass",
                    "groups": ["groupfirst", "groupsecond"],
                }
            }
        )


@mock.patch("app.utils.ip_network")
class GetAuthIpsTestCase(unittest.TestCase):
    """
    Test utils.get_auth_ips
    """

    def setUp(self):
        self.config = ConfigParser()

    def test_valid_single_user_single_group_single_ip(self, ip_network_mock):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstip"
            }
        })
        self.assertEqual(
            get_auth_ips(self.config),
            {
                "userfirstname_userfirstip": {
                    "username": "userfirstname",
                    "network": "userfirstip",
                    "groups": ["groupfirst"],
                }
            }
        )
        ip_network_mock.assert_has_calls([
            mock.call("userfirstip"),
        ], any_order=True)

    def test_valid_single_user_single_group_multi_ip(self, ip_network_mock):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstip,userfirstnetwork"
            }
        })
        self.assertEqual(
            get_auth_ips(self.config),
            {
                "userfirstname_userfirstip": {
                    "username": "userfirstname",
                    "network": "userfirstip",
                    "groups": ["groupfirst"],
                },
                "userfirstname_userfirstnetwork": {
                    "username": "userfirstname",
                    "network": "userfirstnetwork",
                    "groups": ["groupfirst"],
                }
            }
        )
        ip_network_mock.assert_has_calls([
            mock.call("userfirstip"),
            mock.call("userfirstnetwork"),
        ], any_order=True)

    def test_valid_multi_user_single_group_single_ip(self, ip_network_mock):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstip",
                "usersecondname": "usersecondip",
            }
        })
        self.assertEqual(
            get_auth_ips(self.config),
            {
                "userfirstname_userfirstip": {
                    "username": "userfirstname",
                    "network": "userfirstip",
                    "groups": ["groupfirst"],
                },
                "usersecondname_usersecondip": {
                    "username": "usersecondname",
                    "network": "usersecondip",
                    "groups": ["groupfirst"],
                }
            }
        )
        ip_network_mock.assert_has_calls([
            mock.call("userfirstip"),
            mock.call("usersecondip"),
        ], any_order=True)

    def test_valid_multi_user_single_group_multi_ip(self, ip_network_mock):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstip,userfirstnetwork",
                "usersecondname": "usersecondip,usersecondnetwork",
            }
        })
        self.assertEqual(
            get_auth_ips(self.config),
            {
                "userfirstname_userfirstip": {
                    "username": "userfirstname",
                    "network": "userfirstip",
                    "groups": ["groupfirst"],
                },
                "usersecondname_usersecondip": {
                    "username": "usersecondname",
                    "network": "usersecondip",
                    "groups": ["groupfirst"],
                },
                "userfirstname_userfirstnetwork": {
                    "username": "userfirstname",
                    "network": "userfirstnetwork",
                    "groups": ["groupfirst"],
                },
                "usersecondname_usersecondnetwork": {
                    "username": "usersecondname",
                    "network": "usersecondnetwork",
                    "groups": ["groupfirst"],
                }
            }
        )
        ip_network_mock.assert_has_calls([
            mock.call("userfirstip"),
            mock.call("userfirstnetwork"),
            mock.call("usersecondip"),
            mock.call("usersecondnetwork"),
        ], any_order=True)

    def test_valid_single_user_multi_group_single_ip(self, ip_network_mock):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstip",
            },
            "groupsecond": {
                "userfirstname": "userfirstip",
            }
        })
        self.assertEqual(
            get_auth_ips(self.config),
            {
                "userfirstname_userfirstip": {
                    "username": "userfirstname",
                    "network": "userfirstip",
                    "groups": ["groupfirst", "groupsecond"],
                }
            }
        )
        ip_network_mock.assert_has_calls([
            mock.call("userfirstip"),
        ], any_order=True)

    def test_valid_single_user_multi_group_multi_ip(self, ip_network_mock):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstip,userfirstnetwork",
            },
            "groupsecond": {
                "userfirstname": "userfirstip,userfirstnetwork",
            }
        })
        self.assertEqual(
            get_auth_ips(self.config),
            {
                "userfirstname_userfirstip": {
                    "username": "userfirstname",
                    "network": "userfirstip",
                    "groups": ["groupfirst", "groupsecond"],
                },
                "userfirstname_userfirstnetwork": {
                    "username": "userfirstname",
                    "network": "userfirstnetwork",
                    "groups": ["groupfirst", "groupsecond"],
                }
            }
        )
        ip_network_mock.assert_has_calls([
            mock.call("userfirstip"),
            mock.call("userfirstnetwork"),
        ], any_order=True)

    def test_valid_multi_user_multi_group_single_ip(self, ip_network_mock):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstip",
                "usersecondname": "usersecondip",
            },
            "groupsecond": {
                "userfirstname": "userfirstip",
                "usersecondname": "usersecondip",
            }
        })
        self.assertEqual(
            get_auth_ips(self.config),
            {
                "userfirstname_userfirstip": {
                    "username": "userfirstname",
                    "network": "userfirstip",
                    "groups": ["groupfirst", "groupsecond"],
                },
                "usersecondname_usersecondip": {
                    "username": "usersecondname",
                    "network": "usersecondip",
                    "groups": ["groupfirst", "groupsecond"],
                }
            }
        )
        ip_network_mock.assert_has_calls([
            mock.call("userfirstip"),
            mock.call("usersecondip"),
        ], any_order=True)

    def test_valid_multi_user_multi_group_multi_ip(self, ip_network_mock):
        self.config.read_dict({
            "groupfirst": {
                "userfirstname": "userfirstip,userfirstnetwork",
                "usersecondname": "usersecondip,usersecondnetwork",
            },
            "groupsecond": {
                "userfirstname": "userfirstip,userfirstnetwork",
                "usersecondname": "usersecondip,usersecondnetwork",
            }
        })
        self.assertEqual(
            get_auth_ips(self.config),
            {
                "userfirstname_userfirstip": {
                    "username": "userfirstname",
                    "network": "userfirstip",
                    "groups": ["groupfirst", "groupsecond"],
                },
                "usersecondname_usersecondip": {
                    "username": "usersecondname",
                    "network": "usersecondip",
                    "groups": ["groupfirst", "groupsecond"],
                },
                "userfirstname_userfirstnetwork": {
                    "username": "userfirstname",
                    "network": "userfirstnetwork",
                    "groups": ["groupfirst", "groupsecond"],
                },
                "usersecondname_usersecondnetwork": {
                    "username": "usersecondname",
                    "network": "usersecondnetwork",
                    "groups": ["groupfirst", "groupsecond"],
                }
            }
        )
        ip_network_mock.assert_has_calls([
            mock.call("userfirstip"),
            mock.call("userfirstnetwork"),
            mock.call("usersecondip"),
            mock.call("usersecondnetwork"),
        ], any_order=True)
