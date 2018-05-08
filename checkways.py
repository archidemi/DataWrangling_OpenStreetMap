# I use this code to find the swapped entry.

import csv


with open('ways_tags.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        #if row['key'] == 'street' and row['value'] == '92131':
        if row['id'] == '132979649':
            print row

