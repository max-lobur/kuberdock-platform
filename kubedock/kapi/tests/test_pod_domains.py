
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

from collections import namedtuple
import unittest
import mock

from kubedock.testutils.testcases import FlaskTestCase
from kubedock.testutils import create_app
from kubedock.exceptions import PodDomainExists

from kubedock.kapi import pod_domains


class TestCase(FlaskTestCase):
    def create_app(self):
        return create_app(self)


Domain = namedtuple('Domain', ('id', 'name'))
Pod = namedtuple('Pod', ('id', 'name', 'owner'))
User = namedtuple('User', ('username',))


class TestSetPodDomain(TestCase):

    def setUp(self):
        self.pod = Pod(
            id='qwerty', name='pod', owner=User(username='user'))
        self.pod_domain_name = '{0}-{1}'.format(
            self.pod.owner.username, self.pod.name)
        self.base_domain_name = 'base.domain'
        self.sub_domain_name = 'sub'
        self.full_domain_name = '{0}.{1}'.format(
            self.sub_domain_name, self.base_domain_name
        )

    @mock.patch.object(pod_domains, '_get_unique_domain_name')
    @mock.patch.object(pod_domains, 'PodDomain')
    @mock.patch.object(pod_domains, 'BaseDomain')
    def test_set_pod_name(self, base_domain_mock, pod_domain_mock,
                          get_unique_domain_name_mock):
        base_domain = Domain(1234, self.base_domain_name)
        base_domain_mock.query.filter_by.return_value.first.return_value = \
            base_domain
        pod_domain = mock.Mock()
        pod_domain_mock.return_value = pod_domain
        pod_domain_mock.query.filter_by.return_value.first.return_value = None
        get_unique_domain_name_mock.side_effect = lambda basename, _: basename

        # non unique domain
        rv1 = pod_domains.get_or_create_pod_domain(self.pod,
                                                   self.base_domain_name)
        pod_domain_mock.assert_called_once_with(
            name=self.pod_domain_name,
            base_domain=base_domain,
            pod_id=self.pod.id
        )

        pod_domain_mock.reset_mock()

        # unique domain
        pod_domain_mock.query.filter_by.return_value.first.return_value = None
        rv2 = pod_domains.get_or_create_pod_domain(self.pod,
                                                   self.base_domain_name)

        pod_domain_mock.assert_called_once_with(
            name=self.pod_domain_name,
            base_domain=base_domain,
            pod_id=self.pod.id
        )
        self.assertEqual((rv1, rv2), ((pod_domain, True), (pod_domain, True)))

        pod_domain_mock.reset_mock()

        # pod domain exists
        pod_domain_mock.query.filter_by.return_value.first.return_value = \
            pod_domain
        rv3 = pod_domains.get_or_create_pod_domain(self.pod,
                                                   self.base_domain_name)
        self.assertEqual(rv3, (pod_domain, False))

        # subdomain is free
        base_domain_mock.query.filter_by.return_value.first.side_effect = (
            None, base_domain
        )
        pod_domain_mock.query.filter.return_value.first.return_value = None
        pod_domain_mock.query.filter_by.return_value.first.return_value = None

        pod_domains.get_or_create_pod_domain(self.pod, self.full_domain_name)

        pod_domain_mock.assert_called_once_with(
            name=self.sub_domain_name,
            base_domain=base_domain,
            pod_id=self.pod.id
        )

        # subdomain exists
        base_domain_mock.query.filter_by.return_value.first.side_effect = (
            None, base_domain
        )
        pod_domain_mock.query.filter.return_value.first.return_value = \
            pod_domain
        with self.assertRaises(PodDomainExists):
            pod_domains.get_or_create_pod_domain(self.pod,
                                                 self.full_domain_name)

        # edit subdomain
        base_domain_mock.query.filter_by.return_value.first.side_effect = (
            None, base_domain
        )
        pod_domain.name = 'old'
        pod_domain_mock.query.filter.return_value.first.return_value = \
            None
        pod_domain_mock.query.filter_by.return_value.first.return_value = \
            pod_domain

        rv4 = pod_domains.get_or_create_pod_domain(self.pod,
                                                   self.full_domain_name)
        self.assertEqual(
            (rv4, rv4[0].name),
            ((pod_domain, False), self.sub_domain_name)
        )

    @mock.patch.object(pod_domains, 'randstr')
    @mock.patch.object(pod_domains, 'PodDomain')
    def test_get_unique_domain_name(self, pod_domain_mock, randstr_mock):
        query_first_mock = mock.Mock()
        pod_domain_mock.query.filter_by.return_value.first = query_first_mock
        query_first_mock.return_value = None
        dname = 'qwerty1234'
        domain_id = 22
        res = pod_domains._get_unique_domain_name(dname, domain_id)
        self.assertEqual(res, dname)
        pod_domain_mock.query.filter_by.assert_called_once_with(
            name=dname, domain_id=domain_id)
        pod_domain_mock.query.filter_by.reset_mock()

        # if the first call returns som object, the to basename must be
        # appended random suffix
        query_first_mock.reset_mock()
        query_first_mock.side_effect = ['something', 'somethingelse', None]
        random_suffix = 'sfsfd'
        randstr_mock.return_value = random_suffix
        res = pod_domains._get_unique_domain_name(dname, domain_id)
        self.assertEqual(dname + random_suffix, res)
        self.assertEqual(randstr_mock.call_count, 2)
        self.assertEqual(pod_domain_mock.query.filter_by.call_count, 3)
        pod_domain_mock.query.filter_by.assert_called_with(
            name=dname + random_suffix, domain_id=domain_id)


if __name__ == '__main__':
    unittest.main()
