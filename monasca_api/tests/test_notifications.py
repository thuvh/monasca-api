import falcon.testing
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

        self.notification_resource = notifications.Notifications()
        self.api.add_route(
            '/v2.0/notification-methods', self.notification_resource)

        self.notifications_repo_mock = self.useFixture(fixtures.MockPatch(
            'monasca_api.common.repositories.sqla.notifications_repository.NotificationsRepository'
        )).mock

    def test_list_notification(self):

        return_value = self.notifications_repo_mock.return_value
        return_value.list_notifications.return_value = []

        response = self.simulate_request('/v2.0/notification-methods',
                                         headers={'X-Roles':
                                                  CONF.security.default_authorized_roles[0],
                                                  'X-Tenant-Id': TENANT_ID},
                                         method='GET')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertThat(response, base.RESTResponseEquals([]))
