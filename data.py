#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is the final version of the data-to-csv code.
# I first run this without validating any fields to check the original data.

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "sdsample.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

'''The mapping dictionary contains major word mapping from 
over-abbreviated street types/typos to accurate wording.'''
mapping = {'San Diego,': 'San Diego',
           'California': 'CA',
           'ca': 'CA',
           'Av': 'Avenue',
           'Ave': 'Avenue',
           'Bl': 'Boulevard',
           'Blvd': 'Boulevard',
           'Ct': 'Court',
           'Dr': 'Drive',
           'Ln': 'Lane',
           'Rd': 'Road',
           'St': 'Street',
           'Wy': 'Way'
           }

'''updates the specific strings if the last word is in "mapping".'''
def update_name(name, mapping):

    end = name.split()[-1]
    if end in mapping:
        name = name[:-len(end)] + mapping[end]
    
    return name

'''return boolean if the attribute is describing street'''
def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")

'''return boolean if the attribute is describing city'''
def is_city(elem):
    return (elem.attrib['k'] == 'addr:city')

'''return boolean if the attribute is describing state'''
def is_state(elem):
    return (elem.attrib['k'] == 'addr:state')

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields, way_attr_fields,
                  problem_chars, default_tag_type):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    # YOUR CODE HERE
    for tag in element.iter('tag'):
        k = tag.attrib['k']
        if problem_chars.search(k):
            continue
        else:
            one = {}
            one['id'] = element.attrib['id']
            if is_street_name(tag) or is_city(tag) or is_state(tag):
                one['value'] = update_name(tag.attrib['v'], mapping)
            else:
                one['value'] = tag.attrib['v']
            if LOWER_COLON.search(k):
                one['type'] = LOWER_COLON.search(k).group(0).split(':')[0]
                one['key'] = k[len(one['type'])+1:]
            else:
                one['key'] = k
                one['type'] = default_tag_type
            tags.append(one)
        
    if element.tag == 'node':
        for field in node_attr_fields:
            node_attribs[field] = element.attrib[field]
        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        for field in way_attr_fields:
            way_attribs[field] = element.attrib[field]
        count = 0
        for nd in element.iter('nd'):
            two = {}
            two['id'] = element.attrib['id']
            two['node_id'] = nd.attrib['ref']
            two['position'] = count
            count += 1
            way_nodes.append(two)
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular')
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)
    