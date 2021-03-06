#!/usr/bin/env python
# This script comes with no warranty use at your own risk
#
# Title: Get Rubrik Ids
# Author: Drew Russell - Rubrik Ranger Team
# Edited: Michael Levit - Rubrik SE @innocom.co.il E-Mail: Michaell@innocom.co.il
# Date: 03/14/2018
# Updated: 05/07/2018
# Python ver: 3.6.4, 2.7.6
#
# Description:
#
# Create HTML page with all the IDs rubrik is mapping to your data
# Functions added by Michael Levit : get_sla_domains(), get_vms(), get_hosts(), get_filesets(), get_mssql(), get_cluster(), get_available_storage(), write_html(), write_files()
# In case you want to run specific functions you can change the list within write_files() functions.
# In case you want to add/remove keys you can edit "keys" in each of the functions.
# -*- coding: utf-8 -*-

######################################## User Provided Variables #################################

# Cluster IP Address and Credentials
NODE_IP = "126.0.100.1"
USERNAME = "admin"
PASSWORD = "thisisnotveeam"

######################################## End User Provided Variables ##############################

import webbrowser
import os
import base64
import requests
import json
import sys
import json
import time
import csv
from requests.auth import HTTPBasicAuth
from json2table import convert
from pprint import pprint

# ignore certificate verification messages
requests.packages.urllib3.disable_warnings()


# Generic Rubrik API Functions


def basic_auth_header(username, password):
    """Takes a username and password and returns a value suitable for
    using as value of an Authorization header to do basic auth.
    """
    return base64.b64encode(username + ':' + password)


def login_token(username, password):
    """ Generate a new API Token """

    api_version = "v1"
    api_endpoint = "/session"

    request_url = "https://{}/api/{}{}".format(NODE_IP, api_version, api_endpoint)

    data = {'username': username, 'password': password}

    authentication = HTTPBasicAuth(username, password)

    try:
        api_request = requests.post(request_url, data=json.dumps(data), verify=False, auth=authentication)
    except requests.exceptions.ConnectionError as connection_error:
        print(connection_error)
        sys.exit()
    except requests.exceptions.HTTPError as http_error:
        print(http_error)
        sys.exit()

    response_body = api_request.json()

    if 'token' in response_body:
        return response_body['token']
    else:
        print('The response body did not contain the expected token.\n')
        print(response_body)


def rubrik_get(api_version, api_endpoint, token):
    """ Connect to a Rubrik Cluster and perform a GET operation """

    AUTHORIZATION_HEADER = {'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'Authorization': 'Bearer ' + token
                            }

    request_url = "https://{}/api/{}{}".format(NODE_IP, api_version, api_endpoint)

    try:
        api_request = requests.get(request_url, verify=False, headers=AUTHORIZATION_HEADER)
        # Raise an error if they request was not successful
        api_request.raise_for_status()
    except requests.exceptions.RequestException as error_message:
        print(error_message)
        sys.exit(1)

    response_body = api_request.json()

    return response_body


def rubrik_post(api_version, api_endpoint, config, token):
    """ Connect to a Rubrik Cluster and perform a POST operation """

    AUTHORIZATION_HEADER = {'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'Authorization': 'Bearer ' + token
                            }

    config = json.dumps(config)

    request_url = "https://{}/api/{}{}".format(NODE_IP, api_version, api_endpoint)

    try:
        api_request = requests.post(request_url, data=config, verify=False, headers=AUTHORIZATION_HEADER)
        # Raise an error if they request was not successful
        api_request.raise_for_status()
    except requests.exceptions.RequestException as error_message:
        print(error_message)
        sys.exit(1)

    response_body = api_request.json()

    return response_body


# Script Specific Function


def get_vm_by_cluster(cluster_name, token):
    """Get all Virtual Machines and it's effective SLA Domain ID from a specific cluster """

    current_vm = rubrik_get('v1', '/vmware/vm?is_relic=false', token)
    response_data = current_vm['data']

    vm_sla = {}

    for result in response_data:
        try:
            if result['clusterName'] == cluster_name:
                if result['effectiveSlaDomainId'] != "UNPROTECTED":
                    # {vm_id: sla_domain_id}
                    vm_sla[result['id']] = result['effectiveSlaDomainId']
        except:
            continue

    if bool(vm_sla) is False:
        print('\nUnable to locate any virtual machines in the "{}" Cluster.\n'.format(cluster_name))

    return vm_sla


def get_vm_by_sla_domain(sla_domain_name, token):
    """ """

    sla_domain = rubrik_get('v1', '/sla_domain?name={}'.format(sla_domain_name), token)
    response_data = sla_domain['data']

    for result in response_data:
        try:
            if result['name'] == sla_domain_name:
                sla_domain_id = result['id']
        except:
            continue

    try:
        sla_domain_id
    except NameError:
        print("Error: The Rubrik Cluster does not contain the {} SLA Domain".format(sla_domain_name))
        sys.exit()

    current_vm = rubrik_get('v1', '/vmware/vm?is_relic=false', token)
    response_data = current_vm['data']

    vm_sla = {}

    for result in response_data:
        try:
            if result['effectiveSlaDomainId'] == sla_domain_id:
                vm_sla[result['id']] = result['effectiveSlaDomainId']
        except:
            continue

    if bool(vm_sla) is False:
        print('\nUnable to locate any virtual machines assigned to the "{}" SLA Domain.\n'.format(sla_domain_name))

    return vm_sla


def get_sla_domain_id(sla_domain_name, token):
    """ """

    sla_domain = rubrik_get('v1', '/sla_domain?name={}'.format(sla_domain_name), token)
    response_data = sla_domain['data']

    for result in response_data:
        try:
            if result['name'] == sla_domain_name:
                sla_domain_id = result['id']
        except:
            continue

    try:
        sla_domain_id
    except NameError:
        print("Error: The Rubrik Cluster does not contain the {} SLA Domain".format(sla_domain_name))
        sys.exit()

    return sla_domain_id


def on_demand_snapshot(vm_id, sla_id, token):
    """ Create a On Demand Snapshot """
    on_demand_snapshot_config = {}

    on_demand_snapshot_config['slaId'] = sla_id

    rubrik_post('v1', '/vmware/vm/{}/snapshot'.format(vm_id), on_demand_snapshot_config, token)


def get_sla_domains(token):
    """ """
    sla_domain = rubrik_get('v1', '/sla_domain', token)
    response_data = sla_domain['data']
    data = {}
    data["SLA"] = {}
    keys = ["name", "id"]
    for result in response_data:
        data["SLA"][result['name']] = {k: result[k] for k in keys}
    return data


def get_vms(token):
    """ """
    vm = rubrik_get('v1', '/vmware/vm?sort_by=name', token)
    response_data = vm['data']
    data = {}
    data["Virtual Machines"] = {}
    keys = ["name", "id", "toolsInstalled", "hostId", "infraPath"]
    for result in response_data:
        data["Virtual Machines"][result['name']] = {k: result[k] for k in keys}
    return data


def get_hosts(token):
    """ """
    host = rubrik_get('v1', '/host?sort_by=hostname', token)
    response_data = host['data']
    data = {}
    data["Hosts"] = {}
    keys = ["hostname", "id", "operatingSystem"]
    for result in response_data:
        data["Hosts"][result["hostname"]] = {k: result[k] for k in keys}
    return data


def get_filesets(token):
    """ """
    fileset = rubrik_get('v1', '/fileset?sort_by=name', token)
    response_data = fileset['data']
    data = {}
    data["Fileset"] = {}
    keys = ["name", "id", "hostId", "hostName", "includes"]
    for result in response_data:
        data["Fileset"][result["name"]] = {k: result[k] for k in keys}
    return data


def get_mssql(token):
    """ """
    mssql = rubrik_get('v1', '/mssql/db', token)
    response_data = mssql['data']
    i = 0
    data = {}
    data["Mssql"] = {}
    keys = ['name', 'id', 'instanceId', 'instanceName', 'rootProperties']
    for result in response_data:
        if result['rootProperties']:
            data["Mssql"][result["name"]] = {k: result[k] for k in keys}
    return data


def get_cluster(token):
    """ """
    node = rubrik_get('internal', '/cluster/me/node', token)
    return node


def get_available_storage(token):
    """ """
    response_data = rubrik_get('internal', '/stats/available_storage', token)
    data = {}
    data["Storage"] = {}
    data["Storage"]["AvailableStorage"] = str(round(int(response_data['value']) / (1024 ** 4), 2))
    days = rubrik_get('internal', '/stats/runway_remaining', token)
    data["Storage"]["Estimated Runway "] = days
    return data


def data_to_json(data):
    json_object = data
    build_direction = "LEFT_TO_RIGHT"
    table_attributes = {"style": "width:100%"}
    html = convert(json_object, build_direction=build_direction, table_attributes=table_attributes)
    return (html)


def write_html(functions):
    html_str = """
    <!DOCTYPE html>
    <html>
        <head>
        <title>Rubrik Cluster Information</title>
        <style>
        table {
            border-collapse: collapse;
            width: 100%;
        }

        th, td {
            text-align: left;
            padding: 8px;
        }

        tr:nth-child(even){background-color: #f2f2f2}

        th {
            background-color: #7DD8FD;
            color: white;
        }
        .collapsible {
            background-color: #777;
            color: white;
            cursor: pointer;
            padding: 18px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 15px;
        }

        .active, .collapsible:hover {
            background-color: #555;
        }

        .collapsible:after {
            content: "+";
            color: white;
            font-weight: bold;
            float: right;
            margin-left: 5px;
        }

        .active:after {
            content: "-";
        }

        .content {
            padding: 0 18px;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.2s ease-out;
            background-color: #f1f1f1;
        }
        h1 {  
            text-align: center;
        }
        </style>
        </head>
        <body>
            <h1> Rubrik Cluster Information </h1>
            """
    for key, val in functions.items():
        html_str += """<button class="collapsible">""" + key + """</button>"""
        html_str += """<div class=\"content\">""" + (data_to_json((val(token)))) + """</div>"""
    html_str = html_str + """
        <script>
        var coll = document.getElementsByClassName("collapsible");
        var i;

        for (i = 0; i < coll.length; i++) {
          coll[i].addEventListener("click", function() {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            if (content.style.maxHeight){
              content.style.maxHeight = null;
            } else {
              content.style.maxHeight = content.scrollHeight + "px";
            } 
          });
        }
        </script>
        </body>
    </html>
    """
    return html_str


def write_files(html):
    functions = {'Cluster Information': get_cluster, 'Available Storage': get_available_storage,
                 'SLA Domains': get_sla_domains, 'Hosts': get_hosts, 'Filesets': get_filesets,
                 'Virtual Machines': get_vms, 'SQL Servers': get_mssql}
    html_file = open(html, "w")
    html_file.write(write_html(functions))
    html_file.close()


def json_to_csv():
    return 0


# Variable used to refresh the login token after 30 minutes
REFRESH_TOKEN = 0

# Generate the Initial Login Token
token = login_token(USERNAME, PASSWORD)

write_files("index.html")
filename = 'file:///' + os.getcwd() + '/' + 'index.html'
webbrowser.open_new_tab(filename)

# After 25 minutes (4500 seconds) reset the Refresh Token
if REFRESH_TOKEN == 4500:
    REFRESH_TOKEN = 0