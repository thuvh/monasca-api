================
config-generator
================

To generate sample configuration file execute::

  tox -e genconfig

To generate the sample policies execute::

  tox -e genpolicy

After generation you will have sample available in
``etc/api-policy.yaml.sample``. It's contain default values for all policies.
After you change it to suits your needs you will need to change monasca-api
configuration to look for new policy with specific file name. Head to
``api-config.conf`` file and then you will need to replace in ``[oslo_policy]``
section ``policy_file`` to your desired file name (like ``api-policy.yaml``).
