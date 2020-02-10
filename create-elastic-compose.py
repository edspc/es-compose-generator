#!/usr/bin/env python

"""create-elastic-compose.py: This script create es-docker-compose.yml with different versions of Elasticsearch. Usage create-elastic-compose.py <version1> <version2>"""

__author__      = "Eduard Muradov (muudmik@gmail.com)"

import json
import requests
import sys
import re
import yaml

assert sys.version_info >= (3,0)

compose_version = '3.3'

def get_api_token() -> str:
    response = requests.get('https://docker-auth.elastic.co/auth?service=token-service&scope=repository:elasticsearch/elasticsearch:pull')

    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))['token']
    else:
        raise ValueError('Could not get token.')

def get_tag_list() -> list:
    headers = {'Content-Type': 'application/json',
           'Authorization': 'Bearer {0}'.format(get_api_token())}
    response = requests.get('https://docker.elastic.co/v2/elasticsearch/elasticsearch/tags/list', headers=headers)

    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))['tags']
    else:
        raise ValueError('Could not retrive tags list')

def normalize_remote_tags() -> list:
    tags = get_tag_list()
    valid_tags = []

    for tag in tags:
        if (re.match(r"^\d+\.\d+\.\d+$", tag)):
            valid_tags.append(tag)
    
    if (len(valid_tags) > 0):
        valid_tags.sort(key=lambda s: list(map(int, s.split('.'))), reverse = True)
    else:
        raise ValueError('No valid tags found.')

    return valid_tags

def get_last_tag_by_version(version, tags) -> str:
    pattern = r"^"+version.replace('.', r'\.')+r"\.\d+$"
    r = re.compile(pattern)

    return next(filter(r.match, tags))


def get_configured_service(version, tag) -> dict:
    name = 'es'+version.replace('.', '')

    return {
        name : {
            'image': 'docker.elastic.co/elasticsearch/elasticsearch:'+tag,
            'restart': 'unless-stopped',
            'ports': [
                '92'+version.replace('.', '')+':9200'
            ],
            'environment': [
                'node.name='+name,
                'discovery.type=single-node',
                'cluster.name=docker-cluster-'+name,
                'bootstrap.memory_lock=true',
                'ES_JAVA_OPTS=-Xms512m -Xmx512m'
            ],
            'ulimits': {
                'memlock': {
                    'soft': -1,
                    'hard': -1
                }
            },
            'volumes': [
                '/var/lib/elasticsearch-docker/'+version+'/data:/usr/share/elasticsearch/data'
            ]
        }
    }
    
compose_content = {
    'version': compose_version,
    'services': {}
}

args = sys.argv
del args[0]

if (len(args) == 0):
    raise ValueError('No versions are presented.')

tags = normalize_remote_tags()

for version in args:
    last_version_tag = get_last_tag_by_version(version, tags)
    compose_content['services'].update(get_configured_service(version, last_version_tag))


with open('es-docker-compose.yml', 'w') as yml:
    yaml.dump(compose_content, yml, allow_unicode=True)

