# I changed the "key" value to check the validation and accuracy of each group of data.

import csv

postcodes = set()

with open('nodes_tags.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['type'] == 'addr' and row['key'] == 'postcode':
            postcodes.add(row['value'])
            
print postcodes