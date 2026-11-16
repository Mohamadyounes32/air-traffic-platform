import sys
import pandas as pd
import sqlalchemy
import requests
import pyarrow
import psycopg2

print("Python:    ", sys.version.split()[0])
print("pandas:    ", pd.__version__)
print("sqlalchemy:", sqlalchemy.__version__)
print("requests:  ", requests.__version__)
print("pyarrow:   ", pyarrow.__version__)
print("psycopg2:  ", psycopg2.__version__.split()[0])
print("Environment OK")