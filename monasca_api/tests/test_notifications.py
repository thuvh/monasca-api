import falcon.testing
import datetime
import fixtures
import oslo_config.fixture

from monasca_api.v2.reference import notifications

from monasca_api.tests import base


CONF = oslo_config.cfg.CONF

TENANT_ID = u"fedcba9876543210fedcba9876543210"


class TestNotifications(base.BaseApiTestCase):
    def setUp(self):
        super(TestNotifications, self).setUp()

        self.conf_override(
            notifications_driver='monasca_api.common.repositories.sqla.'
                                 'notifications_repository:NotificationsRepository',
            group='repositories')

        self.notifications_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.sqla.notifications_repository.NotificationsRepository'
        )).mock

        self.notification_resource = notifications.Notifications()
        self.api.add_route(
            '/v2.0/notification-methods', self.notification_resource)
        self.api.add_route(
            '/v2.0/notification-methods/{notification_method_id}', self.notification_resource)

    def test_list_notifications(self):
        expected_elements = \
            {'elements': [
                {'name': u'notifcation',
                 'id': u'1',
                 'type': u'EMAIL',
                 'period': 0,
                 'address': u'a@b.com',
                 'links': [{
                     'href': 'http://falconframework.org/v2.0/notification-methods/1',
                     'rel': 'self'}]}]}

        return_value = self.notifications_repo_mock.return_value
        return_value.list_notifications.return_value = \
            [{'name': u'notifcation',
              'id': u'1',
              'tenant_id': u'4199b031d5fa401abf9afaf7e58890b7',
              'type': u'EMAIL',
              'period': 0,
              'address': u'a@b.com',
              'created_at': datetime.datetime(2019, 3, 22, 9, 35, 25),
              'updated_at': datetime.datetime(2019, 3, 22, 9, 35, 25)}]
        response = self.simulate_request('/v2.0/notification-methods',
                                         headers={'X-Roles':
                                                  CONF.security.default_authorized_roles[0],
                                                  'X-Tenant-Id': TENANT_ID},
                                         method='GET')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, base.RESTResponseEquals(expected_elements))

    def test_list_notifications_with_sort_by(self):
        expected_elements = \
            {'elements': [
                {'name': u'notifcation',
                 'id': u'1',
                 'type': u'EMAIL',
                 'period': 0,
                 'address': u'a@b.com',
                 'links': [{
                     'href': 'http://falconframework.org/v2.0/notification-methods/1',
                     'rel': 'self'}]}]}

        return_value = self.notifications_repo_mock.return_value
        return_value.list_notifications.return_value = \
            [{'name': u'notifcation',
              'id': u'1',
              'tenant_id': u'4199b031d5fa401abf9afaf7e58890b7',
              'type': u'EMAIL',
              'period': 0,
              'address': u'a@b.com',
              'created_at': datetime.datetime(2019, 3, 22, 9, 35, 25),
              'updated_at': datetime.datetime(2019, 3, 22, 9, 35, 25)}]
        response = self.simulate_request('/v2.0/notification-methods',
                                         headers={'X-Roles':
                                                  CONF.security.default_authorized_roles[0],
                                                  'X-Tenant-Id': TENANT_ID},
                                         query_string='sort_by=name',
                                         method='GET')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, base.RESTResponseEquals(expected_elements))

    def test_list_notifications_with_offset(self):
        expected_elements = \
            {'elements': [
                {'name': u'notifcation',
                 'id': u'1',
                 'type': u'EMAIL',
                 'period': 0,
                 'address': u'a@b.com',
                 'links': [{
                     'href': 'http://falconframework.org/v2.0/notification-methods/1',
                     'rel': 'self'}]}]}

        return_value = self.notifications_repo_mock.return_value
        return_value.list_notifications.return_value = \
            [{'name': u'notifcation',
              'id': u'1',
              'tenant_id': u'4199b031d5fa401abf9afaf7e58890b7',
              'type': u'EMAIL',
              'period': 0,
              'address': u'a@b.com',
              'created_at': datetime.datetime(2019, 3, 22, 9, 35, 25),
              'updated_at': datetime.datetime(2019, 3, 22, 9, 35, 25)}]
        response = self.simulate_request('/v2.0/notification-methods',
                                         headers={'X-Roles':
                                                  CONF.security.default_authorized_roles[0],
                                                  'X-Tenant-Id': TENANT_ID},
                                         query_string='offset=10',
                                         method='GET')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, base.RESTResponseEquals(expected_elements))

    def test_get_notification_with_id(self):
        expected_elements = \
            {'name': u'notifcation',
             'id': u'1',
             'type': u'EMAIL',
             'period': 0,
             'address': u'a@b.com'}

        return_value = self.notifications_repo_mock.return_value
        return_value.list_notification.return_value = \
            {'name': u'notifcation',
             'id': u'1',
             'tenant_id': u'4199b031d5fa401abf9afaf7e58890b7',
             'type': u'EMAIL',
             'period': 0,
             'address': u'a@b.com',
             'created_at': datetime.datetime(2019, 3, 22, 9, 35, 25),
             'updated_at': datetime.datetime(2019, 3, 22, 9, 35, 25)}
        response = self.simulate_request('/v2.0/notification-methods/1',
                                         headers={'X-Roles':
                                                  CONF.security.default_authorized_roles[0],
                                                  'X-Tenant-Id': TENANT_ID},
                                         method='GET')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, base.RESTResponseEquals(expected_elements))

