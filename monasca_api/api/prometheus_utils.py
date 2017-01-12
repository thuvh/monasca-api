# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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

import time
import uuid

from collections import deque
from datetime import timedelta

import requests

from prometheus_client import core
from prometheus_client.core import _MetricWrapper
from prometheus_client.core import _ValueClass
from prometheus_client.core import default_timer
from prometheus_client.core import decorate
from prometheus_client.bridge.graphite import _RegularPush


MULTIPROCESS_MODES = ['min', 'max', 'livesum', 'liveall', 'all']


def sidecar_default_disambiguator():
    """
    Returns a string used to uniquely identify this process to the sidecar for
    aggregation purposes.

    :return: a unique identifier string
    """
    return str(uuid.uuid4())


class SidecarBridge(object):
    """A prometheus_client bridger for monasca-sidecar based on the
    graphite bridge"""
    def __init__(self, address, registry=core.REGISTRY, timeout_seconds=30,
                 disambiguator=sidecar_default_disambiguator):
        self.address = address
        self.registry = registry
        self.timeout = timeout_seconds
        self.id = disambiguator()

    def push(self, prefix=''):
        output = []

        for metric in self.registry.collect():
            metric_dict = {
                'name': metric.name,
                'help': metric.documentation,
                'type': metric.type,
                'values': []
            }

            for name, labels, value in metric.samples:
                labels = labels.copy()
                labels['_id'] = self.id

                metric_dict['values'].append({
                    'name': name,
                    'labels': labels,
                    'value': value
                })

            output.append(metric_dict)

        requests.post(self.address,
                      json=output,
                      timeout=self.timeout)

    def start(self, interval=30.0, prefix=''):
        t = _RegularPush(self, interval, prefix)
        t.daemon = True
        t.start()


class _Sample(object):
    def __init__(self, sample_time, value, count=1):
        self.sample_time = sample_time
        self.value = value
        self.count = count

    def is_valid(self, interval, when=None):
        """Checks if this sample is still valid for an interval-length time
        window.

        :param interval: the size of the time interval
        :param when: the point in time to check
        :return: True if valid, False if not
        """
        if when is None:
            when = time.time()

        diff = when - self.sample_time
        return diff <= interval.total_seconds()


class _MeanGaugeTimer(object):
    def __init__(self, gauge):
        self._gauge = gauge

    def __enter__(self):
        self._start = default_timer()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._gauge.sample(max(default_timer() - self._start, 0))

    def __call__(self, f):
        def wrapped(func, *args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return decorate(f, wrapped)


@_MetricWrapper
class RateGauge(object):
    _type = 'gauge'
    _reserved_labelnames = []

    def __init__(self, name, label_names, label_values,
                 multiprocess_mode='all', denominator=None, interval=None,
                 condense_mode='mean'):
        """A gauge that calculates mean rates per sec/min/hour over some window.

        Normally rates consumed by Prometheus would be derived on the server
        from raw values, but this derives them on the client as the Monasca
        API currently does not support this functionality.
        """
        if _ValueClass._multiprocess \
                and multiprocess_mode not in MULTIPROCESS_MODES:
            raise ValueError('Invalid multiprocess mode: ' + multiprocess_mode)

        self._value = _ValueClass(self._type, name, name, label_names,
                                  label_values, multiprocess_mode)

        if denominator is None:
            self.denominator = timedelta(seconds=1)
        else:
            self.denominator = denominator

        if interval is None:
            self.interval = timedelta(minutes=1)
        else:
            self.interval = interval

        self.condense_mode = condense_mode
        self.samples = deque()

    def sample(self, value, when=None):
        """Inputs a sample value at the given time.

        If `condense_mode` is set for this rate gauge, subsequent calls to
        `sample()` falling within `denominator` seconds will be combined
        based on the specified mode. A `condense_mode` of None will disable
        this behavior, but beware of excessive memory usage if this function
        is called frequently. Valid values for `condense_mode` include 'sum'
        and 'mean'.

        Note that if `when` is manually specified callers are responsible for
        ensuring input values are sane, i.e. `when` should be strictly
        ascending.

        :param value: the value to insert
        :param when: the time the sample was collected (now if unspecified)
        """
        if when is None:
            when = time.time()

        # remove all data points falling outside the window
        while self.samples and not self.samples[0].is_valid(self.interval, when):
            self.samples.popleft()

        # perf note: deque has O(1) access times from both ends
        prev = self.samples[-1] if self.samples else None
        if self.condense_mode \
                and prev \
                and prev.is_valid(self.denominator, when):
            # sum here but interpret sum vs mean later
            prev.value += value
            prev.count += 1
        else:
            self.samples.append(_Sample(when, value))

        count = 0
        total = 0
        for s in self.samples:
            if self.condense_mode == 'mean':
                count += 1
                total += (float(s.value) / s.count)
            elif self.condense_mode == 'sum':
                count += 1
                total += s.value
            else:
                count += s.count
                total += s.value

        window_mean_per_second = float(total) / self.interval.total_seconds()
        rate_per_unit = window_mean_per_second / self.denominator.total_seconds()

        self._value.set(rate_per_unit)

    def _samples(self):
        return ('', {}, self._value.get()),


@_MetricWrapper
class MeanGauge(object):
    _type = 'gauge'
    _reserved_labelnames = []

    def __init__(self, name, label_names, label_values,
                 multiprocess_mode='all', interval=None):
        """A gauge that calculates mean values over some window."""
        if _ValueClass._multiprocess \
                and multiprocess_mode not in MULTIPROCESS_MODES:
            raise ValueError('Invalid multiprocess mode: ' + multiprocess_mode)

        self._value = _ValueClass(self._type, name, name, label_names,
                                  label_values,
                                  multiprocess_mode=multiprocess_mode)

        if interval is None:
            self.interval = timedelta(minutes=1)
        else:
            self.interval = interval

        self.samples = deque()

    def sample(self, value, when=None):
        """Inputs a sample value at the given time.

        Note that if `when` is manually specified callers are responsible for
        ensuring input values are sane, i.e. `when` should be strictly
        ascending.

        :param value: the value to insert
        :param when: the time the sample was collected (now if unspecified)
        """
        if when is None:
            when = time.time()

        # remove all data points falling outside the window
        while self.samples and not self.samples[0].is_valid(self.interval, when):
            self.samples.popleft()

        # perf note: deque has O(1) access times from both ends
        prev = self.samples[-1] if self.samples else None
        if prev and prev.is_valid(self.interval, when):
            prev.value += value
            prev.count += 1
        else:
            self.samples.append(_Sample(when, value))

        count = 0
        total = 0
        for s in self.samples:
            count += s.count
            total += s.value

        self._value.set(float(total) / count)

    def time(self):
        return _MeanGaugeTimer(self)

    def _samples(self):
        return ('', {}, self._value.get()),
