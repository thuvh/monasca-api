# Copyright 2018 SUSE Linux GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import with_statement

import monasca_api.config

from alembic import context
from logging.config import fileConfig

from monasca_api.common.repositories.sqla import models
from monasca_api.common.repositories.sqla import sql_repository

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# FIXME: Move this to the monasca_db entry point later.
# Load monasca-api config (from files only)
monasca_api.config.parse_args(argv=[])

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = models.get_all_metadata()

nc = {"ix": "ix_%(column_0_label)s",
      "uq": "uq_%(table_name)s_%(column_0_name)s",
      "fk": "fk_%(table_name)s_%(column_0_name)s",
      "pk": "pk_%(table_name)s"}

target_metadata.naming_convention = nc


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = sql_repository.get_engine()

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


def fingerprint_db():
    return


def stamp_db():
    return


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
