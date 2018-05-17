"""a console-script to  allow a library dev to search for records in OLE by arbitrary MARC fields
"""

__author__ = "Tyler Danstrom"
__email__ = "tdanstrom@uchicago.edu"
__version__ = "1.0.0"

from argparse import ArgumentParser, Action, ArgumentError
from marcextraction.lookup import MarcFieldLookup
from marcextraction.interfaces import SolrIndexSearcher, OLERecordFinder
from marcextraction.utils import find_ole_bib_numbers
from os import environ, getcwd
from os.path import exists, join
from sys import stdout, stderr
from urllib.parse import urlparse
from uuid import uuid4
from xml.etree import ElementTree

# run using the following command 
# OLE_INDEX=[uchicago ole sru api] SOLR_INDEX=[uchicago ole solr index] find_records -h

OLE_INDEX = environ["OLE_INDEX"]
SOLR_INDEX = environ["SOLR_INDEX"]

class CombineWithProperFieldLookup(Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super(CombineWithProperFieldLookup, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, args, values, options_string=None):
        if (args.field_lookup != None) and (self.dest == 'subfield_label_lookup'):
            raise ArgumentError(self, "Cannot be combined with -f/--field_lookup")
        elif args.field_label_lookup != None and (self.dest == 'subfield_lookup'):
            raise ArgumentError(self, "Cannot be combined with -fl/--field_label_lookup")
        else:
            print(self.dest)
            print(args)
            setattr(args, self.dest, values)

def show_lookups(args):
    """a function to get the valid lookup labels and printing it to the screen

    The developer should use the MARC field labels in the field_lookup parameter of the searching subparser
    and the appropriate SubField label in the subfield_lookup paramter of the same subparser

    Returns:
        stdout. A pretty-printed string sent to stdout for display in a console.
    """
    output = MarcFieldLookup.show_valid_lookups(pretty_print=True)
    stdout.write(output)

def search_func(args):
    """a function to search the requested Solr index for the query term matching the desired MARC field

    Returns:
        list. A list of XML extracted from the Solr index or an empty list if no items matched the query.
    """
    searcher = SolrIndexSearcher(SOLR_INDEX, 'ole')
    print(args)
    if args.field_lookup and args.subfield_lookup:
        print("need to search by field and subfield")
        results = searcher.search(args.query_term, field=args.field_lookup, subfield=args.subfield_lookup)
    elif args.field_label_lookup and args.subfield_label_lookup:
        results = searcher.search(args.query_term, field_label=args.field_label_lookup, subfield_label=args.subfield_label_lookup)
    elif args.field_lookup:
        results = searcher.search(args.query_term, field=args.field_lookup)
        print(results)
    elif args.field_label_lookup:
        results = searcher.search(args.query_term, field_label=args.field_lookup)
    else:
        results = searcher.search(args.query_term)
    if args.extract_records:
        count = 1
        ole_url_object = urlparse(OLE_INDEX)
        for n in results:
            cf_field = n
            if cf_field:
                bib_number = cf_field
                finder = OLERecordFinder(bib_number, ole_url_object.netloc, ole_url_object.scheme, ole_url_object.path)
                check, data = finder.get_record()
                if check:
                    for n_thing in data:
                        xml_doc = ElementTree.ElementTree(ElementTree.fromstring(n_thing))
                        random_id = uuid4().hex
                        fname = "{}.xml".format(random_id)
                        if exists(join(getcwd(), fname)):
                            stderr.write("could not write over existing file {}".format(fname))
                        else:
                            xml_doc.write(fname, xml_declaration=True, encoding="UTF-8")
                            stdout.write("record for MARC bib number {} written to {}\n".format(cf_field, fname))
                    stdout.write("{} has MARC records in the OLE SRU\n".format(cf_field))
            else:
                stderr.write("record {} did not have a bib number in controlfield_0001\n".format(str(count)))
        count += 1
    else:
        count = 1
        for n_result in results:
            stdout.write("Bib number: {}\n".format(n_result.strip()))
            count += 1 
        stdout.write("Total records in search: {}\n".format(count))

def main():
    """the main function of the console-script.

    There are two sub-parsers: show and searching

    - show takes no parameters and simply returns a pretty-printed display of the MARC field and subfield
      labels necessary to do a field-targetted search
    - searching takes three parameters and returns to stdout the bib numbers of the matching records.
        - query_term is the string that you want to find in the requested MARC field/subfield. Searches include stemming.
        - field_lookup is the MARC field label from show that the developer wants to target
        - subfield_lookup is the subfield label from the show that the developer wants to do a target search in
    """
    try:
        parser = ArgumentParser()
        subparsers = parser.add_subparsers(help='how to retrieve valid lookup labels', dest='which')
        show = subparsers.add_parser('show_lookups')
        search = subparsers.add_parser('searching')
        show.set_defaults(which='show')
        search.set_defaults(which='searching')
        group1 = search.add_mutually_exclusive_group()
        group1.add_argument("-f", "--field_lookup", help="The specific MARC field that you are searching in", type=int)
        group1.add_argument("-fl", "--field_label_lookup", help="The label for the specific MARC field that you are searching in", type=str)

        search.add_argument("-sf", "--subfield_lookup", help="The MARC sub field cod for the specific subfield field that you are searching in", type=str, action=CombineWithProperFieldLookup)
        search.add_argument("-sfl", "--subfield_label_lookup", help="The label for the specific MARC subfield that you are searching in", type=str, action=CombineWithProperFieldLookup)
        search.add_argument("query_term", help="A string that you want to search the OLE index stemmed for matching results", 
                             action='store', type=str)
        search.add_argument("--extract_records", action='store_true', default=False, help="Use this flag if you don't actually want to save the records to disk yet")
        parser.add_argument("--version", action='version', version='%(prog)s 1.0')
 
        args = parser.parse_args()
        if args.which == 'show':
            show_lookups(args)
        elif args.which == 'searching':
            search_func(args)
        return 0
    except KeyboardInterrupt:
        return 131