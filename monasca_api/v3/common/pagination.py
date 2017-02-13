# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import six.moves.urllib.parse as urlparse


def paginate(resource, uri, limit):
    parsed_uri = urlparse.urlparse(uri)

    self_link = build_base_uri(parsed_uri)

    old_query_params = _get_old_query_params(parsed_uri)

    if old_query_params:
        self_link += '?' + '&'.join(old_query_params)

    if resource and len(resource) > limit:

        if 'id' in resource[limit - 1]:
            new_offset = resource[limit - 1]['id']

        next_link = build_base_uri(parsed_uri)

        new_query_params = [u'offset' + '=' + urlparse.quote(
            new_offset.encode('utf8'), safe='')]

        _get_old_query_params_except_offset(new_query_params, parsed_uri)

        if new_query_params:
            next_link += '?' + '&'.join(new_query_params)

        resource = {u'links': ([{u'rel': u'self',
                                 u'href': self_link.decode('utf8')},
                                {u'rel': u'next',
                                 u'href': next_link.decode('utf8')}]),
                    u'elements': resource[:limit]}

    else:

        resource = {u'links': ([{u'rel': u'self',
                                 u'href': self_link.decode('utf8')}]),
                    u'elements': resource}

    return resource


def paginate_with_no_id(dictionary_list, uri, offset, limit):
    """This method is to paginate a list of dictionaries with no id in it.
       For example, metric name list, directory name list and directory
       value list.
    """
    parsed_uri = urlparse.urlparse(uri)
    self_link = build_base_uri(parsed_uri)
    old_query_params = _get_old_query_params(parsed_uri)

    if old_query_params:
        self_link += '?' + '&'.join(old_query_params)

    value_list = []
    for item in dictionary_list:
        value_list.extend(item.values())

    if value_list:
        # Truncate dictionary list with offset first
        truncated_list_offset = _truncate_with_offset(
            dictionary_list, value_list, offset)

        # Then truncate it with limit
        truncated_list_offset_limit = truncated_list_offset[:limit]

        links = [{u'rel': u'self', u'href': self_link.decode('utf8')}]
        if len(truncated_list_offset) > limit:
            new_offset = truncated_list_offset_limit[limit - 1].values()[0]
            next_link = build_base_uri(parsed_uri)
            new_query_params = [u'offset' + '=' + new_offset]

            _get_old_query_params_except_offset(new_query_params, parsed_uri)

            if new_query_params:
                next_link += '?' + '&'.join(new_query_params)

            links.append({u'rel': u'next', u'href': next_link.decode('utf8')})

        resource = {u'links': links,
                    u'elements': truncated_list_offset_limit}
    else:
        resource = {u'links': ([{u'rel': u'self',
                                 u'href': self_link.decode('utf8')}]),
                    u'elements': dictionary_list}

    return resource


def _truncate_with_offset(resource, value_list, offset):
    """Truncate a list of dictionaries with a given offset.
    """
    if not offset:
        return resource

    offset = offset.lower()
    for i, j in enumerate(value_list):
        # if offset matches one of the values in value_list,
        # the truncated list should start with the one after current offset
        if j == offset:
            return resource[i + 1:]
        # if offset does not exist in value_list, find the nearest
        # location and truncate from that location.
        if j > offset:
            return resource[i:]
    return []


def paginate_alarming(resource, uri, limit):
    parsed_uri = urlparse.urlparse(uri)

    self_link = build_base_uri(parsed_uri)

    old_query_params = _get_old_query_params(parsed_uri)

    if old_query_params:
        self_link += '?' + '&'.join(old_query_params)

    if resource and len(resource) > limit:

        old_offset = 0
        for param in old_query_params:
            if param.find('offset') >= 0:
                old_offset = int(param.split('=')[-1])
        new_offset = str(limit + old_offset)

        next_link = build_base_uri(parsed_uri)

        new_query_params = [u'offset' + '=' + urlparse.quote(
            new_offset.encode('utf8'), safe='')]

        _get_old_query_params_except_offset(new_query_params, parsed_uri)

        if new_query_params:
            next_link += '?' + '&'.join(new_query_params)

        resource = {u'links': ([{u'rel': u'self',
                                 u'href': self_link.decode('utf8')},
                                {u'rel': u'next',
                                 u'href': next_link.decode('utf8')}]),
                    u'elements': resource[:limit]}

    else:

        resource = {u'links': ([{u'rel': u'self',
                                 u'href': self_link.decode('utf8')}]),
                    u'elements': resource}

    return resource


def paginate_dimension_values(dimvals, uri, offset, limit):

    parsed_uri = urlparse.urlparse(uri)
    self_link = build_base_uri(parsed_uri)
    old_query_params = _get_old_query_params(parsed_uri)

    if old_query_params:
        self_link += '?' + '&'.join(old_query_params)

    if dimvals and dimvals[u'values']:
        have_more, truncated_values = _truncate_dimension_values(dimvals[u'values'],
                                                                 limit,
                                                                 offset)

        links = [{u'rel': u'self', u'href': self_link.decode('utf8')}]
        if have_more:
            new_offset = truncated_values[limit - 1]
            next_link = build_base_uri(parsed_uri)
            new_query_params = [u'offset' + '=' + urlparse.quote(
                new_offset.encode('utf8'), safe='')]

            _get_old_query_params_except_offset(new_query_params, parsed_uri)

            if new_query_params:
                next_link += '?' + '&'.join(new_query_params)

            links.append({u'rel': u'next', u'href': next_link.decode('utf8')})

        truncated_dimvals = {u'id': dimvals[u'id'],
                             u'dimension_name': dimvals[u'dimension_name'],
                             u'values': truncated_values}
        #
        # Only return metric name if one was provided
        #
        if u'metric_name' in dimvals:
            truncated_dimvals[u'metric_name'] = dimvals[u'metric_name']

        resource = {u'links': links,
                    u'elements': [truncated_dimvals]}
    else:
        resource = {u'links': ([{u'rel': u'self',
                                 u'href': self_link.decode('utf8')}]),
                    u'elements': [dimvals]}

    return resource


def _truncate_dimension_values(values, limit, offset):
    if offset and offset in values:
        next_value_pos = values.index(offset) + 1
        values = values[next_value_pos:]
    have_more = len(values) > limit
    return have_more, values[:limit]


def paginate_measurements(measurements, uri, limit):
    parsed_uri = urlparse.urlparse(uri)

    self_link = build_base_uri(parsed_uri)

    old_query_params = _get_old_query_params(parsed_uri)

    if old_query_params:
        self_link += '?' + '&'.join(old_query_params)

    if measurements:
        measurement_elements = []
        resource = {u'links': [{u'rel': u'self',
                                u'href': self_link.decode('utf8')},
                               ]}
        for measurement in measurements:
            if len(measurement['measurements']) >= limit:

                new_offset = measurement['measurements'][limit - 1][0]

                next_link = build_base_uri(parsed_uri)

                new_query_params = [u'offset' + '=' + urlparse.quote(
                    new_offset.encode('utf8'), safe='')]

                _get_old_query_params_except_offset(new_query_params, parsed_uri)

                if new_query_params:
                    next_link += '?' + '&'.join(new_query_params)

                resource[u'links'].append({u'rel': u'next',
                                           u'href': next_link.decode('utf8')})

                truncated_measurement = {u'dimensions': measurement['dimensions'],
                                         u'measurements': (measurement
                                                           ['measurements'][:limit]),
                                         u'name': measurement['name'],
                                         u'columns': measurement['columns'],
                                         u'id': measurement['id']}
                measurement_elements.append(truncated_measurement)
                break
            else:
                limit -= len(measurement['measurements'])
                measurement_elements.append(measurement)

        resource[u'elements'] = measurement_elements

    else:

        resource = {u'links': ([{u'rel': u'self',
                                 u'href': self_link.decode('utf8')}]),
                    u'elements': []}

    return resource


def _get_old_query_params(parsed_uri):
    old_query_params = []

    if parsed_uri.query:

        for query_param in parsed_uri.query.split('&'):
            query_param_name, query_param_val = query_param.split('=', 1)

            old_query_params.append(urlparse.quote(
                query_param_name.encode('utf8'), safe='') +
                "=" +
                urlparse.quote(query_param_val.encode('utf8'), safe=''))

    return old_query_params


def _get_old_query_params_except_offset(new_query_params, parsed_uri):
    if parsed_uri.query:

        for query_param in parsed_uri.query.split('&'):
            query_param_name, query_param_val = query_param.split('=', 1)
            if query_param_name.lower() != 'offset':
                new_query_params.append(urlparse.quote(
                    query_param_name.encode(
                        'utf8'), safe='') + "=" + urlparse.quote(
                    query_param_val.encode(
                        'utf8'), safe=''))


def paginate_statistics(statistics, uri, limit):
    parsed_uri = urlparse.urlparse(uri)

    self_link = build_base_uri(parsed_uri)

    old_query_params = _get_old_query_params(parsed_uri)

    if old_query_params:
        self_link += '?' + '&'.join(old_query_params)

    if statistics:
        statistic_elements = []
        resource = {u'links': [{u'rel': u'self',
                                u'href': self_link.decode('utf8')}]}

        for statistic in statistics:
            if len(statistic['statistics']) >= limit:

                new_offset = (
                    statistic['statistics'][limit - 1][0])

                next_link = build_base_uri(parsed_uri)

                new_query_params = [u'offset' + '=' + urlparse.quote(
                    new_offset.encode('utf8'), safe='')]

                _get_old_query_params_except_offset(new_query_params, parsed_uri)

                if new_query_params:
                    next_link += '?' + '&'.join(new_query_params)

                resource[u'links'].append({u'rel': u'next',
                                           u'href': next_link.decode('utf8')})

                truncated_statistic = {u'dimensions': statistic['dimensions'],
                                       u'statistics': (statistic['statistics'][:limit]),
                                       u'name': statistic['name'],
                                       u'columns': statistic['columns'],
                                       u'id': statistic['id']}

                statistic_elements.append(truncated_statistic)
                break
            else:
                limit -= len(statistic['statistics'])
                statistic_elements.append(statistic)

        resource[u'elements'] = statistic_elements

    else:

        resource = {u'links': ([{u'rel': u'self',
                                 u'href': self_link.decode('utf8')}]),
                    u'elements': []}

    return resource


def create_alarms_count_next_link(uri, offset, limit):
    if offset is None:
        offset = 0
    parsed_url = urlparse.urlparse(uri)
    base_url = build_base_uri(parsed_url)
    new_query_params = [u'offset=' + urlparse.quote(str(offset + limit))]
    _get_old_query_params_except_offset(new_query_params, parsed_url)

    next_link = base_url
    if new_query_params:
        next_link += '?' + '&'.join(new_query_params)

    return next_link


def build_base_uri(parsed_uri):
    return parsed_uri.scheme + '://' + parsed_uri.netloc + parsed_uri.path


def get_link(uri, resource_id, rel='self'):
    """Returns a link dictionary containing href, and rel.

    :param uri: the http request.uri.
    :param rel: the relation of the uri.
    :param resource_id: the id of the resource
    """
    parsed_uri = urlparse.urlparse(uri)
    href = build_base_uri(parsed_uri)
    href += '/' + resource_id

    if rel:
        link_dict = dict(href=href, rel=rel)
    else:
        link_dict = dict(href=href)

    return link_dict


def add_links_to_resource(resource, uri, rel='self'):
    """Adds links to the given resource dictionary.

    :param resource: the resource dictionary you wish to add links.
    :param uri: the http request.uri.
    :param rel: the relation of the uri.
    """
    resource['links'] = [get_link(uri, resource['id'], rel)]
    return resource


def add_links_to_resource_list(resourcelist, uri):
    """Adds links to the given resource dictionary list.

    :param resourcelist: the list of resources you wish to add links.
    :param uri: the http request.uri.
    """
    for resource in resourcelist:
        add_links_to_resource(resource, uri)
    return resourcelist
