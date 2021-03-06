########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

__author__ = 'dank'

from testenv import TestCase
from testenv import get_resource as resource
from testenv import deploy_application as deploy


class TestRelationships(TestCase):

    def test_pre_source_started_location_source(self):
        dsl_path = resource(
            "dsl/relationship-interface-pre-source-location-source.yaml")
        deploy(dsl_path)
        self.verify_assertions(hook='pre-init',
                               runs_on_source=True)

    def test_post_source_started_location_target(self):
        dsl_path = resource(
            "dsl/relationship-interface-post-source-location-target.yaml")
        deploy(dsl_path)
        self.verify_assertions(hook='post-init',
                               runs_on_source=False)

    def verify_assertions(self, hook, runs_on_source):

        if runs_on_source:
            node_id_id_prefix = 'mock_node_that_connects_to_host'
            related_id_prefix = 'host'
        else:
            node_id_id_prefix = 'host'
            related_id_prefix = 'mock_node_that_connects_to_host'

        from plugins.cloudmock.tasks import get_machines
        result = self.send_task(get_machines)
        machines = result.get(timeout=10)
        self.assertEquals(1, len(machines))

        from plugins.connection_configurer_mock.tasks import get_state \
            as config_get_state
        result = self.send_task(config_get_state)

        state = result.get(timeout=10)[0]

        node_id = state['id']
        related_id = state['related_id']

        self.assertTrue(node_id.startswith(node_id_id_prefix))
        self.assertTrue(related_id.startswith(related_id_prefix))

        from testenv import is_node_started
        self.assertTrue(is_node_started(related_id))

        if runs_on_source:
            self.assertEquals('source_property_value',
                              state['properties']['source_property_key'])
            self.assertEquals(
                'target_property_value',
                state['related_properties']['target_property_key'])
            self.assertEquals(
                'source_runtime_property_value',
                state['runtime_properties']['source_runtime_property_key']
            )
            self.assertEquals(
                'target_runtime_property_value',
                state['related_runtime_properties']
                     ['target_runtime_property_key']
            )
        else:
            self.assertEquals('source_property_value',
                              state['related_properties']
                              ['source_property_key'])
            self.assertEquals(
                'target_property_value',
                state['properties']['target_property_key'])
            self.assertEquals(
                'source_runtime_property_value',
                state['related_runtime_properties']
                     ['source_runtime_property_key']
            )
            self.assertEquals(
                'target_runtime_property_value',
                state['runtime_properties']
                     ['target_runtime_property_key']
            )

        if hook == 'pre-init':
            self.assertTrue(node_id not in
                            state['capabilities'])
        elif hook == 'post-init':
            self.assertTrue(is_node_started(node_id))
        else:
            self.fail('unhandled state')

        connector_timestamp = state['time']

        from plugins.testmockoperations.tasks import get_state \
            as testmock_get_state
        from plugins.testmockoperations.tasks import get_touched_time \
            as testmock_get_touch_time
        state = self.send_task(testmock_get_state).get(timeout=10)[0]
        touched_timestamp = self.send_task(testmock_get_touch_time)\
            .get(timeout=10)

        reachable_timestamp = state['time']
        if hook == 'pre-init':
            self.assertLess(touched_timestamp, connector_timestamp)
            self.assertGreater(reachable_timestamp, connector_timestamp)
        elif hook == 'post-init':
            self.assertLess(reachable_timestamp, connector_timestamp)
        else:
            self.fail('unhandled state')
