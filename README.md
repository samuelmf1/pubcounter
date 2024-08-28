# PubCounter: PubMed Query Tool
@author: Sam Friedman

PubCounter automates requests for publication count of PubMed queries.

## Key features
1. Processes input files containing search terms (e.g., RSIDs)
2. Queries PubMed via Entrez E-utilities for publication counts
3. Returns copy of original file with added column of PubMed publication counts per query

### Implementation Features

- Automatically detects file delimiters
- Supports compressed files (gzip, bzip2)
- Customizable for various delimiters and file formats
- Implements exponential backoff for API requests

## Requirements

- Python 3.6+
- Biopython
- tqdm
- backoff
- chardet

Install the required packages using the dependencies in `requirements.txt`.

### optional, but recommended
```{bash}
python3 -m venv .venv
source .venv/bin/activate  # activate your environment prior to pip install or running tool
```

### not optional
```
pip3 install -r requirements.txt
```

## Usage

```{bash}
python3 pubcounter.py input_file column_number [options]
```


### Arguments

- `input_filepath`: Path to the input file containing RSIDs.
- `column_number`: The column number containing the query (e.g., 1 for the first column).

### Options

- `-o, --output_fp`: Path to the output file. If not provided, will use input filename with '_pubmed_counts' appended.
- `-l, --log_fp`: Path to the log file. If not provided, will use input filename with '_pubmed_counts.log' appended.
- `-d, --delimiter`: Specify the delimiter manually. If not provided, will attempt to detect automatically.
- `-e, --email`: Email address for Entrez queries. Default is 'blank@example.com'.
- `-m, --max_retries`: Maximum number of retries for failed queries. Default is 3 retries.
- `-r, --retry_delay`: Delay in seconds between retries. Default is 10 seconds.

## Example

```
python pubmed_query_tool.py /path/to/your/input_data.ext 1 -e your_email@example.com
```

This command will:
- Use '/path/to/your/input_data.ext' as the input file
- Query the first column element
- Set the email for Entrez queries to 'your_email@example.com'
- Set all other parameters to default settings

## Output

The script will create two files:
1. An output file with the original data and an additional column for PubMed hit counts.
2. A log file with detailed information about the script's execution.

## Note

Make sure to provide a valid email address when using this script. This is required by NCBI's E-utilities and helps them contact you if there are any issues with your queries.

## License

[MIT License](https://opensource.org/licenses/MIT)