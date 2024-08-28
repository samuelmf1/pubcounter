from Bio import Entrez
import argparse
import os
import logging
import gzip
import bz2
import csv
import chardet
from datetime import datetime
import backoff
import time
from urllib.error import HTTPError
from tqdm import tqdm

VALID_DELIMITERS = [',', ' ', '\t', ';', '|', ':']
date_today = datetime.now().strftime("%m%d%y")

def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def get_file_delimiter(file_path : str) -> str:
    """
    Determine the delimiter of a given file (compressed or not).
    
    :param file_path (str): Path to the input file.
    :return: Detected delimiter or '\t' by default if not determined.
    """

    file_path = os.path.expanduser(file_path)

    def open_file(file_path):
        if file_path.endswith('.gz'):
            return gzip.open(file_path, 'rt')
        elif file_path.endswith('.bz2'):
            return bz2.open(file_path, 'rt')
        else:
            return open(file_path, 'r')
    
    try:
        with open_file(file_path) as file:
            # Read a sample of the file (first 1000 bytes)
            sample = file.read(1000)
            
            # Detect the file encoding
            encoding = chardet.detect(sample.encode())['encoding']
            
            # Reset file pointer
            file.seek(0)
            
            # Read the first few lines
            lines = [file.readline() for _ in range(5)]
            
            # Use csv.Sniffer to detect the dialect
            dialect = csv.Sniffer().sniff(''.join(lines), delimiters = VALID_DELIMITERS)
            
            return dialect.delimiter
    
    except Exception as e:
        print(f"Error determining delimiter: {str(e)}")
        return '\t'  # Default to tab delimiter

@backoff.on_exception(backoff.expo, 
                      (IOError, RuntimeError, HTTPError),
                      max_tries=5)
def get_pubmed_count(query: str, max_retries: int, retry_delay: int) -> int:
    """
    Retrieve the count of PubMed articles for a given query.

    Args:
        query (str): The search query for PubMed.

    Returns:
        int: The count of articles matching the query.
        int: 0 if an error occurs after all retries.
    """
    max_retries = args.max_retries
    retry_delay = args.retry_delay

    for attempt in range(max_retries):
        try:
            with Entrez.esearch(db="pubmed", term=query, retmode="xml") as handle:
                results = Entrez.read(handle)
            
            count = results["Count"]
            # logging.info(f"Query: {query}, Count: {count}")
            return count
        except HTTPError as e:
            if e.code == 500:
                logging.warning(f"HTTP 500 error for query '{query}'. Attempt {attempt + 1} of {max_retries}.")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
            if e.code == 429:
                logging.warning(str(e))
                if attempt < max_retries - 1:
                    logging.info(f"Pausing for {retry_delay} seconds. Attempt {attempt + 1} of {max_retries}.")
                    time.sleep(retry_delay)
                    continue
            logging.error(f"HTTP error {e.code} querying '{query}': {str(e)}")
        except Exception as e:
            logging.error(f"Error querying '{query}': {str(e)}")
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    logging.error(f"Failed to query '{query}' after {max_retries} attempts.")
    return -1  # Return 0 instead of -1 for failed queries

def main(args):
    input_fp = args.input_filepath
    column_number = args.column_number
    
    base, ext = os.path.splitext(input_fp)
    args.output_fp = output_fp = args.output_fp or f"{base}_pubmed_counts{ext}"
    args.log_fp = log_fp = args.log_fp or f"{base}_pubmed_counts.log"
    args.delimiter = delim = get_file_delimiter(input_fp) if args.delimiter is None else args.delimiter

    setup_logging(log_fp)
    logging.info(f"{'='*20} PubCounter {'='*20}")
    for arg in vars(args):
        logging.info(f"{arg}: {getattr(args, arg)}")
    logging.info(f"Detected delimiter: TAB:{delim=='\t'} SPACE:{delim==' '} COMMA:{delim==','} PIPE:{delim=='|'} SEMICOLON:{delim==';'} COLON:{delim==':'}")
    
    logging.info('-' * 40)
    logging.info(f"Starting PubMed query process for file: {input_fp}")
    logging.info(f"Output will be written to: {output_fp}")
    logging.info('-' * 40)


    try:
        with open(input_fp, "r") as infile, open(output_fp, "w") as outfile:
            
            # Preview data in the specified column
            preview_lines = []
            for _ in range(5):  # Preview first 5 lines
                line = next(infile, None)
                if line:
                    parts = line.strip().split(f"{delim}")
                    if column_number <= len(parts):
                        preview_lines.append(parts[column_number - 1])
            
            logging.info(f"Preview of data in column {column_number}:")
            for item in preview_lines:
                logging.info(item)

            logging.info('-' * 40)
            infile.seek(0)

            # Write header
            header = infile.readline().strip()
            outfile.write(f"{header}{delim}pubmed_hits_{date_today}\n")
            logging.info("Header processed and written to output file")

            # Count total lines for tqdm
            total_lines = sum(1 for _ in infile)
            infile.seek(0)  # Reset file pointer
            next(infile)  # Skip header

            # Process each line with tqdm progress bar
            for line in tqdm(infile, total=total_lines-1, desc="Processing lines"):
                parts = line.strip().split(f"{delim}")
                rsid = parts[column_number - 1]
                count = get_pubmed_count(rsid, args.max_retries, args.retry_delay)
                outfile.write(f"{line.strip()}{delim}{count}\n")
                outfile.flush()  # Ensure the line is written immediately

        logging.info(f"Processing complete. Total lines processed: {total_lines}")

    except Exception as e:
        logging.error(f"An error occurred during processing: {e}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query PubMed for hits from a file and append results to the original file.")
    parser.add_argument("input_filepath", type=str, help="Path to the input file containing RSIDs.")
    parser.add_argument("column_number", type=int, help="The column number containing query. E.g., 1 for the first column.")
    parser.add_argument("-o", "--output_fp", type=str, help="Path to the output file. If not provided, will use input filename with '_pubmed_counts' appended.")
    parser.add_argument("-l", "--log_fp", type=str, help="Path to the log file. If not provided, will use input filename with '_pubmed_counts.log' appended.")
    parser.add_argument("-d", "--delimiter", type=str, choices=VALID_DELIMITERS, help="Specify the delimiter manually. If not provided, will attempt to detect automatically.")
    parser.add_argument("-e", "--email", type=str, default="null@example.com", help="Email address for Entrez queries. Default is 'your_email@example.com'.")
    parser.add_argument("-m", "--max_retries", type=int, default=3, help="Maximum number of retries for failed queries. Default is 5.")
    parser.add_argument("-r", "--retry_delay", type=int, default=10, help="Delay in seconds between retries. Default is 10 seconds.")

    args = parser.parse_args()

    Entrez.email = args.email
    main(args)