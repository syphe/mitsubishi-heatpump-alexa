from datetime import datetime
import uuid
import heatpump
from config import user_devices

def log(title, msg):
    print(f"[{title}]: {msg}")


def get_utc_timestamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.00Z")


def get_uuid():
    return str(uuid.uuid4())


def generate_response(name, context, appliance_id, correlation_token):
    return {
        "context": context,
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": name,
                "payloadVersion": "3",
                "messageId": get_uuid(),
                "correlationToken": correlation_token
            },
            "endpoint": {
                "endpointId": appliance_id
            },
            "payload": {}
        }
    }

def is_valid_token(access_token):
    return True


def get_devices():
    return user_devices


def is_device_online(applianceId, access_token):
    log("DEBUG", f"is_device_online(applianceId: ${applianceId})")
    return True


def handle_discovery(event, session):
    print("DEBUG", f"Discovery Request: {event}")

    access_token = event["directive"]["payload"]["scope"]["token"]

    if access_token == "" or (not is_valid_token(access_token)):
        message_id = event["directive"]["header"]["messageId"]
        error_message = f"Discovery Request [{message_id}] failed. Invalid access token: {access_token}"
        print("ERROR", error_message)
        return error_message

    return {
        "event": {
            "header": {
                "namespace": 'Alexa.Discovery',
                "name": 'Discover.Response',
                "payloadVersion": 3,
                "messageId": get_uuid()
            },
            "payload": {
                "endpoints": get_devices()
            }
        }
    }


def turn_on(appliance_id, access_token, correlation_token):
    log("DEBUG", f"turn_on(applianceId: {appliance_id}")

    now = datetime.now()

    if not heatpump.turn_on(appliance_id):
        return None

    context = {
        "properties": [
            {
                "namespace": "Alexa.PowerController",
                "name": "powerState",
                "value": "ON",
                "timeOfSample": get_utc_timestamp(now),
                "uncertaintyInMilliseconds": 1000,
            }
        ]
    }

    return generate_response("Response", context, appliance_id, correlation_token)


def turn_off(appliance_id, access_token, correlation_token):
    log("DEBUG", f"turn_off(applianceId: {appliance_id}")

    now = datetime.now()

    if not heatpump.turn_off(appliance_id):
        return None

    context = {
        "properties": [
            {
                "namespace": "Alexa.PowerController",
                "name": "powerState",
                "value": "OFF",
                "timeOfSample": get_utc_timestamp(now),
                "uncertaintyInMilliseconds": 1000,
            }
        ]
    }

    return generate_response("Response", context, appliance_id, correlation_token)

def set_target_temperature(appliance_id, access_token, correlation_token):
    log("DEBUG", f"set_target_temperature: {appliance_id}")

    context = {}

    return generate_response("Response", context, appliance_id, correlation_token)


def report_state(appliance_id, access_token, correlation_token):
    log("DEBUG", f"report_state(applianceId: {appliance_id}")

    status = heatpump.get_status(appliance_id)

    now = datetime.now()

    mode = None
    if status.setmode == 1:
        mode = "HEAT"
    elif status.setmode == 2:
        mode = "DRY"
    elif status.setmode == 3:
        mode = "COOL"
    elif status.setmode == 7:
        mode = "FAN"
    elif status.setmode == 8:
        mode = "AUTO"

    power_state = "ON" if status.power == 1 else "OFF"

    context = {
        "properties": [
            {
                "namespace": "Alexa.PowerController",
                "name": "powerState",
                "value": power_state,
                "timeOfSample": get_utc_timestamp(now),
                "uncertaintyInMilliseconds": 1000
            },
            {
                "namespace": "Alexa.TemperatureSensor",
                "name": "temperature",
                "value": {
                    "value": status.roomtemp,
                    "scale": "CELSIUS"
                },
                "timeOfSample": get_utc_timestamp(now),
                "uncertaintyInMilliseconds": 1000
            },
            {
                "namespace": "Alexa.ThermostatController",
                "name": "targetSetpoint",
                "value": {
                    "value": status.settemp,
                    "scale": "CELSIUS"
                },
                "timeOfSample": get_utc_timestamp(now),
                "uncertaintyInMilliseconds": 6000
            },
            {
                "namespace": "Alexa.ThermostatController",
                "name": "thermostatMode",
                "value": mode,
                "timeOfSample": get_utc_timestamp(now),
                "uncertaintyInMilliseconds": 6000
            }
        ]
    }

    return generate_response("StateReport", context, appliance_id, correlation_token)


def handle_control(event, session):
    log("DEBUG", f"Control Request: {event}")

    access_token = event["directive"]["endpoint"]["scope"]["token"]

    if access_token == "" or (not is_valid_token(access_token)):
        message_id = event["header"]["messageId"]
        error_message = f"Discovery Request [{message_id}] failed. Invalid access token: {access_token}"
        print("ERROR", error_message)
        return error_message

    appliance_id = event["directive"]["endpoint"]["endpointId"]

    if appliance_id == "":
        log("ERROR", "No applianceId provided in request")
        payload = {"faultingParameter": f"applianceId: {applianceId}"}
        return generate_response("UnexpectedInformationReceivedError", payload)

    if not is_device_online(appliance_id, access_token):
        log("ERROR", f"Device offline {access_token}")
        return generate_response("TargetOfflineError", {})

    response = None

    name = event["directive"]["header"]["name"]
    correlation_token = event["directive"]["header"]["correlationToken"]

    if name == "TurnOn":
        response = turn_on(appliance_id, access_token, correlation_token)
    elif name == "TurnOff":
        response = turn_off(appliance_id, access_token, correlation_token)
    elif name == "ReportState":
        response = report_state(appliance_id, access_token, correlation_token)
    elif name == "SetTargetTemperature":
        response = set_target_temperature(appliance_id, access_token, correlation_token)
    else:
        log("ERROR", f"No supported directive name: {name}")
        return generate_response("UnsupportedOperationError", {}, appliance_id, correlation_token)

    log(f"DEBUG", f"Control Confirmation: {response}")
    return response


def lambda_handler(event, session):
    namespace = event["directive"]["header"]["namespace"]
    if namespace == "Alexa.Discovery":
        return handle_discovery(event, session)
    elif namespace == "Alexa":
        return handle_control(event, session)
    elif namespace == "Alexa.PowerController":
        return handle_control(event, session)
    elif namespace == "Alexa.ThermostatController":
        return handle_control(event, session)

    error_message = f"No supported namespace: {namespace}"
    log("ERROR", error_message)
    return error_message
