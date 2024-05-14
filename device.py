from __future__ import annotations
from awscrt import mqtt  # type: ignore
from awsiot import mqtt_connection_builder  # type: ignore
import sys
import time
import json


class TelebrellaDevice():
    '''Class for each Telebrella Device that is be attached to this app'''

    def __init__(self,
                 uuid: str,
                 endpoint: str,
                 cmd_topic: str,
                 fdbk_topic: str) -> None:
        self.__uuid = uuid
        self.__endpoint = endpoint
        self.__cmd_topic = cmd_topic
        self.__fdbk_topic = fdbk_topic
        self.mqtt_connect()
        self._open_state = True
        self._windsensor_power = True

    @property
    def uuid(self) -> str:
        '''The unique identifier of the Telebrella

        Returns:
            str -- The uuid as a string
        '''
        return self.__uuid

    @property
    def is_open(self) -> bool:
        '''The open state of the umbrella

        Returns:
            bool -- _description_
        '''
        return self._open_state

    @is_open.setter
    def is_open(self, value: bool) -> None:
        '''Actions to perform when the umbrella open state is changed

        Arguments:
            value {bool} -- The new umbrella state
        '''
        self._open_state = not value
        self.mqtt_publish(
            topic=self.__cmd_topic,
            message={"umbrella": ("open" if value else "close")}
        )

    @property
    def windsensor_on(self) -> bool:
        '''The wind sensor power state

        Returns:
            bool -- Returns True if the wind sensor power is on
        '''
        return self._windsensor_power

    @windsensor_on.setter
    def windsensor_on(self, value: bool) -> None:
        '''Actions to perform when the wind sensor power state is changed

        Arguments:
            value {bool} -- The new state of the wind sensor power
        '''
        if value != self.windsensor_on:
            self.windsensor_on = not value
            self.mqtt_publish(
                topic=self.__cmd_topic,
                message={"windsensor": ("on" if value else "off")}
            )

    def mqtt_connect(self) -> None:
        '''Connects to the AWS IoT Core using MQTT and mTLS
        '''
        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=self.__endpoint,
            port=8883,
            cert_filepath="certs/app-cert.pem.crt",
            pri_key_filepath="certs/app-private.pem.key",
            ca_filepath="certs/AmazonRootCA1.pem",
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed,
            client_id="telebrella-" + self.__uuid,
            clean_session=False,
            keep_alive_secs=30,
            http_proxy_options=None,
            on_connection_success=self.on_connection_success,
            on_connection_failure=self.on_connection_failure,
            on_connection_closed=self.on_connection_closed
        )
        print("Connecting to endpoint with client ID")
        connect_future = self.mqtt_connection.connect()

        # Waits until a result is available
        connect_future.result()
        print("Connected!")

    def mqtt_subscribe(self, topic: str, callback) -> None:
        '''Subscribes to the listed topic and assigns a callback when a
        message is received

        Arguments:
            topic {str} -- The topic that is being subscribed to
            callback {function} -- The function to perform
        '''
        print("Subscribing to topic '{}'...".format(topic))
        subscribe_future, packet_id = self.mqtt_connection.subscribe(
            topci=topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=callback
        )

        subscribe_result = subscribe_future.result()
        print("Subscribed with {}".format(str(subscribe_result['qos'])))

    def mqtt_publish(self, topic: str, message: dict) -> None:
        '''Pushes a message to the provided topic

        Arguments:
            topic {str} -- The topic that the message is being pushed to
            message {dict} -- The message that is being pushed
        '''
        message_json = json.dumps(message)
        self.mqtt_connection.publish(
            topic=topic,
            payload=message_json,
            qos=mqtt.QoS.AT_LEAST_ONCE)
        time.sleep(1)

    def on_connection_interrupted(self, connection, error, **kwargs):
        '''Callback when connection is accidentally lost.
        '''
        print("Connection interrupted. error: {}".format(error))

    def on_connection_resumed(self,
                              connection,
                              return_code,
                              session_present,
                              **kwargs) -> None:
        '''Callback when an interrupted connection is re-established
        '''
        print("Connection resumed. return_code: {} session_present: {}".format(
            return_code, session_present))

        if all((return_code == mqtt.ConnectReturnCode.ACCEPTED,
                not session_present)):
            print("Session did not persist.",
                  "Resubscribing to existing topics...")
            resubscribe_future, _ = connection.resubscribe_existing_topics()

            # Cannot synchronously wait for resubscribe result
            # because we're on the connection's event-loop thread,
            # evaluate result with a callback instead.
            resubscribe_future.add_done_callback(self.on_resubscribe_complete)

    def on_resubscribe_complete(self, resubscribe_future):
        '''Callback when the topic is resubscribed after disconnect
        '''
        resubscribe_results = resubscribe_future.result()
        print("Resubscribe results: {}".format(resubscribe_results))

        for topic, qos in resubscribe_results['topics']:
            if qos is None:
                sys.exit(
                    "Server rejected resubscribe to topic: {}".format(topic))

    def on_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        '''Callback when the subscribed topic receives a message
        '''
        self.shadow_status = json.load(payload)

    def on_connection_success(self, connection, callback_data):
        '''Callback when the connection successfully connects
        '''
        assert isinstance(callback_data, mqtt.OnConnectionSuccessData)
        print("Connection Successful"
              "with return code: {} session present: {}".format(
                  callback_data.return_code, callback_data.session_present))

    def on_connection_failure(self, connection, callback_data):
        '''Callback when a connection attempt fails
        '''
        assert isinstance(callback_data, mqtt.OnConnectionFailureData)
        print("Connection failed with error code: {}".format(
            callback_data.error))

    def on_connection_closed(self, connection, callback_data):
        '''Callback when a connection has been disconnected or shutdown
        successfully
        '''
        print("Connection closed")
