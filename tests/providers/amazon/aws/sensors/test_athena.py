#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

from unittest import mock

import pytest

from airflow.exceptions import AirflowException, AirflowSkipException
from airflow.providers.amazon.aws.hooks.athena import AthenaHook
from airflow.providers.amazon.aws.sensors.athena import AthenaSensor


class TestAthenaSensor:
    def setup_method(self):
        self.sensor = AthenaSensor(
            task_id="test_athena_sensor",
            query_execution_id="abc",
            sleep_time=5,
            max_retries=1,
            aws_conn_id="aws_default",
        )

    @mock.patch.object(AthenaHook, "poll_query_status", side_effect=("SUCCEEDED",))
    def test_poke_success(self, mock_poll_query_status):
        assert self.sensor.poke({}) is True

    @mock.patch.object(AthenaHook, "poll_query_status", side_effect=("RUNNING",))
    def test_poke_running(self, mock_poll_query_status):
        assert self.sensor.poke({}) is False

    @mock.patch.object(AthenaHook, "poll_query_status", side_effect=("QUEUED",))
    def test_poke_queued(self, mock_poll_query_status):
        assert self.sensor.poke({}) is False

    @mock.patch.object(AthenaHook, "poll_query_status", side_effect=("FAILED",))
    def test_poke_failed(self, mock_poll_query_status):
        with pytest.raises(AirflowException) as ctx:
            self.sensor.poke({})
        assert "Athena sensor failed" in str(ctx.value)

    @mock.patch.object(AthenaHook, "poll_query_status", side_effect=("CANCELLED",))
    def test_poke_cancelled(self, mock_poll_query_status):
        with pytest.raises(AirflowException) as ctx:
            self.sensor.poke({})
        assert "Athena sensor failed" in str(ctx.value)

    @pytest.mark.parametrize(
        "soft_fail, expected_exception", ((False, AirflowException), (True, AirflowSkipException))
    )
    def test_fail_poke(self, soft_fail, expected_exception):
        self.sensor.soft_fail = soft_fail
        message = "Athena sensor failed"
        with pytest.raises(expected_exception, match=message), mock.patch(
            "airflow.providers.amazon.aws.hooks.athena.AthenaHook.poll_query_status"
        ) as poll_query_status:
            poll_query_status.return_value = "FAILED"
            self.sensor.poke(context={})
