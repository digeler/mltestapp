import os
import inspect
import importlib.util as imp
import logging
import sys
import json

from azureml.api.exceptions.BadRequest import BadRequestException
from azureml.api.realtime.swagger_spec_generator import generate_service_swagger
try:
    from azureml.webservice_schema._schema_util import parse_service_input, load_service_schema
except ImportError:
    pass

driver_module_spec = imp.spec_from_file_location('service_driver', 'score.py')
driver_module = imp.module_from_spec(driver_module_spec)
driver_module_spec.loader.exec_module(driver_module)

if(True):
    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    aml_logger = logging.getLogger('azureml')
    aml_logger.setLevel(logging.DEBUG)
    aml_logger.addHandler(stream_handler)

def run(http_body, request_headers):
    global run_supports_request_headers

    if aml_service_schema is not None:
        arguments = parse_service_input(http_body, aml_service_schema.input)

        if run_supports_request_headers:
            arguments["request_headers"] = request_headers

        try:
            return_obj = driver_module.run(**arguments)
        except TypeError as exc:
            raise BadRequestException(str(exc))
    else:
        arguments = {run_input_parameter_name: http_body}
        if run_supports_request_headers:
            arguments["request_headers"] = request_headers

        return_obj = driver_module.run(**arguments)

    return return_obj


def init():
    global aml_service_schema
    global run_input_parameter_name
    global run_supports_request_headers

    schema_file = ""
    service_name = os.getenv('SERVICE_NAME', 'ML service')
    service_path_prefix = os.getenv('SERVICE_PATH_PREFIX', '')
    service_version = os.getenv('SERVICE_VERSION', '1.0')

    if schema_file:
        aml_service_schema = load_service_schema(schema_file)
    else:
        aml_service_schema = None

    swagger_json = generate_service_swagger(service_name=service_name,
                                            service_schema_file_path=schema_file,
                                            service_version=service_version,
                                            service_path_prefix=service_path_prefix)

    with open('swagger.json', 'w') as swagger_file:
        json.dump(swagger_json, swagger_file)

    run_args = inspect.signature(driver_module.run).parameters.keys()
    run_args_list = list(run_args)
    run_input_parameter_name = run_args_list[0] if run_args_list[0] != "request_headers" else run_args_list[1]
    run_supports_request_headers = "request_headers" in run_args_list

    driver_module.init()