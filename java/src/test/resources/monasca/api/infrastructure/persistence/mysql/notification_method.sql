CREATE TABLE `notification_method` (
  `id` varchar(36) NOT NULL,
  `tenant_id` varchar(36) NOT NULL DEFAULT '',
  `name` varchar(250) NOT NULL DEFAULT '',
  `type` varchar(10) NOT NULL DEFAULT 'EMAIL' check type in ('EMAIL', 'WEBHOOK', 'PAGERDUTY'),
  `address` varchar(100) NOT NULL DEFAULT '',
  `periodic_interval` tinyint NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
);
