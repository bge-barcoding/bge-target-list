import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import argparse
import logging
import re
import pandas as pd
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from orm.common import DataSource, get_specimen_index_dict, get_barcode_index_dict
from orm.nsr_node import NsrNode
from orm.nsr_species import NsrSpecies
from orm.nsr_synonym import NsrSynonym
from orm.barcode import Barcode
from orm.specimen import Specimen
from orm.marker import Marker
import loggers

main_logger = logging.getLogger('main')
lk_logger = logging.getLogger('load_klasse')


def has_unusual_name(taxon):
    ignore_name_pattern = ['?', '(', 'to be checked']
    for el in ignore_name_pattern:
        if el in taxon:
            return True
    return False


# initializes a dict with the fields that should go in barcode and specimen table, or None if any of the checks fail
def init_record_fields(row):
    # print(row)
    record = {}
    # print(row.__dict__)
    # IEEE specs say NaN's can not be equal, so that's how we do the checks for missing values

    # check if there is a sequence, otherwise nothing to do
    if not row['Sequence']:
        lk_logger.warning("Record %s has no sequence, skipping..." % row['GBnumber'])
        return None

    if not row['Taxon name']:
        lk_logger.warning("Record %s has no Taxon field, skipping..." % row['GBnumber'])
        return None

    # set up the other required fields
    record['taxon'] = row['Taxon name']
    record['marker'] = row['Biomarker']
    record['catalognum'] = row['StrainID']
    record['institution_storing'] = 'Westerdijk Fungal Biodiversity Institute'  # same as in BOLD
    record['identification_provided_by'] = row['Collected_by']  # XXX can be NaN!
    record['external_id'] = row['GBnumber']
    record['locality'] = row['Country'] if row['Country'] else 'Unknown'
    record['kingdom'] = row['kingdom']

    return record


def load_excel(input_file):
    df = pd.read_excel(input_file, sheet_name="Sheet1", header=0,
                       engine='openpyxl')  # req. openpyxl package to be installed
    df.fillna('', inplace=True)
    specimens_created = 0
    specimens_existing = 0
    markers_created = 0
    barcodes_created = 0
    barcodes_existing = 0
    incomplete_records = 0
    fail_matching_nsr_species = 0
    unknown_taxon_record_set = set()
    specimen_index_id_dict = get_specimen_index_dict(session, Specimen)
    barcode_index_id_dict = get_barcode_index_dict(session, Barcode)
    for index, row in df.iterrows():

        # initialize dict with relevant fields, next row if failed
        record = init_record_fields(row)
        if record is None:
            incomplete_records += 1
            continue

        if record['taxon'] in unknown_taxon_record_set:
            fail_matching_nsr_species += 1
            continue

        # initialize species, continue if failed
        nsr_species_node = NsrNode.match_species_node(record['taxon'], session, kingdom=record['kingdom'])
        if nsr_species_node is None:
            fail_matching_nsr_species += 1
            unknown_taxon_record_set.add(record['taxon'])
            continue

        # get or create specimen
        index = f"{nsr_species_node.species_id}-{record['catalognum']}-{record['institution_storing']}-{record['identification_provided_by']}"
        if index not in specimen_index_id_dict:
            specimen, created = Specimen.get_or_create_specimen(nsr_species_node.species_id,
                                                                record['catalognum'],
                                                                record['catalognum'],
                                                                record['institution_storing'],
                                                                record['identification_provided_by'],
                                                                record['locality'], session, fast_insert=True)

            specimen_id = specimen.id
            specimens_created += 1
            specimen_index_id_dict[index] = specimen_id
        else:
            specimen_id = specimen_index_id_dict[index]
            specimens_existing += 1

        # get or create marker
        marker, created = Marker.get_or_create_marker(record['marker'], session)
        if created:
            markers_created += 1

        # get or create barcode
        index = f"{specimen_id}-{DataSource.WFBI}-{marker.id}-{record['external_id']}"
        if index not in barcode_index_id_dict:
            barcode, created = Barcode.get_or_create_barcode(specimen_id, DataSource.WFBI,
                                                             marker.id, None, record['external_id'],
                                                             session, fast_insert=True)
            barcodes_created += 1
            barcode_index_id_dict[index] = barcode.id
        else:
            barcodes_existing += 1

    main_logger.info(f'{specimens_created=}')
    main_logger.info(f'{specimens_existing=}')
    main_logger.info(f'{markers_created=}')
    main_logger.info(f'{barcodes_created=}')
    main_logger.info(f'{barcodes_existing=}')
    main_logger.info(f'{incomplete_records=}')
    main_logger.info(f'{fail_matching_nsr_species=}')


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('pragma journal_mode=OFF')
    cursor.execute('PRAGMA synchronous=OFF')
    cursor.execute('PRAGMA cache_size=100000')
    cursor.execute('PRAGMA temp_store = MEMORY')
    cursor.close()


if __name__ == '__main__':
    # process command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-db', default="arise-barcode-metadata.db", help="Input file: SQLite DB")
    parser.add_argument('-excel', help="A TSV file exported from Klasse using the ARISE template")
    parser.add_argument('--verbose', '-v', action='count', default=1)

    args = parser.parse_args()
    args.verbose = 70 - (10 * args.verbose) if args.verbose > 0 else 0
    [h.addFilter(loggers.LevelFilter(args.verbose)) for h in lk_logger.handlers]

    # create connection/engine to database file
    dbfile = args.db
    engine = create_engine(f'sqlite:///{dbfile}', echo=False)

    # load data during session
    Session = sessionmaker(engine)
    session = Session()
    main_logger.info('Load excel file "%s"', args.excel)
    load_excel(args.excel)
    session.commit()
